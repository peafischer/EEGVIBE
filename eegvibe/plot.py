from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
from collections import deque
import zmq
import numpy as np

from .connect import is_stop_data, SerializingContext, MRStream

def update_plot(plot_refs, track_queue, EMG_queues, EEG_scale_factor, vert_offsets, most_recent_stream, timer):
    data = most_recent_stream.receive()
    if not is_stop_data(data):
        track_queue.append(data[0] * EEG_scale_factor + vert_offsets[0])
        plot_refs[0].setData(track_queue)

        for i, pr in enumerate(plot_refs[1:]):
            EMG_queues[i].append(data[i+1] + vert_offsets[i+1])
            pr.setData(EMG_queues[i])
    else:
        timer.stop()
 
def plot_stream(port, topic, signal_range, n_samples, EEG_scale_factor, autoscale, t_update = 0, 
    title = "EEG Stream", labels = ["Tracked channel"]):

    context = SerializingContext()
    most_recent_stream = MRStream(port, topic, context)

    app = QtWidgets.QApplication([])
    pw = pg.PlotWidget()
    p = pw.plotItem
    p.setTitle(title)

    #cm = pg.colormap.get('CET-C7s')
    #colors = cm.getColors()
    colors = ['g', 'r', 'c', 'm', 'y', 'k', 'w', 'b']
    #color_idx = np.round(np.linspace(0, len(colors)-1, len(labels))).astype(int)
    y_range = (signal_range[0] * len(labels), signal_range[1] * len(labels))
    
    x = np.arange(0, n_samples)
    data_track = deque([0.0]*n_samples, maxlen = n_samples)
    data_EMG = [deque([0.0]*n_samples, maxlen = n_samples) for _ in range(len(labels) - 1)]
    
    if not autoscale:
        p.disableAutoRange()
        p.setRange(xRange = (0, n_samples), yRange = y_range)
    
    r = y_range[1] - y_range[0]
    vert_offsets = np.linspace(y_range[0] + r/4, y_range[0] + 3*r/4, len(labels))
    
    p.addLegend()
    plot_refs = [p.plot(x, data_track, pen = pg.mkPen(color = colors[0]), name = labels[0])]
    
    for i, label in enumerate(labels[1:]):
        plot_refs.append(p.plot(x, data_EMG[i], pen = pg.mkPen(color = colors[i+1]), name = label))

    timer = QtCore.QTimer()
    timer.setInterval(t_update)
    timer.timeout.connect(lambda: update_plot(plot_refs, data_track, data_EMG, EEG_scale_factor, vert_offsets, most_recent_stream, timer))
    timer.start() 

    pw.show()
    app.exec()
    most_recent_stream.close()
