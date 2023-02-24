import zmq
import threading

def is_stop_data(data):
    return isinstance(data, str)

def generate_publisher(port, context):
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://*:%s" % port)

    return socket

def generate_subscriber(port, topic, context):
    socket = context.socket(zmq.SUB)
    socket.connect(f"tcp://localhost:{port}")
    topic_filter = topic.encode('utf-8')
    socket.setsockopt(zmq.SUBSCRIBE, topic_filter)

    return socket

class MRStream:
    # Most Recent Stream class.
    def __init__(self, port, topic, context):
        self.port = port
        self.topic = topic
        self.context = context
        self.stop = False
        self.data_ready = threading.Event()
        self.thread = threading.Thread(target = self.run, args=())
        self.thread.daemon = True
        self.thread.start()

    def receive(self, timeout=15.0):
        flag = self.data_ready.wait(timeout = timeout)

        if not flag:
            raise TimeoutError(
                "Timeout while reading from subscriber tcp://localhost:{}".format(self.port))

        self.data_ready.clear()
        return self.data

    def run(self):
        socket = generate_subscriber(self.port, self.topic, self.context)
        while not self.stop:
            topic = socket.recv_string()
            self.data = socket.recv_pyobj() 
            self.data_ready.set()
        socket.close()

    def close(self):
        self.stop = True
