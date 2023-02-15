from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

import random

from collections import deque

import zmq

import numpy as np

from .connect import generate_publisher, generate_subscriber
from .read import DataIterator

def update_plot_sync(plot_ref, y, stim_mask, data_iter, channel, timer):
    y.append(next(data_iter)[0, channel])
    stim_mask.append(bool(random.getrandbits(1)))
    plot_ref.setData(y)

def plot_sync():
    n = 1
    AMP_SR = 1000   # Hz
    channel = 0
    file = './tst_10.csv'
    data_iter = DataIterator(n_samples=n, sampling_rate=AMP_SR, data_file=file)

    channel = 0

    app = QtWidgets.QApplication([])
    pw = pg.PlotWidget()
    p = pw.plotItem
    p.setTitle("Stream")

    n_plot_samples = 200
    x = np.arange(0, n_plot_samples)
    y = deque([0.0]*n_plot_samples, maxlen = n_plot_samples)
    stim_mask = deque([False]*n_plot_samples, maxlen = n_plot_samples)

    plot_ref = p.plot(x, y)

    timer = QtCore.QTimer()
    timer.setInterval(0)
    timer.timeout.connect(lambda: update_plot_sync(plot_ref, y, stim_mask, data_iter, channel, timer))
    timer.start() 

    pw.show()
    app.exec()
    
def update_plot(plot_ref, y, x, stim_mask, socket, timer):
    topic = socket.recv_string()
    data = socket.recv_pyobj()
    if not isinstance(data, str):
        is_stim = socket.recv_pyobj()
        y.append(data)
        stim_mask.append(is_stim)
        plot_ref.setData(y)
    else:
        timer.stop()
        
def plot_stream(port, topic):

    context = zmq.Context()
    socket = generate_subscriber(port, topic, context)

    app = QtWidgets.QApplication([])
    pw = pg.PlotWidget()
    p = pw.plotItem
    p.setTitle("Stream")

    n_plot_samples = 20
    x = np.arange(0, n_plot_samples)
    y = deque([0.0]*n_plot_samples, maxlen = n_plot_samples)
    stim_mask = deque([False]*n_plot_samples, maxlen = n_plot_samples)

    plot_ref = p.plot(x, y)

    #stim_ref = axes.vlines(x[stim_mask], 0, 1, color = 'r')

    timer = QtCore.QTimer()
    timer.setInterval(0)
    timer.timeout.connect(lambda: update_plot(plot_ref, y, x, stim_mask, socket, timer))
    timer.start() 

    pw.show()
    app.exec()
    socket.close()
    
def update_plot_from_iter(data_iter, plot_ref, stim_ref, canvas, y, x, stim_mask, channel):
    y.append(next(data_iter)[0, channel])
    stim_mask.append(bool(random.getrandbits(1)))

    plot_ref.set_ydata(y)

    seg_new = [np.array([[x_stim, 0], [x_stim, 1]]) for x_stim in x[stim_mask]]
    stim_ref.set_segments(seg_new)
    
    canvas.draw()
