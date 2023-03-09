import zmq
from time import sleep
from .connect import generate_publisher, send_array, SerializingContext
#import eego_sdk
import numpy as np
import pandas as pd
import h5py
from time import sleep
from warnings import warn

def get_freq_sample(freq_sample, amplifier_ID):
    factory = eego_sdk.factory()
    amplifiers = factory.getAmplifiers()
    amplifier = amplifiers[amplifier_ID]

    try:
        rates = amplifier.getSamplingRatesAvailable()
        rates.index(freq_sample)
        return freq_sample
    except:
        diff = [abs(freq_sample - r) for r in rates]
        idx = diff.index(min(diff))
        new_freq = rates[idx]
        warn(f"Sampling rate {freq_sample} is not available. Using rate={new_freq} as the closest available value.")
        return new_freq

def run_EEG_stream(freq_sample, event, socket, topic):
    factory = eego_sdk.factory()
    amplifiers = factory.getAmplifiers()
    amplifier = amplifiers[0]
    
    ref_ranges = amplifier.getReferenceRangesAvailable()
    bip_ranges = amplifier.getBipolarRangesAvailable()
    stream = amplifier.OpenEegStream(freq_sample, ref_ranges[1], bip_ranges[0])
    
    i = 0
    while not event.is_set():
        data = np.array(stream.getData())
        socket.send_string(topic, zmq.SNDMORE)
        socket.send_array(data)
        i += 1
    sleep(0.005)  # Sleeps 5 milliseconds to be polite with the CPU
    print(f'Sent {i} samples')
    socket.send_string(topic, zmq.SNDMORE)
    #socket.send_pyobj('stop')
    socket.send_array(np.empty(0))

    sleep(1)  # Gives enough time to the subscribers to update their status

def get_impedance(amplifier_ID):
    factory = eego_sdk.factory()
    amplifiers = factory.getAmplifiers()
    amplifier = amplifiers[amplifier_ID]
    stream = amplifier.OpenImpedanceStream()
    return list(stream.getData())
    
def get_channel_names(amplifier_ID):
    factory = eego_sdk.factory()
    amplifiers = factory.getAmplifiers()
    amplifier = amplifiers[amplifier_ID]
    stream = amplifier.OpenImpedanceStream()
    channels = stream.getChannelList()
    return [str(c) for c in channels]

def read_from_stream(freq_sample, event, port, topic = 'stream'):
    context = SerializingContext()
    socket = generate_publisher(port, context)

    run_EEG_stream(freq_sample, event, socket, topic)

    sleep(1)  # Gives enough time to the subscribers to update their status
    socket.close()

def read_from_file(filename_data, n_samples_per_chunk, freq_sample, event, port, topic = 'stream'):

    file_format = filename_data.split('.')[-1]
    if file_format == 'csv':
        data = np.array(pd.read_csv(filename_data))
    elif file_format == 'hdf5':
        f = h5py.File(filename_data, 'r')
        data = f['EEG']
    else :
        raise FileNotFoundError(f"Invalid file format {file_format} provided. Please use csv or hdf5 files.")
    
    context = SerializingContext()
    socket = generate_publisher(port, context)

    i = 0
    while not event.is_set():
        idx_start = n_samples_per_chunk * i
        idx_end = idx_start + n_samples_per_chunk
        
        data_sample = np.ascontiguousarray(data[idx_start:idx_end, :])

        socket.send_string(topic, zmq.SNDMORE)
        socket.send_array(data_sample)

        i += 1
        sleep(n_samples_per_chunk/freq_sample) 

    sleep(0.005)  # Sleeps 5 milliseconds to be polite with the CPU
    print(f'Sent {i} samples')
    socket.send_string(topic, zmq.SNDMORE)
    #socket.send_pyobj('stop')
    socket.send_array(np.empty(0))
    sleep(1)  # Gives enough time to the subscribers to update their status

    if file_format == 'hdf5':
        f.close()

    socket.close()
