import audiomath as am

am.BackEnd.Load('PsychToolboxInterface') # requires PsychToolbox to be installed

def generate_sound(N_pulses, pulse_duration, IPI):

    s = am.Sound(fs=44100).GenerateWaveform(duration_msec = pulse_duration*1000, freq_hz=440)

    pulse_train = []
    for i in range(0, N_pulses):
        pulse_train.append(s)
        pulse_train.append(IPI)

    p = am.Player(am.Concatenate(pulse_train), device=2)
    return p

N_pulses = 3
pulse_duration = 0.1 # sec
IPI = 0.2 # sec
ITI = 2.0 # sec

p = generate_sound(N_pulses, pulse_duration, IPI)

p.Play(wait = True)
## keep the script running while sound is playing from script, not REPL
## if PsychToolbox is the chosen backend, it's not needed
#time.sleep(10)  

