import audiomath as am
import time

am.BackEnd.Load('PsychToolboxInterface') # requires PsychToolbox to be installed

def generate_player(N_pulses, pulse_duration, IPI):

    s = am.Sound(fs=44100).GenerateWaveform(duration_msec = pulse_duration, freq_hz=440)

    pulse_train = []
    for i in range(0, N_pulses):
        pulse_train.append(s)
        pulse_train.append(IPI)

    p = am.Player(am.Concatenate(pulse_train), device = 0)
    return p

def generate_player_single(pulse_duration):
    s = am.Sound(fs=44100).GenerateWaveform(duration_msec = pulse_duration, freq_hz=440)
    p = am.Player(s, device = 0)
    return p

def test_player(p):
    p.Play(wait = True)

def test_player_single(p, N_pulses, IPI):
    i = 1
    while i <= N_pulses:
        p.Play(wait = True)
        time.sleep(IPI)
        i += 1
