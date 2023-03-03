from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

import random

from collections import deque

import zmq

import numpy as np

from .connect import generate_subscriber, is_stop_data, SerializingContext
from .read import DataIterator

def update_plot(plot_refs, track_queue, EMG_queues, socket, timer):
    topic = socket.recv_string()
    #data_track = socket.recv_pyobj()
    data_track = socket.recv_array()
    if not is_stop_data(data_track):
        track_queue.append(data_track)
        plot_refs[0].setData(track_queue)
    else:
        timer.stop()

def update_plot_extended(plot_refs, track_queue, EMG_queues, socket, timer):
    topic = socket.recv_string()
    #data_track = socket.recv_pyobj()
    #data_EMG = socket.recv_pyobj()
    data_track = socket.recv_array()
    data_EMG = socket.recv_array()
    if not is_stop_data(data_track):
        track_queue.append(data_track)
        plot_refs[0].setData(track_queue)

        for i, pr in enumerate(plot_refs[1:]):
            EMG_queues[i].append(data_EMG[i])
            pr.setData(EMG_queues[i])
    else:
        timer.stop()
 
def plot_stream(port, topic, 
    n_samples = 200, autoscale = False, y_range = (-0.002, 0.002), t_update = 0, 
    title = "EEG Stream", labels = ["Tracked channel"]):

    #context = zmq.Context()
    context = SerializingContext()
    socket = generate_subscriber(port, topic, context)

    app = QtWidgets.QApplication([])
    pw = pg.PlotWidget()
    p = pw.plotItem
    p.setTitle(title)

    #cm = pg.colormap.get('CET-C7s')
    #colors = cm.getColors()
    colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'w']
    #color_idx = np.round(np.linspace(0, len(colors)-1, len(labels))).astype(int)

    x = np.arange(0, n_samples)
    data_track = deque([0.0]*n_samples, maxlen = n_samples)
    data_EMG = [deque([0.0]*n_samples, maxlen = n_samples) for _ in range(len(labels) - 1)]
    
    if not autoscale:
        p.disableAutoRange()
        p.setRange(xRange = (0, n_samples), yRange = y_range)

    p.addLegend()
    plot_refs = [p.plot(x, data_track, pen = pg.mkPen(color = colors[0]), name = labels[0])]
    #plot_refs = [p.plot(x, data_track, name = labels[0])]
    
    if len(labels) > 1:
        for i, label in enumerate(labels[1:]):
            plot_refs.append(p.plot(x, data_EMG[i], pen = pg.mkPen(color = colors[i+1]), name = label))
            #plot_refs.append(p.plot(x, data_EMG[i], name = label))
        update_func = update_plot_extended
    else:
        update_func = update_plot

    timer = QtCore.QTimer()
    timer.setInterval(t_update)
    timer.timeout.connect(lambda: update_func(plot_refs, data_track, data_EMG, socket, timer))
    timer.start() 

    pw.show()
    app.exec()
    socket.close()

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
    