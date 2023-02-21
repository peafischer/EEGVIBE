import numpy as np
from math import atan2
from time import sleep
import zmq
from .sound_gen import generate_player
from .connect import generate_publisher, generate_subscriber, MRStream, is_stop_data
from .filter import HighPassFilter, mean_subtract

class Oscilltrack:
    a = 0.0
    b = 0.0
    re = 0.0
    im = 0.0
    theta = 0.0
    sinv = 0.0
    cosv = 1.0

    def __init__(self, freq_target, phase_target, freq_sample, suppression_cycle, gamma = None):
        self.phase_target = phase_target
        self.w = 2 * np.pi * freq_target / freq_sample
        self.gamma = gamma if gamma != None else 125/freq_sample
        self.suppression_reset = suppression_cycle * freq_sample / freq_target
        self.suppression_count = 0
        self.is_prev_above_thrs = False

    def update(self, data):
        
        Delta = self.pred_error(data)
        self.a += self.gamma * Delta * self.sinv
        self.b += self.gamma * Delta * self.cosv

        self.theta += self.w
        # Wrap theta in the range [-pi, pi] for numerical stability
        if self.theta >= np.pi:
           self.theta -= 2*np.pi

        self.sinv = np.sin(self.theta)
        self.cosv = np.cos(self.theta)
        self.re = self.a * self.sinv + self.b * self.cosv
        self.im = self.b * self.sinv - self.a * self.cosv 

    def pred_error(self, data):
        # Calculates the error between the predicted signal value and the actual data at a timestep.
        # Used internally in the update function to update self.a and self.b .
        # This is a separate function for debug purposes.
        return data - self.re
    
    def get_phase(self):
        return atan2(self.im, self.re)

    def decide_stim(self):
        phase = self.get_phase()
        phase_rotated = phase - self.phase_target
        if phase_rotated >= np.pi:
            phase_rotated -= 2*np.pi
        elif phase_rotated < -np.pi:
            phase_rotated += 2*np.pi

        is_stim = False
        is_above_thrs = phase_rotated >= 0
        
        if is_above_thrs and (not self.is_prev_above_thrs) and (phase_rotated < np.pi/2):
            is_stim = self.suppression_count == 0
            self.suppression_count = self.suppression_reset

        self.is_prev_above_thrs = is_above_thrs
        if self.suppression_count > 0 :
            self.suppression_count -= 1
        else :
            self.suppression_count = 0
        
        return is_stim



def track_phase(port_publish, topic_publish, port_plot, topic_plot, 
    phase_target = 0, freq_target = 10, freq_sample = 1000, freq_corner = 8,
    oscilltrack_suppression = 0.8, channel_track = 0, channels_ms = range(0,31), channels_EMG = [],
    N_pulses = 1, pulse_duration = 100, IPI = 0.2):

    tracker = Oscilltrack(
        freq_target = freq_target, 
        phase_target = phase_target, 
        freq_sample = freq_sample, 
        suppression_cycle = oscilltrack_suppression
    )

    p = generate_player(N_pulses, pulse_duration, IPI)

    filt = HighPassFilter(freq_corner = freq_corner, freq_sample = freq_sample)
    
    context = zmq.Context()
    most_recent_stream = MRStream(port_publish, topic_publish, context)
    plot_socket = generate_publisher(port_plot, context)

    i = 0
    while True:
        data = most_recent_stream.receive()
        if is_stop_data(data):
            plot_socket.send_string(topic_plot, zmq.SNDMORE)
            plot_socket.send_pyobj(data, zmq.SNDMORE)
            break
        
        data_channel = mean_subtract(data[0, :], data[0, channel])
        filt_data = filt.filter(data_channel)
        
        tracker.update(filt_data)
        is_stim = tracker.decide_stim()

        if is_stim:
            p.Play(wait = False)

        plot_socket.send_string(topic_plot, zmq.SNDMORE)
        plot_socket.send_pyobj(filt_data, zmq.SNDMORE)
        plot_socket.send_pyobj(is_stim)

        i+=1

    print(f'Analysed {i} samples')
    sleep(1)  # Gives enough time to the subscribers to update their status
    most_recent_stream.close()
    plot_socket.close()
