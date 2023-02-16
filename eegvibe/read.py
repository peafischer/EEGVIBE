import zmq
from time import sleep
from .connect import generate_publisher
#import eego_sdk
from threading import Event
import numpy as np
import pandas as pd
import time

def stream_to_queue(queue, event):
    factory = eego_sdk.factory()
    amplifiers = factory.getAmplifiers()
    amplifier = amplifiers[0]
    
    rates = amplifier.getSamplingRatesAvailable()
    ref_ranges = amplifier.getReferenceRangesAvailable()
    bip_ranges = amplifier.getBipolarRangesAvailable()
    stream = amplifier.OpenEegStream(rates[0], ref_ranges[0], bip_ranges[0])
    
    while not event.is_set():
        queue.put({'topic': 'sample', 'data': np.array(stream.getData())})

def publish_from_queue(queue, event, port):
    context = zmq.Context()
    socket = generate_publisher(port, context)

    i = 0
    while not event.is_set():
        while not queue.empty():
            data = queue.get()  # Should be a dictionary {'topic': topic, 'data': data}
            socket.send_string(data['topic'], zmq.SNDMORE)
            socket.send_pyobj(data['data'])
            i += 1
    sleep(0.005)  # Sleeps 5 milliseconds to be polite with the CPU
    print(f'Sent {i} samples')
    socket.send_string('stop')
    sleep(1)  # Gives enough time to the subscribers to update their status
    socket.close()

def stream_to_publish(event, port, topic):
    context = zmq.Context()
    socket = generate_publisher(port, context)

    factory = eego_sdk.factory()
    amplifiers = factory.getAmplifiers()
    amplifier = amplifiers[0]
    
    rates = amplifier.getSamplingRatesAvailable()
    ref_ranges = amplifier.getReferenceRangesAvailable()
    bip_ranges = amplifier.getBipolarRangesAvailable()
    stream = amplifier.OpenEegStream(rates[0], ref_ranges[0], bip_ranges[0])

    i = 0
    while not event.is_set():
        data = np.array(stream.getData())
        socket.send_string(topic, zmq.SNDMORE)
        socket.send_pyobj(data)
        i += 1
    sleep(0.005)  # Sleeps 5 milliseconds to be polite with the CPU
    print(f'Sent {i} samples')
    socket.send_string('stop')
    sleep(1)  # Gives enough time to the subscribers to update their status
    socket.close()

class DataIterator:
    def __init__(self, n_samples, sampling_rate, data_file):
        # channel is assumed to be zero-indexed
        self.n_samples = n_samples
        self.sampling_rate = sampling_rate
        self.counter = 0
        self.stop = False

        D = np.array(pd.read_csv(data_file))
        self.data = D[:, :]

        self.n_rows = len(self.data)

    def __iter__(self):
        return self

    def __next__(self):
        idx_start = self.n_samples * self.counter
        idx_end = idx_start + self.n_samples
        if idx_end <= self.n_rows:
            time.sleep(self.n_samples/self.sampling_rate)   
            self.counter += 1

            if ((self.n_samples + 1) * self.counter) > self.n_rows:
                self.reset()

            next_data = self.data[idx_start:idx_end]
            return next_data
        else:
            self.counter = 0 # reset iterator
            raise StopIteration

    def acquire_data(self, queue):
        while not self.stop:
            queue.put({'topic': 'sample', 'data': next(self)})
            
    def reset(self):
        self.counter = 0
    