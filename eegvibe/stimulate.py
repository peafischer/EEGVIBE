import audiomath as am
import pickle
from time import sleep

am.BackEnd.Load('PsychToolboxInterface') # requires PsychToolbox to be installed

def generate_player(N_pulses, pulse_duration, IPI, device_ID):

    s = am.Sound(fs=44100).GenerateWaveform(duration_msec = pulse_duration*1000, freq_hz=440)

    pulse_train = []
    for _ in range(0, N_pulses-1): 
        pulse_train.append(s)
        pulse_train.append(IPI)

    pulse_train.append(s)
    p = am.Player(am.Concatenate(pulse_train), device = device_ID)
   
    return p

def test_player(p):
    p.Play(wait = True)

class Stimulator:
    def __init__(self, device_ID, init_time = am.Seconds(), stim_times = []):
        self.device_ID = device_ID
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

class CLStimulator(Stimulator):
    def __init__(self, N_pulses_stim, N_stim_train, pulse_duration, IPI, ITI, device_ID, init_time=am.Seconds(), stim_times=[]):
        super().__init__(device_ID, init_time, stim_times)
        self.pulse_duration = pulse_duration
        self.IPI = IPI
        self.N_stim_current = 0
        self.N_pulses_stim = N_pulses_stim
        self.N_stim_train = N_stim_train
        self.ITI = ITI
        self.suppression_time = init_time
        self.train_duration = IPI * (N_pulses_stim - 1) + pulse_duration * N_pulses_stim

    def stimulate(self):
        if self.N_stim_current >= self.N_stim_train:
            self.suppression_time = am.Seconds()
            self.N_stim_current = 0
        elif (self.suppression_time + self.train_duration + self.ITI <= am.Seconds()):
            super().stimulate()
            self.N_stim_current += 1
    
    def replay(self):
        return super().replay()
    
    def generate_player(self):
        self.player = generate_player(self.N_pulses_stim, self.pulse_duration, self.IPI, self.device_ID)

    def write_params(self, filename):
        with open(filename, 'wb') as file:
            d = {
                'N_pulses_stim' : self.N_pulses_stim,
                'N_stim_train' : self.N_stim_train, 
                'pulse_duration' : self.pulse_duration, 
                'IPI' : self.IPI,
                'ITI' : self.ITI,
                'device_ID' : self.device_ID,
                'init_time' : self.init_time,
                'stim_times' : self.stim_times
            }
            pickle.dump(d, file, protocol = pickle.HIGHEST_PROTOCOL)      

class SemiCLStimulator(Stimulator):
    def __init__(self, N_pulses, pulse_duration, IPI, ITI, device_ID, init_time=am.Seconds(), stim_times=[]):
        super().__init__(device_ID, init_time, stim_times)
        self.pulse_duration = pulse_duration
        self.IPI = IPI
        self.N_stim_current = 0
        self.N_pulses = N_pulses
        self.ITI = ITI
        self.suppression_time = -10000
        self.train_duration = IPI * (N_pulses - 1) + pulse_duration * N_pulses

    def stimulate(self):
        if (self.suppression_time + self.train_duration + self.ITI <= am.Seconds()):
            super().stimulate()
            self.suppression_time = am.Seconds()
    
    def replay(self):
        return super().replay()
    
    def generate_player(self):
        self.player = generate_player(self.N_pulses, self.pulse_duration, self.IPI, self.device_ID)

    def write_params(self, filename):
        with open(filename, 'wb') as file:
            d = {
                'N_pulses' : self.N_pulses,
                'pulse_duration' : self.pulse_duration, 
                'IPI' : self.IPI,
                'ITI' : self.ITI,
                'device_ID' : self.device_ID,
                'init_time' : self.init_time,
                'stim_times' : self.stim_times
            }
            pickle.dump(d, file, protocol = pickle.HIGHEST_PROTOCOL)  
     
def init_CLStimulator(filename):
     with open(filename, 'rb') as f:
        d = pickle.load(f)
        s = CLStimulator(
            N_pulses_stim = d['N_pulses_stim'], 
            N_stim_train = d['N_stim_train'],
            ITI = d['ITI'], 
            IPI = d['IPI'], 
            pulse_duration = d['pulse_duration'], 
            device_ID = d['device_ID'], 
            stim_times = d['stim_times']
        )
        return s

def init_SemiCLStimulator(filename):
     with open(filename, 'rb') as f:
        d = pickle.load(f)
        s = SemiCLStimulator(
            N_pulses = d['N_pulses'], 
            ITI = d['ITI'], 
            IPI = d['IPI'], 
            pulse_duration = d['pulse_duration'], 
            device_ID = d['device_ID'], 
            stim_times = d['stim_times']
        )
        return s