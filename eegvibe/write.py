import zmq
import h5py
from time import sleep
from .connect import generate_subscriber, is_stop_data

def write_stream(file_name, port, topic):
    
    chunk_size = 100

    context = zmq.Context()
    socket = generate_subscriber(port, topic, context)

    topic = socket.recv_string()
    data = socket.recv_pyobj() 

    n_channels = data.shape[1]
    d_type = data.dtype
    f = h5py.File(file_name + '.hdf5', 'w')
    dset = f.create_dataset("default", (1, n_channels), maxshape = (None, n_channels), dtype = d_type, chunks = (chunk_size, n_channels))

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
    