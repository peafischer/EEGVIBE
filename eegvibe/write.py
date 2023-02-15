import zmq
import h5py
from time import sleep
from .connect import generate_subscriber

def write_stream(file_name, port, topic):
    
    context = zmq.Context()
    socket = generate_subscriber(port, topic, context)

    topic = socket.recv_string()
    data = socket.recv_pyobj() 

    d_shape = data.shape
    d_type = data.dtype
    f = h5py.File(file_name + '.hdf5', 'w')
    dset = f.create_dataset("default", d_shape + (1,), maxshape = d_shape + (None,), dtype = d_type)
    dset[:,:,0] = data
    dset.resize(d_shape + (2,))

    i = 1
    while True:
        topic = socket.recv_string()
        data = socket.recv_pyobj() 
        if isinstance(data, str):
            break
        dset[:,:,i] = data
        i += 1
        dset.resize(d_shape + (i+1,))
    sleep(1)  # Gives enough time for the publishers to finish sending data before closing the socket
    f.flush()
    print(f'Acquired {i} samples')
    