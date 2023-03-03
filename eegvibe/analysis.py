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
    
    #context = zmq.Context()
    context = SerializingContext()
    most_recent_stream = MRStream(port_publish, topic_publish, context)
    socket = generate_subscriber(port_publish, topic_publish, context)
    plot_socket = generate_publisher(port_plot, context)

    stim.generate_player()

    filt_data_EMG = np.zeros(len(channels_EMG))

    i = 0
    while True:
        data = most_recent_stream.receive()
        #topic = socket.recv_string()
        #data = socket.recv_array() 

        if is_stop_data(data):
            plot_socket.send_string(topic_plot, zmq.SNDMORE)
            #plot_socket.send_pyobj(data, zmq.SNDMORE)
            #plot_socket.send_pyobj(filt_data_EMG)
            plot_socket.send_array(data, zmq.SNDMORE)
            plot_socket.send_array(filt_data_EMG)
            break
        
        for data_sample in data:
            data_track = mean_subtract(data_sample[channels_ref], data_sample[channel_track])
            #data_track = data_sample[channel_track]
            filt_data = filter_track.filter(data_track)
            
            tracker.update(filt_data)
            is_stim = tracker.decide_stim()

            if is_stim:
                stim.stimulate()

            for j, c_EMG in enumerate(channels_EMG):
                filt_data_EMG[j] = filters_EMG[j].filter(data_sample[c_EMG])

            plot_socket.send_string(topic_plot, zmq.SNDMORE)
            #plot_socket.send_pyobj(filt_data, zmq.SNDMORE)
            #plot_socket.send_pyobj(filt_data_EMG)
            plot_socket.send_array(filt_data, zmq.SNDMORE)
            plot_socket.send_array(filt_data_EMG)
        i+=1

    print(f'Analysed {i} samples')
    sleep(10)  # Gives enough time to the subscribers to update their status        
    if filename_stim is not None:
        stim.write_params(filename_stim)

    most_recent_stream.close()
    plot_socket.close()

def replay(port_publish, topic_publish, port_plot, topic_plot, 
    stim, filter_track, filters_EMG,
    channel_track = 0, channels_ref = range(0,31), channels_EMG = []):
    
    #context = zmq.Context()
    context = SerializingContext()
    #most_recent_stream = MRStream(port_publish, topic_publish, context)
    socket = generate_subscriber(port_publish, topic_publish, context)
    plot_socket = generate_publisher(port_plot, context) 

    stim.generate_player()

    filt_data_EMG = np.zeros(len(channels_EMG))
    
    stim_thread = Thread(target=stim.replay)
    stim_thread.start()

    i = 0
    while True:
        #data = most_recent_stream.receive()
        topic = socket.recv_string()
        data = socket.recv_array() 

        if is_stop_data(data):
            plot_socket.send_string(topic_plot, zmq.SNDMORE)
            #plot_socket.send_pyobj(data, zmq.SNDMORE)
            #plot_socket.send_pyobj(filt_data_EMG)
            plot_socket.send_array(data, zmq.SNDMORE)
            plot_socket.send_array(filt_data_EMG)
            break
        
        for data_sample in data:
            data_track = mean_subtract(data_sample[channels_ref], data_sample[channel_track])
            filt_data = filter_track.filter(data_track)

            for j, c_EMG in enumerate(channels_EMG):
                filt_data_EMG[j] = filters_EMG[j].filter(data_sample[c_EMG])

            plot_socket.send_string(topic_plot, zmq.SNDMORE)
            #plot_socket.send_pyobj(filt_data, zmq.SNDMORE)
            #plot_socket.send_pyobj(filt_data_EMG)
            plot_socket.send_array(filt_data, zmq.SNDMORE)
            plot_socket.send_array(filt_data_EMG)

        i+=1

    print(f'Analysed {i} samples')
    sleep(10)  # Gives enough time to the subscribers to update their status        

    #most_recent_stream.close()
    stim_thread.join()
    plot_socket.close()
