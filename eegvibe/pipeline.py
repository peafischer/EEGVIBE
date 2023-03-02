from multiprocessing import Process
import threading
from time import sleep, time

from eegvibe import (DataIterator, plot_stream, tracking, replay, write_stream, find_filename, HighPassFilter, Oscilltrack,
                     stream_to_publish, CLStimulator, init_CLStimulator, SemiCLStimulator, init_SemiCLStimulator)


def run_tracking(freq_sample, freq_target, phase_target, freq_high_pass, oscilltrack_suppresion,
        is_CL_stim, N_pulses, pulse_duration, ITI, IPI, stim_device_ID,
        channel_track, channels_ref, channels_EMG,
        subject_ID, N_plot_samples, plot_labels, recording_duration = 10,
        filename_data = None):

    port = 5555
    topic = 'sample'
    plot_port = 5556
    plot_topic = 'plot'

    out_path = './out_data/'
    file_data = find_filename(subject_ID, out_path, 'hdf5')
    file_stim = find_filename(subject_ID, out_path, 'pkl')
    
    # TO DO :
    # change freq_sample to final_freq_sample after sampling frequency is resolved via get_freq_sample()
    tracker = Oscilltrack(
        freq_target = freq_target, 
        phase_target = phase_target, 
        freq_sample = freq_sample, 
        suppression_cycle = oscilltrack_suppresion
    )

    if is_CL_stim: 
        stim = CLStimulator(
            N_pulses_stim = 1, 
            N_stim_train = N_pulses, 
            ITI = ITI, 
            pulse_duration = pulse_duration, 
            IPI = IPI, 
            device_ID = stim_device_ID
        )
    else:
        stim = SemiCLStimulator(
            N_pulses = N_pulses, 
            ITI = ITI, 
            pulse_duration = pulse_duration, 
            IPI = IPI, 
            device_ID = stim_device_ID
        )

    filter_track = HighPassFilter(
        freq_corner = freq_high_pass, 
        freq_sample = freq_sample
    )
    filters_EMG = [HighPassFilter(freq_corner = freq_high_pass, freq_sample = freq_sample) for _ in range(len(channels_EMG))]

    analysis_process = Process(
        target=tracking, 
        args=(port, topic, plot_port, plot_topic, tracker, stim, filter_track, filters_EMG), 
        kwargs={
            'filename_stim' : file_stim, 
            'channel_track' : channel_track, 
            'channels_ref' : channels_ref, 
            'channels_EMG' : channels_EMG
        }
    )
    analysis_process.start()

    saver_process = threading.Thread(target=write_stream, args=(port, topic, file_data))
    saver_process.start()

    plot_process = Process(
        target=plot_stream, 
        args=(plot_port, plot_topic),
        kwargs={'n_samples' : N_plot_samples, 'labels' : plot_labels}
    )
    plot_process.start()
    
    stop_stream_event = threading.Event()
    if filename_data is None:
        read_thread = threading.Thread(target=stream_to_publish, args=(freq_sample, stop_stream_event, port, topic))
        read_thread.start()
    else:
        data_iter = DataIterator(
            n_samples = 8, 
            freq_sample = freq_sample, 
            data_file = filename_data
        )
        read_thread = threading.Thread(target=data_iter.publish_data, args=(port, topic))
        read_thread.start()
    

    t0 = time()
    while time()-t0 < recording_duration:
        print('Still acquiring')
        sleep(1) 
    
    data_iter.stop = True
    stop_stream_event.set()    
    plot_process.join()
    saver_process.join()
    analysis_process.join()
    read_thread.join()


def run_replay(freq_sample, freq_target, phase_target, freq_high_pass, oscilltrack_suppresion,
        is_CL_stim, filename_stim,
        channel_track, channels_ref, channels_EMG,
        N_plot_samples, plot_labels, recording_duration = 10):
    n = 1
    file = './test_data/tst_10.csv'

    port = 5555
    topic = 'sample'
    plot_port = 5556
    plot_topic = 'plot'

    fs = filename_stim.split('.')
    file_data = '.'.join(fs[:-1]) + 'REPLAY' + '.hdf5'

    data_iter = DataIterator(n_samples=n, sampling_rate=freq_sample, data_file=file)
    
    if is_CL_stim: 
        stim = init_CLStimulator(filename_stim)
    else:
        stim = init_SemiCLStimulator(filename_stim)

    filter_track = HighPassFilter(
        freq_corner = freq_high_pass, 
        freq_sample = freq_sample
    )
    filters_EMG = [HighPassFilter(freq_corner = 8, freq_sample = 1000) for _ in range(len(channels_EMG))]

    analysis_process = Process(
        target=replay, 
        args=(port, topic, plot_port, plot_topic, stim, filter_track, filters_EMG), 
        kwargs={
            'channel_track' : channel_track, 
            'channels_ref' : channels_ref, 
            'channels_EMG' : channels_EMG
        }
    )
    analysis_process.start()

    saver_process = threading.Thread(target=write_stream, args=(port, topic, file_data))
    saver_process.start()

    plot_process = Process(
        target=plot_stream, 
        args=(plot_port, plot_topic),
        kwargs={'n_samples' : N_plot_samples, 'labels' : plot_labels}
    )
    plot_process.start()
    
    #read_thread = threading.Thread(target=data_iter.publish_data, args=(port, topic))
    #read_thread.start()
    
    stop_stream_event = threading.Event()
    read_thread = threading.Thread(target=stream_to_publish, args=(freq_sample, stop_stream_event, port, topic))
    read_thread.start()
    
    t0 = time()
    while time()-t0 < recording_duration:
        print('Still acquiring')
        sleep(1) 
    
    data_iter.stop = True
    stop_stream_event.set()    
    plot_process.join()
    saver_process.join()
    analysis_process.join()
    read_thread.join()
