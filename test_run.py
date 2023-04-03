from eegvibe import run_tracking, run_replay
from time import sleep
import numpy

if __name__ == '__main__':
    
    partic_ID = 1
        
    print("STARTING - PLEASE WAIT")
    
    condition = 3  
    replay = 1
    sound_label = 'test'


    if condition == 1:  # -90 degree, (-pi/2)
        phase = numpy.radians(-90)
    elif condition == 2:  # 180 degree (pi)
        phase = numpy.radians(180)
    elif condition == 3: # +90 degree (pi/2)
        phase = numpy.radians(90)
    elif condition == 4:  # 0 degree (0 rad)
        phase = numpy.radians(0)
        
        
    CHAN_TRACK = 14
    CHAN_REFS =  [8, 9, 19, 20]  # for avg ref: range(0,31)
        
    gamma_param = 0.05 # alternative: 0.005
        
    if not replay:    
        run_tracking(freq_sample = 1000, freq_target = 10, phase_target = phase, freq_high_pass = 3, 
            oscilltrack_suppresion = 0.8, oscilltrack_gamma = gamma_param,
            is_CL_stim = True, N_pulses = 30, pulse_duration = 0.02, ITI = 1, IPI = 0.08, stim_device_ID = 1,  # stim_device_ID needs to be 1 for the Lab PC
            channel_track = CHAN_TRACK, channels_ref =  CHAN_REFS, channels_EMG = [32],  
            N_plot_samples = 500, plot_labels = ["Track", "EMG1"], plot_signal_range = (-0.0002, 0.0002),
            participant_ID = partic_ID, condition_label = sound_label, recording_duration = 10 # ,
            # filename_data = './out_data/06_03_2023_P1_Ch14_FRQ=10Hz_FULL_CL_phase=90_v1.hdf5' 
            )
     
    if replay: 
        run_replay(freq_sample = 1000, freq_high_pass = 3,
            filename_stim = './out_data/07_03_2023_P1_Ch14_FRQ=50Hz_FULL_CL_phase=90_test_v3.pkl',
            channel_track = CHAN_TRACK, channels_ref = CHAN_REFS, channels_EMG = [32],
            N_plot_samples = 500, plot_labels = ["Track", "EMG1"], plot_signal_range = (-0.0002, 0.0002), 
            participant_ID = partic_ID #,
            # filename_data = './out_data/07_03_2023_P1_Ch14_FRQ=10Hz_FULL_CL_phase=90_v1.hdf5'
            )
