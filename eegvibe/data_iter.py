import numpy as np
import pandas as pd
import time

class DataIterator:
    def __init__(self, n_samples, sampling_rate, channel, data_file):
        # channel is assumed to be zero-indexed
        self.n_samples = n_samples
        self.sampling_rate = sampling_rate
        self.counter = 0

        D = np.array(pd.read_csv(data_file))
        self.data = D[:, channel]

        self.n_rows = len(self.data)

    def __iter__(self):
        return self

    def __next__(self):
        idx_start = self.n_samples * self.counter
        idx_end = idx_start + self.n_samples
        if idx_end <= self.n_rows:
            time.sleep(self.n_samples/self.sampling_rate)      
            self.counter += 1
            next_data = self.data[idx_start:idx_end]
            return next_data
        else:
            raise StopIteration
