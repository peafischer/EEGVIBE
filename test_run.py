from multiprocessing import Queue, Process, Event
import threading

from time import sleep, time

from eegvibe import DataIterator, plot_stream, track_phase, write_stream, publish_from_queue, stream_to_queue

if __name__ == '__main__':
    n = 1
    AMP_SR = 1000   # Hz
    channel = 0
    file = './test_data/tst_10.csv'

    port = 5555
    topic = 'sample'
    plot_port = 5556
    plot_topic = 'plot'

    data_iter = DataIterator(n_samples=n, sampling_rate=AMP_SR, data_file=file)

    pub_queue = Queue()
    stop_event = Event()
    stop_stream_event = threading.Event()
    
    data_thread = threading.Thread(target=data_iter.acquire_data, args=(pub_queue,))
    data_thread.start()
    
    #data_thread = threading.Thread(target=stream_to_queue, args = (pub_queue, stop_stream_event))
    #data_thread.start()
    
    publisher_process = Process(target=publish_from_queue, args=(pub_queue, stop_event, port))
    publisher_process.start()

    analyzer_process = Process(target=track_phase, args=(port, topic, plot_port, plot_topic), kwargs={'channels_ms' : range(0,2), "channels_EMG" : [1,2]})
    analyzer_process.start()

    saver_process = threading.Thread(target=write_stream, args=('tst', port, topic))
    saver_process.start()

    plot_process = Process(target=plot_stream, args=(plot_port, plot_topic), kwargs={'labels' : ["Track", "EMG1", "EMG2"]})
    plot_process.start()
    
    t0 = time()
    while time()-t0 < 15:
        print('Still acquiring')
        sleep(1) 
    
    data_iter.stop = True
    pub_queue.put({'topic': 'sample', 'data': 'stop'})
    stop_stream_event.set()
    data_thread.join()
    analyzer_process.join()
    stop_event.set()
    publisher_process.join()
    saver_process.join()
    plot_process.join()
    print('Bye')
