from multiprocessing import Queue, Process, Event
import threading
import pickle
from time import sleep, time
from eegvibe import (DataIterator, plot_stream, tracking, replay, write_stream, find_filename, HighPassFilter, Oscilltrack,
                     stream_to_publish, CLStimulator, init_CLStimulator, SemiCLStimulator, init_SemiCLStimulator)

if __name__ == '__main__':
    n = 8
    AMP_SR = 1000   # Hz
    file = './test_data/eeg_attend.csv'

    port = 5555
    topic = 'sample'
    plot_port = 5556
    plot_topic = 'plot'

    subject_ID = 1
    out_path = './out_data/'
    file_data = find_filename(subject_ID, out_path, 'hdf5')
    file_stim = find_filename(subject_ID, out_path, 'pkl')

    data_iter = DataIterator(n_samples=n, sampling_rate=AMP_SR, data_file=file)
    
    tracker = Oscilltrack(
        freq_target = 10, 
        phase_target = 0, 
        freq_sample = AMP_SR, 
        suppression_cycle = 0.8
    )

    
    stim = CLStimulator(
        N_pulses_stim = 1, 
        N_stim_train = 50, 
        ITI = 1.0, 
        pulse_duration = 0.02, 
        IPI = 0.2, 
        device_ID = 1
    )
    
    """
    stim = SemiCLStimulator(
        N_pulses = 30, 
        ITI = 0.7, 
        pulse_duration = 0.1, 
        IPI = 0.2, 
        device_ID = 1
    )
    """

    filt = HighPassFilter(
        freq_corner = 8, 
        freq_sample = AMP_SR
    )

    saver_process = threading.Thread(target=write_stream, args=(port, topic, file_data))
    saver_process.start()

    analysis_process = Process(
        target=tracking, 
        args=(port, topic, plot_port, plot_topic, tracker, stim, filt, filt), 
        kwargs={'filename_stim' : file_stim, 'channel_track' : 14, 'channels_ref' : range(0,31), "channels_EMG" : [32]}
    )
    analysis_process.start()

    plot_process = Process(
        target=plot_stream, 
        args=(plot_port, plot_topic),
        kwargs={'n_samples' : 1000, 'labels' : ["Track", "EMG1"]}
    )
    plot_process.start()
    
    read_thread = threading.Thread(target=data_iter.publish_data, args=(port, topic))
    read_thread.start()

    #stop_stream_event = threading.Event()
    #read_thread = threading.Thread(target=stream_to_publish, args=(AMP_SR, stop_stream_event, port, topic))
    #read_thread.start()
    
    t0 = time()
    while time()-t0 < 10:
        print('Still acquiring')
        sleep(1) 
    
    data_iter.stop = True
    #stop_stream_event.set()    
    plot_process.join()
    analysis_process.join()
    saver_process.join()
    read_thread.join()
