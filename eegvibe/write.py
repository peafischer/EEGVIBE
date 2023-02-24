import zmq
import h5py
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

def write_stream(port, topic, out_path = './out_data/', data_format = 'hdf5'):
    
    chunk_size = 100

    context = zmq.Context()
    socket = generate_subscriber(port, topic, context)

    topic = socket.recv_string()
    data = socket.recv_pyobj() 

    n_channels = data.shape[1]
    d_type = data.dtype
    file_name = find_file_name(out_path, data_format)
    f = h5py.File(out_path + file_name + '.' + data_format, 'w')
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

    sleep(1)  # Gives enough time for the publishers to finish sending data before closing the socket
    f.flush()
    f.close()
    print(f'Acquired {i} samples')
    