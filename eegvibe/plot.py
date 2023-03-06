from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

import random

from collections import deque

import zmq

import numpy as np

from .connect import generate_subscriber, is_stop_data, SerializingContext
from .read import DataIterator

def update_plot(plot_refs, track_queue, EMG_queues, EEG_scale_factor, EEG_vertical_offset, socket, timer):
    topic = socket.recv_string()
    #data_track = socket.recv_pyobj()
    data_track = socket.recv_array()
    if not is_stop_data(data_track):
        track_queue.append(data_track[0] * EEG_scale_factor + EEG_vertical_offset)
        plot_refs[0].setData(track_queue)
    else:
        timer.stop()

def update_plot_extended(plot_refs, track_queue, EMG_queues, EEG_scale_factor, EEG_vertical_offset, socket, timer):
    topic = socket.recv_string()
    #data_track = socket.recv_pyobj()
    #data_EMG = socket.recv_pyobj()

    #data_track = socket.recv_array()
    #data_EMG = socket.recv_array()
    data = socket.recv_array()
    if not is_stop_data(data):
        track_queue.append(data[0] * EEG_scale_factor + EEG_vertical_offset)
        plot_refs[0].setData(track_queue)

        for i, pr in enumerate(plot_refs[1:]):
            EMG_queues[i].append(data[i+1])
            pr.setData(EMG_queues[i])
    else:
        timer.stop()
 
def plot_stream(port, topic, 
    n_samples = 200, EEG_scale_factor = 1.0, autoscale = False, y_range = (-0.002, 0.002), t_update = 0, 
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
        EEG_vertical_offset = max(y_range)/4
        p.disableAutoRange()
        p.setRange(xRange = (0, n_samples), yRange = y_range)
    else:
        EEG_vertical_offset = 0.0005

    p.addLegend()
    plot_refs = [p.plot(x, data_track, pen = pg.mkPen(color = colors[0]), name = labels[0])]
    
    if len(labels) > 1:
        for i, label in enumerate(labels[1:]):
            plot_refs.append(p.plot(x, data_EMG[i], pen = pg.mkPen(color = colors[i+1]), name = label))
        update_func = update_plot_extended
    else:
        update_func = update_plot

    timer = QtCore.QTimer()
    timer.setInterval(t_update)
    timer.timeout.connect(lambda: update_func(plot_refs, data_track, data_EMG, EEG_scale_factor, EEG_vertical_offset, socket, timer))
    timer.start() 

    pw.show()
    app.exec()
    socket.close()
