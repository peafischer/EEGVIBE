import zmq
import h5py
import pickle
from time import sleep
from datetime import date
from pathlib import Path

from .connect import generate_subscriber, is_stop_data

def find_filename(path = './out_data/', format = 'hdf5'):
    today = date.today()
    today_str = today.strftime("%d_%m_%Y")

    c = 1
    filename = '_'.join([today_str, f"subject_{c}"])
    while Path(path + filename + '.' + format).is_file():
        c += 1
        filename = '_'.join([today_str, f"subject_{c}"])
    
    return (path + filename + '.' + format)

def write_stream(port, topic, filename):
    
    chunk_size = 100

    context = zmq.Context()
    socket = generate_subscriber(port, topic, context)

    socket_imp = generate_subscriber(port, 'imp', context)

    topic = socket.recv_string()
    data = socket.recv_pyobj() 

    n_channels = data.shape[1]
    d_type = data.dtype
    f = h5py.File(filename, 'w')
    dset = f.create_dataset(
        "EEG", 
        (1, n_channels), 
        maxshape = (None, n_channels), 
        dtype = d_type, 
        chunks = (chunk_size, n_channels)
    )

    n_samples = data.shape[0]
    dset.resize((dset.shape[0] + n_samples, n_channels))
    dset[-n_samples: , :] = data

    i = 1
    while True:
        topic = socket.recv_string()
        data = socket.recv_pyobj() 
        if is_stop_data(data):
            break

        n_samples = data.shape[0]
        dset.resize((dset.shape[0] + n_samples, n_channels))
        dset[-n_samples: , :] = data
        i += 1

    topic_imp = socket_imp.recv_string()
    impedance_init = socket_imp.recv_pyobj() 
    impedance_final = socket_imp.recv_pyobj() 
    dset.attrs['init_impedance'] = impedance_init
    dset.attrs['final_impedance'] = impedance_final

    sleep(1)  # Gives enough time for the publishers to finish sending data before closing the socket
    f.flush()
    f.close()
    print(f'Acquired {i} samples')
