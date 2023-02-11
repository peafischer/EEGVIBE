import zmq
from time import sleep
from .connect import generate_publisher

def publisher(queue, event, port):
    context = zmq.Context()
    socket = generate_publisher(port, context)

    while not event.is_set():
        while not queue.empty():
            data = queue.get()  # Should be a dictionary {'topic': topic, 'data': data}
            socket.send_string(data['topic'], zmq.SNDMORE)
            socket.send_pyobj(data['data'])
    sleep(0.005)  # Sleeps 5 milliseconds to be polite with the CPU
    socket.send_string('stop')
    sleep(1)  # Gives enough time to the subscribers to update their status
    socket.close()