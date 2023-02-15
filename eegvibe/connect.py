import zmq

def generate_publisher(port, context):
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://*:%s" % port)

    return socket

def generate_subscriber(port, topic, context):
    socket = context.socket(zmq.SUB)
    socket.connect(f"tcp://localhost:{port}")
    topic_filter = topic.encode('utf-8')
    socket.setsockopt(zmq.SUBSCRIBE, topic_filter)
    socket.setsockopt(zmq.SUBSCRIBE, ''.encode('utf-8'))

    return socket
    