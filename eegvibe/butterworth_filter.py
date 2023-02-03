import numpy as np
from scipy.signal import butter, filtfilt
import pandas as pd

def butter_bandpass(lowcut, highcut, fs, order=5):
    return butter(order, [lowcut, highcut], fs=fs, btype='band')

def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    padding_length = 3 * max(len(a), len(b))
    y = filtfilt(b, a, data, padlen = padding_length)
    return y

def mean_subtract(array):
    mean = np.mean(array)
    array -= mean
    return array

def prepare_filter(f_low, f_high, sampling_rate, f_order):
    def butterworth_filter(data):
        data = mean_subtract(data)
        filtered_data = butter_bandpass_filter(data, f_low, f_high, sampling_rate, f_order)
        return filtered_data

    return butterworth_filter
