from eegvibe import run_tracking, run_replay
from time import sleep

if __name__ == '__main__':
    run_tracking(freq_sample = 1000, freq_target = 50, phase_target = 0.0, freq_high_pass = 8, oscilltrack_suppresion = 0.8,
        is_CL_stim = True, N_pulses = 10, pulse_duration = 0.1, ITI = 0.5, IPI = 0.2, stim_device_ID = 2,
        channel_track = 14, channels_ref = range(0,31), channels_EMG = [32,33],
        N_plot_samples = 1000, plot_labels = ["Track", "EMG1", "EMG2"], recording_duration = 10,
        subject_ID = 4
        )
    
    sleep(5)
    print('Starting replay')

    run_replay(freq_sample = 1000, freq_target = 50, phase_target = 0.0, freq_high_pass = 8, oscilltrack_suppresion = 0.8,
        is_CL_stim = True, filename_stim = './out_data/01_03_2023_4.pkl',
        channel_track = 14, channels_ref = range(0,31), channels_EMG = [32,33],
        N_plot_samples = 1000, plot_labels = ["Track", "EMG1", "EMG2"], recording_duration = 10
        )