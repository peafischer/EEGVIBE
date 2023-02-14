import numpy as np
import pandas as pd
import time

class DataIterator:
    def __init__(self, n_samples, sampling_rate, data_file):
        # channel is assumed to be zero-indexed
        self.n_samples = n_samples
        self.sampling_rate = sampling_rate
        self.counter = 0
        self.stop = False

        D = np.array(pd.read_csv(data_file))
        self.data = D[:, :]

        self.n_rows = len(self.data)

    def __iter__(self):
        return self

    def __next__(self):
        idx_start = self.n_samples * self.counter
        idx_end = idx_start + self.n_samples
        if idx_end <= self.n_rows:
            time.sleep(self.n_samples/self.sampling_rate)   
            self.counter += 1

            if ((self.n_samples + 1) * self.counter) > self.n_rows:
                self.reset()

            next_data = self.data[idx_start:idx_end]
            return next_data
        else:
            self.counter = 0 # reset iterator
            raise StopIteration

    def acquire_data(self, queue):
        while not self.stop:
            queue.put({'topic': 'sample', 'data': next(self)})
            
    def reset(self):
        self.counter = 0
