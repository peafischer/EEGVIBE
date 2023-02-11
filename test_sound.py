from eegvibe import *

n = 18
AMP_SR = 1000   # Hz
channel = 14
file = './test_data/tst.csv'

FREQ_LOW = 10 # in Hz
FREQ_HIGH= 13 # in Hz
BUTTERWORTH_FLTER_ORDER = 2

a = DataIterator(n_samples=n, sampling_rate=AMP_SR, channel=channel, data_file=file)
f = prepare_filter(f_low=FREQ_LOW, f_high=FREQ_HIGH, sampling_rate=AMP_SR, f_order=BUTTERWORTH_FLTER_ORDER)

N_pulses = 3
pulse_duration = 100 # ms
IPI = 1.0 # sec
ITI = 2.0 # sec

p = generate_player(N_pulses, pulse_duration, IPI)

p_single = generate_player_single(pulse_duration)

test_player_single(p_single, N_pulses, IPI)