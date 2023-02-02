import csv
import os
import time
from datetime import datetime

import audiomath as am
import numpy as np
import pandas as pd

from scipy.signal import hilbert
from butterworth_filter import *

from PySide6 import QtGui, QtCore, QtWidgets
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

from multiprocessing import Process, Manager, Queue
import sched, time, threading


#==========================================
# Constant variables

TEST_MODE = False # If True, then do not try to connect with amplifier but get test data
test_file_path = './main_code/test_data/eeg_2022_12_09_16_03_12_CHAN_14_TIMEOUT_0.043_TRAIN_NR_PULS=10_ITI=0.5_FRQ_10-13Hz_DET=2_NoStimEyesCl.csv'

STIM_INFO = 'Right_ABP_EyesOpen'
               
REPLAY_ON = False
REPLAY_STIM_PTS_FILE = 'data/stim_points_2022_12_20_10_39_31_CHAN_14_TIMEOUT_0.043_TRAIN_NR_PULS=10_ITI=0.5_FRQ_10-13Hz_DET=-1_Right_ABP_EyesOpen.csv'
               
FREQ_LOW = 10 # in Hz

FREQ_HIGH= 13 # in Hz

SELECTED_CHAN = 14 # EMG (BIP 1)= 32, C3 = 14, C4 = 16 (EEGO_CHANNR-1)

RECORDING_DURATION = 6 # overall recording duration

NUM_STIM_PULSES_PER_TRAIN = 10  # set to 10000 if you do not want to use trains

ITI = 0.5 # Inter-train-interval in seconds

PEAK_TROUGH_RISE_FALL = -1 # 2 to detect the rising slope,  -2 to detect the falling slope 

AMPLITUDE_THRESHOLD_PERCENTILE = 25  # stimulate only when the oscillation exceeeds a certain percentile of the amplitude in a preceding window

meanFreq = np.mean([FREQ_LOW, FREQ_HIGH])

# the time buffer at the end of the vector before you start looking for crossing points in seconds
FIXED_STIM_LAG = ((1000 / meanFreq) /2) / 1000 # in Seconds

# TIMEOUT between pulses 0.5, 0.2, 0.09 in seconds, say wait for 50% of the cycle duration to pass before looking again for another pulse
MIN_TIME_DIFF_PULSES =  ((1000 / meanFreq) * 0.5) / 1000 # in Seconds  

AUDIO_FILE_PATH = './main_code/Pulse_100Hz_40ms.wav'
#AUDIO_FILE_PATH = 'Pulse_100Hz_40ms_Ampl=3.wav'

# sampling rate of the amplifier, changed this to 1000 on the 8th Nov 2022
AMP_SR = 1000   # Hz
DISPLAY_WIN = 5 # seconds

SUB_WIN_WIDTH_DETECT_CROSSING = 0.02 * AMP_SR  # in samples

# ==============================================================================
# the interval between pulling each chunk of data, i.e. sampling rate of phase detection
PULL_DATA_INTERVAL = 0.001 # in seconds, FORMERLY 0.01, 0.001 did not speed up the process

# length of the time window to run the filter on (in seconds)
FILTERING_WIN_SEC = 1

# order of butterworth filter
BUTTERWORTH_FLTER_ORDER = 2

# max length of filter_sample list
FILTER_SAMPLE_LENGTH = int(FILTERING_WIN_SEC*AMP_SR)

# SR for the vibration pulse, does not need to be that high
AUDIO_SR = 44100  

# the interval between each real-time plot (in seconds)
PLOTTING_INTERVAL = 0.5

# Pick a channel, which does not contain any data to store our time stamp data, we only have
# 32 EEG + 2 EMG + 4 AUX channels (=38 channels)
STORE_TIMESTAMP_CHANNEL = 40 

# the array that contains all of information from one sensor
unfiltered_sample_uncut = np.array([])

# the array that contains one second of information for one sensor
unfiltered_sample_cut = np.array([])

# the array that contains one second of filtered information for one sensor
filtered_sample = np.array([])

# array that keeps track of the time stamps of the zero points
trig_point_xarray = np.array([]) 

trig_point_yarray = np.array([])

conc_array = np.array([])

replay_txt = ''
if REPLAY_ON:
    replay_txt = '_REPLAY'

csv_file = str(datetime.now().strftime('%Y_%m_%d_%H_%M_%S')) + \
    '_CHAN_' + str(SELECTED_CHAN) + '_TIMEOUT_' + str(round(MIN_TIME_DIFF_PULSES,3)) + \
        '_TRAIN_NR_PULS=' + str(NUM_STIM_PULSES_PER_TRAIN) + '_ITI=' + str(ITI) + \
        '_FRQ_' + str(FREQ_LOW) + '-' + str(FREQ_HIGH) + 'Hz_DET=' + str(PEAK_TROUGH_RISE_FALL) + '_SR=' + str(AMP_SR) + '_' + STIM_INFO + replay_txt + '.csv'


# ================================================================================
# FUNCTIONS 
    
def save_impedance(amplifier, time_of_reading):
    '''
    Function provided by the EEG supplier - 
    stores EEG impedances at the beginning and at the end of each recording
    '''
    stream = amplifier.OpenImpedanceStream()
    imp_csv_file = './main_code/data/imped_' + time_of_reading + '_' + csv_file

    with open(imp_csv_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(stream.getChannelList())
        writer.writerow(list(stream.getData()))

    print('\n\nStoring impedances')
    #print('  channels.... {}'.format(stream.getChannelList()))
    #print('  impedances.. {}'.format(list(stream.getData())))


def detect_crossing_point(array, stim_player, cnt, time_elapsed, time_lastStim, time_stamp, fixed_lag_samples):
    '''
    KEY function which runs the phase-detection algorithm
    '''
    global p, AMPLITUDE_THRESHOLD_PERCENTILE, MIN_TIME_DIFF_PULSES, PEAK_TROUGH_RISE_FALL, SUB_WIN_WIDTH_DETECT_CROSSING, trig_point_xarray, trig_point_yarray
 
    index = len(array) - fixed_lag_samples # we focus on the point located half a cycle before the end of the streamed data, as our filter might give distorted results for later points

    # ==============================================
    # Option 1) Based on the phase
    #phase_signal = np.angle(hilbert(array))
    #signData     = np.sign(phase_signal[int(index- SUB_WIN_WIDTH_DETECT_CROSSING/2): int(index + SUB_WIN_WIDTH_DETECT_CROSSING/2)])
    
    # ==============================================
    # Option 2) Maybe faster, but more spurious detection, based on the filtered data but without extracting phase

    fullWin_amplitude = np.abs(hilbert(array))  
    fullWin_ampl_thresh = np.percentile(fullWin_amplitude, AMPLITUDE_THRESHOLD_PERCENTILE)   # 

    analysis_win = array[int(index- SUB_WIN_WIDTH_DETECT_CROSSING/2): int(index + SUB_WIN_WIDTH_DETECT_CROSSING/2)]
    amp_analysis_win = fullWin_amplitude[int(index- SUB_WIN_WIDTH_DETECT_CROSSING/2): int(index + SUB_WIN_WIDTH_DETECT_CROSSING/2)]


    DO_STIM = False   # SET AN AMPLITUDE THRESHOLD, STIM ONLY IF AMPLITUDE EXCEEDS THE SET THRESHOLD
    if np.median(amp_analysis_win) > fullWin_ampl_thresh:
        DO_STIM = True

    stimEvent = [0]
    if DO_STIM:
        if (abs(PEAK_TROUGH_RISE_FALL) == 2):  # look for rising or descending phase
            signData     = np.sign(analysis_win)  
            zeroCrossing = np.diff(signData, 1) == PEAK_TROUGH_RISE_FALL  # 2 when detecting the zero-crossing for the rising slope, -2 for the descending slope     
            stimEvent = zeroCrossing    
        else:
            sign_diff_data = np.sign(np.diff(analysis_win, 1))
            if PEAK_TROUGH_RISE_FALL == 1:         
                peakDetect = np.diff(sign_diff_data, 1) == -2
                stimEvent = peakDetect             
            if PEAK_TROUGH_RISE_FALL == -1:        
                troughDetect = np.diff(sign_diff_data, 1) == 2
                stimEvent = troughDetect
                             
    
    idxOf_stimEvt = np.where(stimEvent)[0]
    if idxOf_stimEvt.size > 0: # if multiple stim events detected, choose the first one
        idxOf_stimEvt = idxOf_stimEvt[0]
    else:
        idxOf_stimEvt = 0


    if True in stimEvent: 
        if time_elapsed > MIN_TIME_DIFF_PULSES:  
            #time_elapsed_str = "{:.2f}".format(time_elapsed)
            #print(time_elapsed_str)
            if time_elapsed >= ITI:
                cnt = 1
            if cnt <= NUM_STIM_PULSES_PER_TRAIN:                    
                delay = idxOf_stimEvt/AMP_SR
                time_stamp += delay
                trig_point_xarray = np.hstack((trig_point_xarray, [time_stamp]))
                trig_point_yarray = np.hstack((trig_point_yarray, [array[index+idxOf_stimEvt]]))
                #print(f'{time_stamp:04.4f} 0 point')
                #time.sleep(delay)

                # # 1) Option: Try to reduce jitter (but at the cost of increased delay):
                # # only works with am.BackEnd.Load('PsychToolboxInterface'), which initially does not provide the correct output on the Lab PC
                # #  see also  https://audiomath.readthedocs.io/en/release/auto/Examples.html
                # offsetSeconds = 0.008  # this param, depends on your hardware and can be 5ms for Mac, often 25ms for Win
                # t0 = am.Seconds() # should be replaced with am.Seconds()
                #p.Play(when=t0 + delay + offsetSeconds) 

                # 2) Option: Do not control for jitter:
                # works with am.BackEnd.Load('PortAudioInterface'), and delivers correct output on PC
                stim_player.Play(wait = False)  # this
                #time_elapsed_str = "{:.2f}".format(time_elapsed)
                time_lastStim = am.Seconds()
                cnt = cnt + 1          
                
        
    return time_lastStim, cnt


# ================================================================================
# PULL DATA AND ANALYZE IT
def process_data(amplifier, stim_player, csv_file, q, print_delay=0, rec_duration=10, PULL_DATA_INTERVAL=0.001):
    '''
    Takes data samples from the amplifer at a fixed rate and saves it in a csv file

    Args:
        amplifier::eemagine::sdk::amplifier object
            The amplifier that you want to test
        print_delay::float
            The delay between printing messages in seconds
        rec_duration::int
            The period of time that the program streams data from the amplifier, default =10
        PULL_DATA_INTERVAL::float
            The delay between each sample taken from the amplifier

    Returns:
        None
    '''
    global TEST_MODE, test_file_path, AMP_SR, REPLAY_ON, REPLAY_STIM_PTS_FILE, FILTER_SAMPLE_LENGTH, PLOTTING_INTERVAL, FIXED_STIM_LAG, unfiltered_sample_uncut, unfiltered_sample_cut, filtered_sample, p, trig_point_xarray
    
    file_data = pd.read_csv(test_file_path)
    channel_list = pd.read_csv(test_file_path, nrows=0)
    #channel_list = ['FP1', 'FPz', 'FP2', 'F7', 'F4', 'Fz', 'F4', 'F8', 'FC5', 'FC1', 'FC2', 'FC6', ,'M1', 'T7', 'C3', 'Cz', 'C4', 'T8', 'M2', 'CP5', 'CP1', 'CP2', 'CP6', 'P7', 'P3', 'Pz', 'P4', 'P8', 'POz', 'O1', 'Oz', 'O2', 'EMG1', 'EMG2', 'AUX1', 'AUX2', 'AUX3', 'AUX4']

    #print('\n\nStreaming data:')
    #print(f'  channels:   {channel_list}')
    #time.sleep(print_delay)
    if REPLAY_ON:
        print(f'\nREPLAY ON!!!!!!!!')
    else:
        print(f'\nreplay off')

    print(f'\nRecording duration: {rec_duration}s')
    time.sleep(print_delay)
    print('\nSTREAMING IN')
    time.sleep(print_delay)
    
    if REPLAY_ON:
        #stim_pts_fname = 'data/' + REPLAY_STIM_PTS_FILE + '.csv'
        stim_points = pd.read_csv(REPLAY_STIM_PTS_FILE, header=None)
        stim_points = np.squeeze(stim_points.to_numpy())                           
        stim_points = stim_points - stim_points[0] # start at 0
        iterator = 0

    eeg_csv_file = './main_code/data/eeg_' + csv_file
    with open(eeg_csv_file, 'w+', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(channel_list)

        # ignore the samples at the very end, which can't be filtered
        fixed_lag_samples = int(FIXED_STIM_LAG * AMP_SR)

        t0 = am.Seconds()
        tend = t0 + rec_duration
        tnext = t0

        time_lastStim = 0 # in seconds
        time_elapsed = 1 # in seconds
        cnt = 1 # counter to count the nr of pulses in each stimulation train
        cnt_testData = 0
        samples_testData = 8
            
        while am.Seconds() < tend:
            time_stamp = am.Seconds() - t0
                
            # =======================================================
            # REPLAY MODE (if activated)
            if REPLAY_ON:
                if len(stim_points) == 0:
                    print("WARNING: NO STIM POINTS TO REPLAY")
        
                if iterator < (len(stim_points)-1): 
                    if time_stamp > stim_points[iterator]:                                                         
                        trig_point_xarray = np.hstack((trig_point_xarray, [time_stamp]))
                        stim_player.Play(wait = False)
                        iterator += 1
            
            # =======================================================
            # STREAM AND WRITE EEG DATA TO CSV
            tnext += PULL_DATA_INTERVAL
            delay = tnext - am.Seconds()
            if delay > 0: # first, wait for a fixed time with the streaming
                time.sleep(delay)      
              
            preTime = am.Seconds()           
            
            idx_start = cnt_testData + (samples_testData*cnt_testData)
            data = np.array(file_data[idx_start:(idx_start+samples_testData+1)])
            cnt_testData += 1
            time.sleep(samples_testData/AMP_SR)      
                
            durationStream = am.Seconds() - preTime    
            
            data_len = len(data[:,0])
            timeStamp_Vect = np.zeros(data_len)  # use the first column for timestamps
            timeStamp_Vect[data_len-1] = am.Seconds()
            timeStamp_Vect[data_len-2] = durationStream
            data[:,STORE_TIMESTAMP_CHANNEL] = timeStamp_Vect
            writer.writerows(data)
        

            # =======================================================
            # PROCESS SINGLE CHANNEL DATA
            if time_lastStim != 0: # time_lastStim will always be 0
                time_elapsed = am.Seconds() - time_lastStim

            # get a single column which is the data for one sensor
            new_data_chunk = np.array(data[:,SELECTED_CHAN].copy())

            # stick data into list
            unfiltered_sample_uncut = np.hstack((unfiltered_sample_uncut, new_data_chunk))
            
            # get only 1s worth of data and save in unfiltered_sample_cut if unfiltered_sample_uncut is bigger than FILTER_SAMPLE_LENGTH
            if len(unfiltered_sample_uncut) >= FILTER_SAMPLE_LENGTH:
                unfiltered_sample_cut = unfiltered_sample_uncut[-FILTER_SAMPLE_LENGTH:].copy()
                unfiltered_sample_cut = mean_subtract(unfiltered_sample_cut)
                
                t = list(range(1, len(unfiltered_sample_cut)+1))
                #print(len([t, unfiltered_sample_cut]))
                q.put([t, unfiltered_sample_cut])
                                    
                # =======================================================
                # CLOSED-LOOP STIM MODE
                if not REPLAY_ON:                      
                    filtered_sample = butterworth_filter(unfiltered_sample_cut)      
                    [time_lastStim, cnt] = detect_crossing_point(filtered_sample, stim_player, cnt, time_elapsed, time_lastStim, time_stamp, fixed_lag_samples)
                                            

# ================================================================================
# RUN EXPERIMENT
def run_exp(amplifier, stim_player, q, print_delay=0):
    '''
    Args:
        amplifier::eemagine::sdk::amplifier object
            The amplifier that you want to test
        print_delay::float
            The delay between printing messages in seconds

    Returns:
        None
    '''
    global TEST_MODE, RECORDING_DURATION, PULL_DATA_INTERVAL, SELECTED_CHAN, csv_file

    process_data(amplifier, stim_player, csv_file, q, print_delay=0.2, rec_duration=RECORDING_DURATION, PULL_DATA_INTERVAL=PULL_DATA_INTERVAL)


def save_trig_points(trig_points, csv_file):
    '''
    Save the timing of the stimulation points. 
    Returns:
        None
    '''
    csv_file_path = './main_code/data/stim_points_' + csv_file
    with open(csv_file_path, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(trig_points)


def mean_subtract(array):
    mean = np.mean(array)
    array -= mean
    return array


def butterworth_filter(array):
    '''
    Subtract the mean from array, flips array and runs butterworth filter.

    Args:
        array: np array
            the array that you want to filter
    
    Returns:
        a filtered array
    '''
    global FREQ_LOW, FREQ_HIGH, AMP_SR, BUTTERWORTH_FLTER_ORDER
    array = mean_subtract(array)
    length = len(array)
    new_array = np.hstack((np.flip(array), array, np.flip(array)))
    filtered_array = butter_bandpass_filter(new_array, FREQ_LOW, FREQ_HIGH, AMP_SR, BUTTERWORTH_FLTER_ORDER)
    return filtered_array[length:2*length]


def amplifier_to_id(amplifier):
  return '{}-{:06d}-{}'.format(amplifier.getType(), amplifier.getFirmwareVersion(), amplifier.getSerialNumber())


def live_stream(running, q):
    '''
    handles streaming data from amplifier
    '''
    global TEST_MODE, FIXED_STIM_LAG, AUDIO_FILE_PATH, AUDIO_SR
    
    #am.BackEnd.Load('PsychToolboxInterface') # for better precision, see https://audiomath.readthedocs.io/en/release/auto/Examples.html
    am.BackEnd.Load('PortAudioInterface') # the default back end
    stimPulse = am.Sound(AUDIO_FILE_PATH, fs = AUDIO_SR)

    deviceInfo = am.PortAudioInterface.GetDeviceInfo() # https://audiomath.readthedocs.io/en/release/source/audiomath.PortAudioInterface.html
    print(str(deviceInfo))
    #am.PortAudioInterface.LowLatencyMode(True, preferASIO=False)
    stim_player = am.Player(stimPulse, fs = AUDIO_SR,  loop = False, playing=False)

    print('delaying to allow slow devices to attach...')
    time.sleep(1)

    amplifier = 'test'
    run_exp(amplifier, stim_player, q, 1)
    
    save_trig_points()
    print("Saved trigger points")

def updateInProc(curve1,curve2,q,y_np):
        item = q.get()
            
        global conc_array   
        # Plot more recent data
        newData = np.squeeze(np.transpose(np.asarray(item)))
        newData = newData[:,1]
        newData = newData - np.mean(newData)

        conc_array = np.append(conc_array, newData)

        if len(conc_array) > (AMP_SR * DISPLAY_WIN):
            diplay_len = AMP_SR * DISPLAY_WIN
            conc_array = conc_array[-diplay_len:]

        filtered_data = butter_bandpass_filter(conc_array, FREQ_LOW, FREQ_HIGH, AMP_SR, BUTTERWORTH_FLTER_ORDER)

        t = list(range(1, len(conc_array)+1))
        curve1.setData(conc_array)
        curve2.setData(filtered_data+1)
    
def display(name,q):
    # Nicer visualization: https://towardsdatascience.com/dynamic-replay-of-time-series-data-819e27212b4b
    app = QtWidgets.QApplication([])

    win = pg.GraphicsLayoutWidget(title="Basic plotting examples")
    win.resize(1000,600)
    win.setWindowTitle(name)
    p2 = win.addPlot(title="Updating plot")
    curve1 = p2.plot(pen='y')
    curve2 = p2.plot(pen='y')

    y_np = []      

    timer = QtCore.QTimer()
    timer.timeout.connect(lambda: updateInProc(curve1,curve2,q,y_np))
    timer.start(50)  # update every 50 milliseconds

    win.show()
    app.exec_()

if __name__ == '__main__':   
                          
    q = Queue()
    # Event for stopping the IO thread
    #run = threading.Event()
    #run.set()

    running = True # not currently in use
    # Run io function in a thread
    t = threading.Thread(target=live_stream, args=(running, q))
    t.start()

    # Start display process
    p = Process(target=display, args=('RealtimeDisplay', q))
    p.start()
    
    # #if REPLAY_ON: # this did not work
    # # start_time = am.Seconds()
    # #rp = Process(target=replay_stim, args=(start_time, q))
    # #rp.start()

    t.join()
    p.terminate()
    # #rp.terminate()
