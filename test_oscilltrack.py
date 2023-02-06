import numpy as np
import matplotlib.pyplot as plt

from eegvibe import Oscilltrack

t_final = 2
t_step = 0.001
t = np.arange(0, t_final, t_step)
f1 = 10
f2 = 20
f3 = 50

signal = 2.5*np.sin(2*np.pi*f1*t) + 2*np.sin(2*np.pi*f2*t + np.pi/6) + 0.2 * np.sin(2*np.pi*f3*t)

f_c = 10
gamma = 125 * t_step
d = []

o = Oscilltrack(gamma, f_c, 1/t_step)

for i in range(0, len(signal)):

    Delta = o.pred_error(signal[i])
    d.append(Delta)

    o.update(signal[i])
    print(o.calc_phase())

plt.plot(t, d)
plt.show()