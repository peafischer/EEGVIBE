from multiprocessing import Queue, Process, Event
import threading
import pickle
from time import sleep, time

from eegvibe import DataIterator, plot_stream, analysis, write_stream, find_filename, stream_to_publish, Stimulator

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
        args=(port, topic, plot_port, plot_topic, file_stim), 
        kwargs={'channels_ms' : range(0,2), "channels_EMG" : [1,2], "stim_device_ID" : 1}
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
    with open(file_stim, 'rb') as f:
        d = pickle.load(f)

    s = Stimulator(N_pulses = d['N_pulses'], IPI = d['IPI'], pulse_duration = d['pulse_duration'], device_ID = d['device_ID'], stim_times = d['stim_times'])
    s.replay()
