from time import sleep
import numpy as np
import zmq
from .oscilltrack import Oscilltrack
from .stimulator import Stimulator
from .connect import generate_publisher, generate_subscriber, MRStream, is_stop_data
from .filter import HighPassFilter, mean_subtract
from .write import write_stimulator

def analysis(port_publish, topic_publish, port_plot, topic_plot, filename_stim = None,
    phase_target = 0, freq_target = 10, freq_sample = 1000, freq_corner = 8,
    oscilltrack_suppression = 0.8, channel_track = 0, channels_ms = range(0,31), channels_EMG = [],
    N_pulses = 1, pulse_duration = 100, IPI = 0.2, stim_device_ID = 0):

    tracker = Oscilltrack(
        freq_target = freq_target, 
        phase_target = phase_target, 
        freq_sample = freq_sample, 
        suppression_cycle = oscilltrack_suppression
    )

    #p = generate_player(N_pulses, pulse_duration, IPI)
    stim = Stimulator(N_pulses = N_pulses, pulse_duration = pulse_duration, IPI = IPI, device_ID = stim_device_ID)
    filt = HighPassFilter(freq_corner = freq_corner, freq_sample = freq_sample)
    
    context = zmq.Context()
    most_recent_stream = MRStream(port_publish, topic_publish, context)
    plot_socket = generate_publisher(port_plot, context)

    filters_EMG = [HighPassFilter(freq_corner = freq_corner, freq_sample = freq_sample) for _ in range(len(channels_EMG))]
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
        filt_data = filt.filter(data_track)
        
        tracker.update(filt_data)
        is_stim = tracker.decide_stim()

        if is_stim:
            #p.Play(wait = False)
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
        write_stimulator(stim, filename_stim)

    most_recent_stream.close()
    plot_socket.close()
