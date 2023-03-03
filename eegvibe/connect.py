import zmq
import threading
import numpy as np
from typing import Any, Dict, cast

class SerializingSocket(zmq.Socket):
    """A class with some extra serialization methods
    send_zipped_pickle is just like send_pyobj, but uses
    zlib to compress the stream before sending.
    send_array sends numpy arrays with metadata necessary
    for reconstructing the array on the other side (dtype,shape).
    """
    def send_array(
        self, A: np.ndarray, flags: int = 0, copy: bool = True, track: bool = False
    ) -> Any:
        """send a numpy array with metadata"""
        md = dict(
            dtype=str(A.dtype),
            shape=A.shape,
        )
        self.send_json(md, flags | zmq.SNDMORE)
        return self.send(A, flags, copy=copy, track=track)

    def recv_array(
        self, flags: int = 0, copy: bool = True, track: bool = False
    ) -> np.ndarray:
        """recv a numpy array"""
        md = cast(Dict[str, Any], self.recv_json(flags=flags))
        msg = self.recv(flags=flags, copy=copy, track=track)
        A = np.frombuffer(msg, dtype=md['dtype'])  # type: ignore
        return A.reshape(md['shape'])


class SerializingContext(zmq.Context[SerializingSocket]):
    _socket_class = SerializingSocket

def is_stop_data(data):
    #return isinstance(data, str)
    return not data.size

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
        #socket = generate_subscriber(self.port, self.topic, self.context)
        socket = generate_subscriber(self.port, self.topic, self.context)

        while not self.stop:
            topic = socket.recv_string()
            #self.data = socket.recv_pyobj() 
            self.data = socket.recv_array(copy = False)
            self.data_ready.set()
        socket.close()

    def close(self):
        self.stop = True

def send_array(socket, A, flags=0, copy=True, track=False):
    """send a numpy array with metadata"""
    md = dict(
        dtype=str(A.dtype),
        shape=A.shape,
    )
    socket.send_json(md, flags | zmq.SNDMORE)
    return socket.send(A, flags, copy=copy, track=track)


def recv_array(socket, flags=0, copy=True, track=False):
    """recv a numpy array"""
    md = socket.recv_json(flags=flags)
    msg = socket.recv(flags=flags, copy=copy, track=track)
    buf = memoryview(msg)
    A = np.frombuffer(buf, dtype=md["dtype"])
    return A.reshape(md["shape"])
