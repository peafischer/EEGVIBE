from multiprocessing import Queue, Process, Event
import threading
import pickle
from time import sleep, time

from eegvibe import (DataIterator, plot_stream, analysis, write_stream, find_filename, HighPassFilter, Oscilltrack,
                     stream_to_publish, CLStimulator, init_CLStimulator, SemiCLStimulator, init_SemiCLStimulator)

if __name__ == '__main__':
    n = 1
    AMP_SR = 1000   # Hz
    channel = 0
    file = './test_data/tst_10.csv'

    port = 5555
    topic = 'sample'
    plot_port = 5556
    plot_topic = 'plot'

    out_path = './out_data/'
    file_data = find_filename(out_path, 'hdf5')
    file_stim = find_filename(out_path, 'pkl')

    data_iter = DataIterator(n_samples=n, sampling_rate=AMP_SR, data_file=file)
    
    tracker = Oscilltrack(
        freq_target = 10, 
        phase_target = 0, 
        freq_sample = AMP_SR, 
        suppression_cycle = 0.8
    )

    stim = CLStimulator(
        N_pulses_stim = 1, 
        N_stim_train = 20, 
        ITI = 0.7, 
        pulse_duration = 0.1, 
        IPI = 0.2, 
        device_ID = 2
    )
    """
    stim = SemiCLStimulator(
        N_pulses = 1, 
        ITI = 0.7, 
        pulse_duration = 0.1, 
        IPI = 0.2, 
        device_ID = 2
    )
    """

    filt = HighPassFilter(
        freq_corner = 8, 
        freq_sample = AMP_SR
    )

    read_thread = threading.Thread(target=data_iter.publish_data, args=(port, topic))
    read_thread.start()
    
    #pub_queue = Queue()
    #stop_event = Event()
    #stop_stream_event = threading.Event()

    #data_thread = threading.Thread(target=stream_to_queue, args = (pub_queue, stop_stream_event))
    #data_thread.start()
    #publisher_process = Process(target=publish_from_queue, args=(pub_queue, stop_event, port))
    #publisher_process.start()

    analysis_process = Process(
        target=analysis, 
        args=(port, topic, plot_port, plot_topic, tracker, stim, filt, filt), 
        kwargs={'filename_stim' : file_stim, 'channels_ms' : range(0,2), "channels_EMG" : [1,2]}
    )
    analysis_process.start()

    saver_process = threading.Thread(target=write_stream, args=(port, topic, file_data))
    saver_process.start()

    plot_process = Process(
        target=plot_stream, 
        args=(plot_port, plot_topic),
        kwargs={'n_samples' : 1000, 'labels' : ["Track", "EMG1", "EMG2"]}
    )
    plot_process.start()
    
    t0 = time()
    while time()-t0 < 5:
        print('Still acquiring')
        sleep(1) 
    
    data_iter.stop = True
    #pub_queue.put({'topic': 'sample', 'data': 'stop'})
    #stop_stream_event.set()    
    #stop_event.set()
    #publisher_process.join()
    plot_process.join()
    saver_process.join()
    analysis_process.join()
    read_thread.join()

    sleep(2)
    print('Starting replay')
    s = init_CLStimulator(file_stim)
    s.generate_player()
    s.replay()
    print(s.stim_times)