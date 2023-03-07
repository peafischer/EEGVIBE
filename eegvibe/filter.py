import numpy as np

def mean_subtract(data_all, data_channel):
    return data_channel - np.mean(data_all)

class HighPassFilter:
    x = 0.0

    def __init__(self, freq_corner, freq_sample):
        self.hp = 2.0 * np.pi * freq_corner / freq_sample

    def filter(self, data):
        filt_data = data - self.x
        self.x += self.hp * filt_data
        return filt_data
