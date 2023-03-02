import zmq
from time import sleep
from .connect import generate_publisher, send_array
#import eego_sdk
from threading import Event
import numpy as np
import pandas as pd
import time
from warnings import warn

def get_freq_sample(freq_sample, amplifier):
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
    final_freq_sample = get_freq_sample(freq_sample, amplifier)
    stream = amplifier.OpenEegStream(final_freq_sample, ref_ranges[0], bip_ranges[0])
    
    i = 0
    while not event.is_set():
        data = np.array(stream.getData())
        socket.send_string(topic, zmq.SNDMORE)
        socket.send_pyobj(data)
        i += 1
    sleep(0.005)  # Sleeps 5 milliseconds to be polite with the CPU
    print(f'Sent {i} samples')
    socket.send_string(topic, zmq.SNDMORE)
    socket.send_pyobj('stop')
    sleep(1)  # Gives enough time to the subscribers to update their status

def get_impedance():
    factory = eego_sdk.factory()
    amplifiers = factory.getAmplifiers()
    amplifier = amplifiers[0]
    stream_imp = amplifier.OpenImpedanceStream()
    return list(stream_imp.getData())
    
def stream_to_publish(freq_sample, event, port, topic = 'stream', topic_impedance = 'impedance'):
    context = zmq.Context()
    socket = generate_publisher(port, context)

    impedance_init = get_impedance()
    run_EEG_stream(freq_sample, event, socket, topic)
    impedance_final = get_impedance()
    
    socket.send_string(topic_impedance, zmq.SNDMORE)
    socket.send_pyobj(impedance_init, zmq.SNDMORE)
    socket.send_pyobj(impedance_final)
    
    sleep(1)  # Gives enough time to the subscribers to update their status
    socket.close()

class DataIterator:
    def __init__(self, n_samples, freq_sample, data_file):
        # channel is assumed to be zero-indexed
        self.n_samples = n_samples
        self.freq_sample = freq_sample
        self.counter = 0
        self.stop = False

        D = np.array(pd.read_csv(data_file))
        #self.data = D[:, :]
        self.data = D

        self.n_rows = len(self.data)

    def __iter__(self):
        return self

    def __next__(self):
        idx_start = self.n_samples * self.counter
        idx_end = idx_start + self.n_samples
        if idx_end <= self.n_rows:
            time.sleep(self.n_samples/self.freq_sample)   
            self.counter += 1

            if ((self.n_samples + 1) * self.counter) > self.n_rows:
                self.reset()

            next_data = self.data[idx_start:idx_end,:]
            return next_data
        else:
            self.counter = 0 # reset iterator
            raise StopIteration

    def acquire_data(self, queue):
        while not self.stop:
            queue.put({'topic': 'sample', 'data': next(self)})

    def publish_data(self, port, topic = 'stream', topic_impedance = 'impedance'):
        context = zmq.Context()
        socket = generate_publisher(port, context)

        impedance_init = list(np.zeros(32)*1000)

        i = 0
        while not self.stop:
            data = next(self)
            socket.send_string(topic, zmq.SNDMORE)
            socket.send_pyobj(data)
            i += 1
        sleep(0.005)  # Sleeps 5 milliseconds to be polite with the CPU
        print(f'Sent {i} samples')
        socket.send_string(topic, zmq.SNDMORE)
        socket.send_pyobj('stop')
        sleep(1)  # Gives enough time to the subscribers to update their status

        impedance_final = list(np.ones(32)*1000)
        socket.send_string(topic_impedance, zmq.SNDMORE)
        socket.send_pyobj(impedance_init, zmq.SNDMORE)
        socket.send_pyobj(impedance_final)

        sleep(1)  # Gives enough time to the subscribers to update their status
        socket.close()

    def reset(self):
        self.counter = 0
    