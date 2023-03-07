from time import sleep
import numpy as np
import zmq
from threading import Thread
from .oscilltrack import Oscilltrack
from .stimulate import CLStimulator, SemiCLStimulator, init_CLStimulator, init_SemiCLStimulator
from .connect import generate_publisher, generate_subscriber, MRStream, is_stop_data, SerializingContext
from .filter import HighPassFilter, mean_subtract

def tracking(port_publish, topic_publish, port_plot, topic_plot, 
    tracker, stim, filter_track, filters_EMG, filename_stim = None,
    channel_track = 0, channels_ref = range(0,31), channels_EMG = []):
    
    context = SerializingContext()
    most_recent_stream = MRStream(port_publish, topic_publish, context)
    plot_socket = generate_publisher(port_plot, context)

    data_channels = np.zeros(len(channels_EMG) + 1)

    stim.generate_player()

    i = 0
    while True:
        data = most_recent_stream.receive()

        if is_stop_data(data):
            plot_socket.send_string(topic_plot, zmq.SNDMORE)
            plot_socket.send_array(data)
            break
        
        for data_sample in data:
            data_channels[0] = mean_subtract(data_sample[channels_ref], data_sample[channel_track])
            data_channels[0] = filter_track.filter(data_sample[0])

            tracker.update(data_channels[0])
            is_stim = tracker.decide_stim()

            if is_stim:
                stim.stimulate()

            for j, c in enumerate(channels_EMG):
                data_channels[j+1] = filters_EMG[j].filter(data_sample[c])

            plot_socket.send_string(topic_plot, zmq.SNDMORE)
            plot_socket.send_array(data_channels)
        i+=1

    print(f'Analysed {i} chunks')
    sleep(10)  # Gives enough time to the subscribers to update their status        
    if filename_stim is not None:
        stim.write_params(filename_stim)

    most_recent_stream.close()
    plot_socket.close()

def replay(port_publish, topic_publish, port_plot, topic_plot, 
    stim, filter_track, filters_EMG,
    channel_track = 0, channels_ref = range(0,31), channels_EMG = []):
    
    context = SerializingContext()
    most_recent_stream = MRStream(port_publish, topic_publish, context)
    plot_socket = generate_publisher(port_plot, context) 

    data_channels = np.zeros(len(channels_EMG) + 1)

    stim.generate_player()
    stim_thread = Thread(target=stim.replay)
    stim_thread.start()

    i = 0
    while True:
        data = most_recent_stream.receive()

        if is_stop_data(data):
            plot_socket.send_string(topic_plot, zmq.SNDMORE)
            plot_socket.send_array(data)
            break
        
        for data_sample in data:
            data_channels[0] = mean_subtract(data_sample[channels_ref], data_sample[channel_track])
            data_channels[0] = filter_track.filter(data_sample[0])

            for j, c in enumerate(channels_EMG):
                data_channels[j+1] = filters_EMG[j].filter(data_sample[c])

            plot_socket.send_string(topic_plot, zmq.SNDMORE)
            plot_socket.send_array(data_channels)

        i+=1

    print(f'Analysed {i} samples')
    sleep(10)  # Gives enough time to the subscribers to update their status        

    most_recent_stream.close()
    stim_thread.join()
    plot_socket.close()
