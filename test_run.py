from eegvibe import run_tracking, run_replay
from time import sleep

if __name__ == '__main__':
    run_tracking(freq_sample = 1000, freq_target = 10, phase_target = 0.0, freq_high_pass = 3, oscilltrack_suppresion = 0.8,
        is_CL_stim = False, N_pulses = 5, pulse_duration = 0.05, ITI = 1.0, IPI = 0.1, stim_device_ID = 1,
        channel_track = 14, channels_ref = range(0,31), channels_EMG = [32, 33],
        N_plot_samples = 1000, plot_labels = ["Track", "EMG1", "EMG2"], recording_duration = 10,
        participant_ID = 1, filename_data = './test_data/eeg_rest.csv', condition_label = 'tst'
        )
    
    """
    sleep(5)
    print('Starting replay')

    run_replay(freq_sample = 1000, freq_high_pass = 3,
        is_CL_stim = False, filename_stim = './out_data/03_03_2023_P1_Ch14_FRQ=10Hz_SEMI_CL_phase=0.0_tst_v2.pkl',
        channel_track = 14, channels_ref = range(0,31), channels_EMG = [32,33],
        N_plot_samples = 1000, plot_labels = ["Track", "EMG1", "EMG2"], recording_duration = 10,
        participant_ID = 1, filename_data = './test_data/eeg_rest.csv'
        )
    """