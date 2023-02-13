import zmq
from time import sleep
from .connect import generate_publisher
import eego_sdk
from threading import Event
import numpy as np

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

def publisher(queue, event, port):
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