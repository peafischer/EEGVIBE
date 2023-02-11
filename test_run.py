from multiprocessing import Queue, Process, Event
from threading import Thread

from time import sleep, time

from eegvibe import DataIterator, plot_stream, track_phase, write_stream, publisher

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

    publisher_process = Process(target=publisher, args=(pub_queue, stop_event, port))
    publisher_process.start()

    data_thread = Thread(target=data_iter.acquire_data, args=(pub_queue,))
    data_thread.start()

    analyzer_process = Process(target=track_phase, args=(port, topic, plot_port, plot_topic))
    analyzer_process.start()

    saver_process = Process(target=write_stream, args=('tst', port, topic))
    saver_process.start()

    plot_process = Process(target=plot_stream, args=(plot_port, plot_topic))
    plot_process.start()
    
    t0 = time()
    while time()-t0 < 3:
        print('Still acquiring')
        sleep(1) 
    
    data_iter.stop = True
    pub_queue.put({'topic': 'sample', 'data': 'stop'})
    data_thread.join()
    analyzer_process.join()
    stop_event.set()
    publisher_process.join()
    saver_process.join()
    plot_process.join()
    print('Bye')
