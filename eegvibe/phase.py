def find_poi(data, rise_fall_ctrl):
    # poi: point of interest for stimulation
    if (abs(rise_fall_ctrl) == 2):  # look for rising or descending phase
        sign_data     = np.sign(data)  
        zero_crossing = np.diff(sign_data, 1) == rise_fall_ctrl  # 2 when detecting the zero-crossing for the rising slope, -2 for the descending slope     
        return np.where(zero_crossing)[0]
    elif rise_fall_ctrl == 1:         
        sign_diff_data = np.sign(np.diff(data, 1))
        peak_detect = np.diff(sign_diff_data, 1) == -2
        return np.where(peak_detect)[0]            
    elif rise_fall_ctrl == -1: 
        sign_diff_data = np.sign(np.diff(data, 1))       
        trough_detect = np.diff(sign_diff_data, 1) == 2
        return np.where(trough_detect)[0]
    else:
        raise Exception("Invalid flag number, please choose rise_fall_ctrl in {-2, -1, 1, 1}")

def prepare_decide_stim(amp_thrs_perc, amp_sampling_rate, min_time_diff_pulses, ITI, n_stim_per_train, rise_fall_ctrl, sub_window_width):
    def decide_stim(data, cnt, time_elapsed, time_stamp, n_lag_samples):
        '''
        KEY function which runs the phase-detection algorithm
        '''
    
        index = len(data) - n_lag_samples # we focus on the point located half a cycle before the end of the streamed data, as our filter might give distorted results for later points

        # ==============================================
        # Option 1) Based on the phase
        #phase_signal = np.angle(hilbert(data))
        #signData     = np.sign(phase_signal[int(index- sub_window_width/2): int(index + sub_window_width/2)])
        
        # ==============================================
        # Option 2) Maybe faster, but more spurious detection, based on the filtered data but without extracting phase

        data_ampl = np.abs(hilbert(data))  
        data_ampl_thrs = np.percentile(data_ampl, amp_thrs_perc)

        idx_slice = slice(int(index - sub_window_width/2), int(index + sub_window_width/2))
        data_window = data[idx_slice]
        data_ampl_window = data_ampl[idx_slice]

        if np.median(data_ampl_window) > data_ampl_thrs:
            idx_poi = find_poi(data_window, rise_fall_ctrl)
                    
            if idx_poi.size and (time_elapsed > min_time_diff_pulses) and (cnt <= n_stim_per_train):
                idx = idx_poi[0] # Get the first POI found
                delay = idx/amp_sampling_rate
                time_stamp += delay
                return True
            else:
                return False
        else:
            return False
                        
    return decide_stim
