import audiomath as am
from time import sleep

am.BackEnd.Load('PsychToolboxInterface') # requires PsychToolbox to be installed

def generate_player(N_pulses, pulse_duration, IPI, device_ID):

    s = am.Sound(fs=44100).GenerateWaveform(duration_msec = pulse_duration, freq_hz=440)

    pulse_train = []
    for i in range(0, N_pulses-1): 
        pulse_train.append(s)
        pulse_train.append(IPI)

    pulse_train.append(s)
    p = am.Player(am.Concatenate(pulse_train), device = device_ID)
   
    return p

def test_player(p):
    p.Play(wait = True)

class Stimulator:
    def __init__(self, N_pulses, pulse_duration, IPI, device_ID, init_time = am.Seconds(), stim_times = []):
        self.N_pulses = N_pulses
        self.pulse_duration = pulse_duration
        self.IPI = IPI
        self.device_ID = device_ID
        self.player = generate_player(N_pulses, pulse_duration, IPI, device_ID)
        self.init_time = init_time
        self.stim_times = stim_times
    
    def stimulate(self):
        self.player.Play(wait = False)
        self.stim_times.append(am.Seconds() - self.init_time)

    def replay(self):
        t0 = am.Seconds()
        for t in self.stim_times:
            #sleep(t)
            self.player.Play(when = t0 + t, wait = True)
