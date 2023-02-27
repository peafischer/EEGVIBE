from time import sleep
import numpy as np
import zmq
from .oscilltrack import Oscilltrack
from .stimulate import CLStimulator, SemiCLStimulator, generate_player
from .connect import generate_publisher, generate_subscriber, MRStream, is_stop_data
from .filter import HighPassFilter, mean_subtract

def analysis(port_publish, topic_publish, port_plot, topic_plot, 
    tracker, stim, filter_track, filter_EMG, filename_stim = None,
    channel_track = 0, channels_ms = range(0,31), channels_EMG = []):
    
    context = zmq.Context()
    most_recent_stream = MRStream(port_publish, topic_publish, context)
    plot_socket = generate_publisher(port_plot, context)

    stim.generate_player()

    filters_EMG = [filter_EMG for _ in range(len(channels_EMG))]
    filt_data_EMG = np.zeros(len(channels_EMG))

    i = 0
    while True:
        data = most_recent_stream.receive()
        if is_stop_data(data):
            plot_socket.send_string(topic_plot, zmq.SNDMORE)
            plot_socket.send_pyobj(data, zmq.SNDMORE)
            plot_socket.send_pyobj(filt_data_EMG)
            break
        
        data_track = mean_subtract(data[0, channels_ms], data[0, channel_track])
        filt_data = filter_track.filter(data_track)
        
        tracker.update(filt_data)
        is_stim = tracker.decide_stim()

        if is_stim:
            stim.stimulate()

        for j, c_EMG in enumerate(channels_EMG):
            filt_data_EMG[j] = filters_EMG[j].filter(data[0, c_EMG])

        plot_socket.send_string(topic_plot, zmq.SNDMORE)
        plot_socket.send_pyobj(filt_data, zmq.SNDMORE)
        plot_socket.send_pyobj(filt_data_EMG)

        i+=1

    print(f'Analysed {i} samples')
    sleep(10)  # Gives enough time to the subscribers to update their status        
    if filename_stim is not None:
        stim.write_params(filename_stim)

    most_recent_stream.close()
    plot_socket.close()
