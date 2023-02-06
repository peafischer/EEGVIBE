import numpy as np
from math import atan2

class Oscilltrack:
    a = 0.0
    b = 0.0
    re = 0.0
    im = 0.0
    theta = 0.0
    sinv = 0.0
    cosv = 1.0

    def __init__(self, gamma, fc, fs) -> None:
        self.w = 2 * np.pi * fc / fs
        self.gamma = gamma

    def update(self, data):
        
        Delta = self.pred_error(data)
        self.a += self.gamma * Delta * self.sinv
        self.b += self.gamma * Delta * self.cosv

        self.theta += self.w
        # Wrap theta in the range [-pi, pi] for numerical stability
        #if self.theta >= np.pi:
        #   self.theta -= 2*np.pi

        self.sinv = np.sin(self.theta)
        self.cosv = np.cos(self.theta)
        self.re = self.a * self.sinv + self.b * self.cosv
        self.im = self.b * self.sinv - self.a * self.cosv 

    def pred_error(self, data):
        # Calculates the error between the predicted signal value and the actual data at a timestep.
        # Used internally in the update function to update self.a and self.b .
        # This is a separate function for debug purposes.
        return data - self.re
    
    def phase(self):
        return atan2(self.im, self.re)