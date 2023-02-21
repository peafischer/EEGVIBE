import audiomath as am
import time

am.BackEnd.Load('PsychToolboxInterface') # requires PsychToolbox to be installed

def generate_player(N_pulses, pulse_duration, IPI):

    s = am.Sound(fs=44100).GenerateWaveform(duration_msec = pulse_duration, freq_hz=440)

    pulse_train = []
    for i in range(0, N_pulses-1):
        pulse_train.append(s)
        pulse_train.append(IPI)

    pulse_train.append(s)
    p = am.Player(am.Concatenate(pulse_train), device = 2)
   
    return p

def test_player(p):
    p.Play(wait = True)
