from multiprocessing import Process
import threading
from time import sleep

from .read import DataIterator, stream_to_publish, get_freq_sample, get_impedance, get_channel_names
from .analysis import tracking, replay
from .filter import HighPassFilter
from .oscilltrack import Oscilltrack
from .stimulate import CLStimulator, SemiCLStimulator, init_CLStimulator, init_SemiCLStimulator
from .write import write_stream, find_filename, add_metadata
from .plot import plot_stream

def run_tracking(freq_sample, freq_target, phase_target, freq_high_pass, oscilltrack_suppresion,
        is_CL_stim, N_pulses, pulse_duration, ITI, IPI, stim_device_ID,
        channel_track, channels_ref, channels_EMG,
        N_plot_samples, plot_labels, participant_ID, recording_duration = 10,
        out_path = './out_data/', condition_label = '', filename_data = None,
        amplifier_ID = 0):

    port = 5555
    topic = 'sample'
    plot_port = 5556
    plot_topic = 'plot'

    stop_stream_event = threading.Event()
    if filename_data is None:
        final_freq_sample = get_freq_sample(freq_sample, amplifier_ID)
        impedance_init = get_impedance(amplifier_ID)
        channel_names = get_channel_names(amplifier_ID)

        read_thread = threading.Thread(
            target=stream_to_publish, 
            args=(final_freq_sample, stop_stream_event, port, topic)
        )
    else:
        final_freq_sample = freq_sample
        impedance_init = [0.0 for _ in range(0,32)]
        channel_names = ['' for _ in range(0,32)]

        data_iter = DataIterator(
            n_samples = 8, 
            freq_sample = final_freq_sample, 
            data_file = filename_data
        )
        read_thread = threading.Thread(
            target = data_iter.publish_data, 
            args = (port, topic)
        )
    
    tracker = Oscilltrack(
        freq_target = freq_target, 
        phase_target = phase_target, 
        freq_sample = final_freq_sample, 
        suppression_cycle = oscilltrack_suppresion
    )

    if is_CL_stim: 
        sm = 'FULL_CL'
        stim = CLStimulator(
            N_pulses_stim = 1, 
            N_stim_train = N_pulses, 
            ITI = ITI, 
            pulse_duration = pulse_duration, 
            IPI = IPI, 
            device_ID = stim_device_ID
        )
    else:
        sm = 'SEMI_CL'
        stim = SemiCLStimulator(
            N_pulses = N_pulses, 
            ITI = ITI, 
            pulse_duration = pulse_duration, 
            IPI = IPI, 
            device_ID = stim_device_ID
        )

    filter_track = HighPassFilter(
        freq_corner = freq_high_pass, 
        freq_sample = final_freq_sample
    )
    filters_EMG = [
        HighPassFilter(freq_corner = freq_high_pass, freq_sample = final_freq_sample) 
        for _ in range(len(channels_EMG))
    ]

    filename_out_data = find_filename(
        participant_ID = participant_ID, 
        channel_track = channel_track,
        freq_target = freq_target,
        stim_mode = sm,
        phase_target = phase_target,
        label = condition_label,
        path = out_path,
        format = 'hdf5'
        )    
    
    fs = filename_out_data.split('.')
    filename_stim = '.'.join(fs[:-1]) + '.pkl'

    analysis_process = Process(
        target=tracking, 
        args=(port, topic, plot_port, plot_topic, tracker, stim, filter_track, filters_EMG), 
        kwargs={
            'filename_stim' : filename_stim, 
            'channel_track' : channel_track, 
            'channels_ref' : channels_ref, 
            'channels_EMG' : channels_EMG
        }
    )

    saver_process = threading.Thread(
        target = write_stream, 
        args = (port, topic, filename_out_data)
    )

    plot_process = Process(
        target = plot_stream, 
        args = (plot_port, plot_topic),
        kwargs = {'n_samples' : N_plot_samples, 'labels' : plot_labels}
    )

    analysis_process.start()
    saver_process.start()
    plot_process.start()
    read_thread.start()

    sleep(recording_duration) 
    
    if filename_data is None:
        stop_stream_event.set()
        impedance_final = get_impedance(amplifier_ID)
    else:
        data_iter.stop = True
        impedance_final = [1.0 for _ in range(0,32)]

    plot_process.join()
    saver_process.join()
    analysis_process.join()
    read_thread.join()
    
    metadata_dict = {
        'impedance_init' : impedance_init,
        'impedance_final' : impedance_final,
        'channel_names' : channel_names,
        'channels_ref' : channels_ref,
        'freq_sample' : final_freq_sample,
        'recording_duration' : recording_duration,
        'oscilltrack_suppression' : oscilltrack_suppresion,
        'replay_file' : '',
        'participant_ID' : participant_ID,
        'stim_mode' : sm,
        'N_pulses_per_train' : N_pulses,
        'pulse_duration' : pulse_duration,
        'IPI' : 0.0 if is_CL_stim else IPI,
        'ITI' : ITI,
        'phase_target' : phase_target,
        'freq_target' : freq_target,
        'condition_label' : condition_label
    }
    add_metadata(metadata =  metadata_dict, filename = filename_out_data)

def run_replay(freq_sample, freq_high_pass, is_CL_stim, filename_stim,
        channel_track, channels_ref, channels_EMG,
        N_plot_samples, plot_labels, participant_ID, recording_duration = 10,
        condition_label = '', filename_data = None, amplifier_ID = 0):
    
    port = 5555
    topic = 'sample'
    plot_port = 5556
    plot_topic = 'plot'

    fs = filename_stim.split('.')
    filename_out_data = '.'.join(fs[:-1]) + '_REPLAY' + '.hdf5'

    stop_stream_event = threading.Event()
    if filename_data is None:
        final_freq_sample = get_freq_sample(freq_sample, amplifier_ID)
        impedance_init = get_impedance(amplifier_ID)
        channel_names = get_channel_names(amplifier_ID)

        read_thread = threading.Thread(
            target = stream_to_publish, 
            args = (final_freq_sample, stop_stream_event, port, topic)
        )
    else:
        final_freq_sample = freq_sample
        impedance_init = [0.0 for _ in range(0,32)]
        channel_names = ['' for _ in range(0,32)]

        data_iter = DataIterator(
            n_samples = 8, 
            freq_sample = final_freq_sample, 
            data_file = filename_data
        )
        read_thread = threading.Thread(
            target = data_iter.publish_data, 
            args = (port, topic)
        )
        
    if is_CL_stim: 
        sm = 'FULL_CL'
        stim = init_CLStimulator(filename_stim)
        N_pulses = stim.N_stim_train
    else:
        sm = 'SEMI_CL'
        stim = init_SemiCLStimulator(filename_stim)
        N_pulses = stim.N_pulses

    filter_track = HighPassFilter(
        freq_corner = freq_high_pass, 
        freq_sample = final_freq_sample
    )
    filters_EMG = [
        HighPassFilter(freq_corner = freq_high_pass, freq_sample = final_freq_sample) 
        for _ in range(len(channels_EMG))
    ]

    analysis_process = Process(
        target=replay, 
        args=(port, topic, plot_port, plot_topic, stim, filter_track, filters_EMG), 
        kwargs={
            'channel_track' : channel_track, 
            'channels_ref' : channels_ref, 
            'channels_EMG' : channels_EMG
        }
    )

    saver_process = threading.Thread(
        target = write_stream, 
        args = (port, topic, filename_out_data)
    )
    
    plot_process = Process(
        target = plot_stream, 
        args = (plot_port, plot_topic),
        kwargs = {'n_samples' : N_plot_samples, 'labels' : plot_labels}
    )

    analysis_process.start()
    saver_process.start()
    plot_process.start()
    read_thread.start()

    sleep(recording_duration) 
    
    if filename_data is None:
        stop_stream_event.set()
        impedance_final = get_impedance(amplifier_ID)
    else:
        data_iter.stop = True
        impedance_final= [1.0 for _ in range(0,32)]

    plot_process.join()
    saver_process.join()
    analysis_process.join()
    read_thread.join()

    metadata_dict = {
        'impedance_init' : impedance_init,
        'impedance_final' : impedance_final,
        'channel_names' : channel_names,
        'channels_ref' : channels_ref,
        'freq_sample' : final_freq_sample,
        'recording_duration' : recording_duration,
        'replay_file' : filename_stim,
        'participant_ID' : participant_ID,
        'stim_mode' : sm,
        'N_pulses_per_train' : N_pulses,
        'pulse_duration' : stim.pulse_duration,
        'IPI' : 0.0 if is_CL_stim else stim.IPI,
        'ITI' : stim.ITI,
        'condition_label' : condition_label
    }
    add_metadata(metadata =  metadata_dict, filename = filename_out_data)
