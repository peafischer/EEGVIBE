import zmq
import h5py
import pickle
import numpy as np
from time import sleep
from datetime import date
from pathlib import Path
from warnings import warn

from .connect import generate_subscriber, is_stop_data, SerializingContext

def get_filename(participant_ID, channel_track, freq_target, stim_mode, phase_target, label, count):
    today = date.today()
    today_str = today.strftime("%d_%m_%Y")

    phase_degrees = np.around(np.rad2deg(phase_target), decimals=2)

    if not label:
        filename = '_'.join(
            [today_str, 
            f'P{participant_ID}', 
            f'Ch{channel_track}',
            f'FRQ={freq_target}Hz',
            f'{stim_mode}',
            f'phase={phase_degrees}',
            f'v{count}']
        )  
    else:
        filename = '_'.join(
            [today_str, 
            f'P{participant_ID}', 
            f'Ch{channel_track}',
            f'FRQ={freq_target}Hz',
            f'{stim_mode}',
            f'phase={phase_degrees}',
            label,
            f'v{count}']
        )  
    return filename

def find_filename(participant_ID, channel_track, freq_target, stim_mode, phase_target, label = '', 
                  path = './out_data/', format = 'hdf5'):
    
    count = 1
    f = get_filename(participant_ID, channel_track, freq_target, stim_mode, phase_target, label, count)

    while Path(path + f + '.' + format).is_file():
        count += 1
        f = get_filename(participant_ID, channel_track, freq_target, stim_mode, phase_target, label, count)
     
    if count > 1:
        warn(f"File with provided parameters already exists, changing to v{count}.")
        
    return (path + f + '.' + format)

def write_stream(port, topic, filename):
    
    chunk_size = 100

    #context = zmq.Context()
    context = SerializingContext()

    socket = generate_subscriber(port, topic, context)
    
    topic = socket.recv_string()
    #data = socket.recv_pyobj() 
    data = socket.recv_array()

    n_channels = data.shape[1]
    d_type = data.dtype
    f = h5py.File(filename, 'w')
    dset = f.create_dataset(
        'EEG', 
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
        #data = socket.recv_pyobj() 
        data = socket.recv_array()
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
    socket.close()

def add_metadata(metadata, filename):
    f = h5py.File(filename, 'r+')
    dset = f['EEG']

    for k, v in metadata.items():
        dset.attrs[k] = v

    f.flush()
    f.close()