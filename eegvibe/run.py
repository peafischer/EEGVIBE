from multiprocessing import Process
import threading
from time import sleep
from pathlib import Path

from .read import read_from_file, read_from_stream, get_freq_sample, get_impedance, get_channel_names
from .analysis import tracking, replay
from .filter import HighPassFilter
from .oscilltrack import Oscilltrack
from .stimulate import CLStimulator, SemiCLStimulator, init_CLStimulator, init_SemiCLStimulator
from .write import write_stream, find_filename, is_CL_stim, add_metadata
from .plot import plot_stream
from pathlib import Path

def run_tracking(freq_sample, freq_target, phase_target, freq_high_pass, 
        oscilltrack_suppresion, oscilltrack_gamma,
        is_CL_stim, N_pulses, pulse_duration, ITI, IPI, stim_device_ID,
        channel_track, channels_ref, participant_ID, channels_EMG = [],
        N_plot_samples = 1000, plot_labels = ["Tracked channel"], plot_signal_range = (-0.0002, 0.0002), 
        plot_EEG_scale_factor = 1.0, plot_autoscale = False, 
        recording_duration = 10, out_path = './out_data/', condition_label = '', filename_data = None,
        amplifier_ID = 0):
    """
    Run the typical pipeline of a tracking experiment : [read -> write] concurrent with [read -> track -> plot]

    The track part of the pipeline uses the Oscilltrack algorithm to track a signal of a particular frequency 
    and output stimulations on a particular phase of this signal.

    Arguments :
        freq_sample : number
            The sampling frequency at which data is read (either from an EEG amplifier or from a file).
        freq_target : number
            The target frequency that the Oscilltrack algorithm tracks.
        phase_target : number
            The target phase of freq_target when stimulations are triggered.
        freq_high_pass : number 
            The corner frequency of a high-pass filter. The high-pass filter is applied on the track step before Oscilltrack tracking.
        oscilltrack_suppresion : number 
            This is a number in range [0,1].
            It determines the proportion of a cycle of freq_target that no stimulation is allowed to happen after a successful stimulation.
            It is added to counteract erronous detections of phase_target in noisy data.
        oscilltrack_gamma : number
            The time window in the past that Oscilltrack considers when adapting its estimate for the current value of the freq_target signal.
            Its inverse (1 / oscilltrack_gamma) is equivalent to the number of past samples that Oscilltrack considers for its adaptation.
            Thus oscilltrack_gamma should match a time window that contains some cycles of freq_target, 
            but its not too large or too small so that much slower or much faster frequencies (respectively) are not considered.
        is_CL_stim : bool
            A flag that determines whether the stimulation mode is closed-loop (if True) or semi-closed-loop (if False).
        N_pulses : integer
            The number of stimulation pulses that are delivered in a stimulation train, before an ITI is triggered.
        pulse_duration : number
            The duration of each stimulation pulse.
        ITI : number 
            Inter-train-interval. An interval where there no stimulations can be triggered between two stimulation trains.
            This is triggered after N_pulses have been triggered.
        IPI : number
            Inter-pulse-interval.
            If the stimulation mode is closed-loop (is_CL_stim = True), this argument is ignored, as each pulse is triggered whenever phase_target is detected.
            If the stimulation mode is semi-closed-loop (is_CL_stim = False), this argument represents the interval between two consecutive pulses of a single stimulation train. 
        stim_device_ID : integer
            The ID of the device that is used to trigger stimulation pulses. 
            To print a list of available stimulation devices and their corresponding ID, one could run :
                import audiomath
                audiomath.FindDevices()
        channel_track : integer
            The index of the data channel that Oscilltrack uses to track freq_target. 
            This corresponds to the column index of each data sample that contains the channel of interest.
        channels_ref : list or numpy.array of integers
            Collection containing the indices of all channels that are used for referencing.
            Referencing is applied as subtraction of the mean value over all channels in channels_ref from the tracked channel in channel_track.
            This operation is performed before high-pass filtering and tracking with Oscilltrack.
        channels_EMG : list or numpy.array of integers, optional
            Defaults to empty list. Collection containing the indices of any additional channels that are included in the plot, along with channel_track.
            If this collection is empty, no such channels will be plotted. 
            If it is not empty, the channels will be high-pass filtered using freq_high_pass before plotting.
        participant_ID : integer, optional
            The ID of the participant of the current experiment. This value is included in the output data filename as _P{participant_ID}_ .
        N_plot_samples : integer, optional, optional
            Defaults to 1000. The number of most recent samples to be included in the plot.
        plot_labels : list of strings, optional
            Defaults to ["Tracked channel"]. A list of the labels for each channel that is plotted.
            The first element is the label of the channel in channel_track and every next label corresponds to the channels in channels_EMG.
            The default value matches the default of channels_EMG=[], where only channel_track is plotted.
        plot_signal_range : tuple of numbers, optional
            Defaults to (-0.0002, 0.0002). The suggested range of a single signal in the form of a tuple of (lower_bound, upper_bound).
            During plotting this range will be multiplied by the number of channels to be plotted (channel_track and channels_EMG)
            to calculate the final y-axis range. Each plotted signal is offsetted along the y-axis to distinguish between them.
            The offset values cover the range of the two middle quarters of the final y-axis range. 
            So this argument determines how much room should be left for each signal, so that after the y-axis offsets, signals will not overlap.
        plot_EEG_scale_factor : number, optional
            Defaults to 1 . The scaling factor that is multiplied to the EEG signal that is tracked (channel_track) before plotting it.
            This can be used to magnify the signal so it is more visible in the final plot.
        plot_autoscale : bool, optional
            Defaults to False . Determined whether the y-axis is autoscaled during plotting. 
            WARNING : Switching autoscaling on (plot_autoscale = True) will slow down the plotting function considerably!
        recording_duration : number, optional
            Defaults to 10 seconds. The number of seconds that the current single experiment recording runs for.
        out_path : string, optional
            Defaults to './out_data/'. Path to the folder where output data and pkl files (stimulation parameters) are saved.
            WARNING: Path to folder must already exist in order for this to work.
        condition_label : string, optional
            Defaults to empty string (''). A label containing any additional information that should be included in the filename
            of output data and pkl files (stimulation parameters).
        filename_data : string, optional
            Defaults to None. Path to a hdf5 or csv file containing data. If a path is given, then data is read from the given file to emulate an experimental recording.
            If the default value is used, then data is read from an EEG amplifier.
        amplifier_ID : integer, optional
            Defaults to 0 . The ID of the EEG amplifier to be used when filename_data is None. 
            Typically the default value should be accurate, unless more amplifier-like devices are plugged in the computer.

    Returns :
        None. The pipeline is run and two files are saved as a result: 
        a hdf5 file containing the raw data (without filtering or referencing) 
        and a pkl file containing all parameters of a Stimulator object, to be used during replay.
    """

    port = 5555
    topic = 'sample'
    plot_port = 5556
    plot_topic = 'plot'

    stop_stream_event = threading.Event()
    if filename_data is None:
        final_freq_sample = get_freq_sample(freq_sample, amplifier_ID)
        impedance_init = get_impedance(amplifier_ID)
        channel_names = get_channel_names(amplifier_ID)

        read_thread = threading.Thread(
            target=read_from_stream, 
            args=(final_freq_sample, stop_stream_event, port, topic)
        )
    else:
        final_freq_sample = freq_sample
        impedance_init = [0.0 for _ in range(0,32)]
        channel_names = ['' for _ in range(0,32)]

        read_thread = threading.Thread(
            target = read_from_file,
            args = (filename_data, 8, freq_sample, stop_stream_event, port, topic)
        )
    
    tracker = Oscilltrack(
        freq_target = freq_target, 
        phase_target = phase_target, 
        freq_sample = final_freq_sample, 
        suppression_cycle = oscilltrack_suppresion,
        gamma = oscilltrack_gamma
    )

    if is_CL_stim: 
        sm = 'FULL_CL'
        stim = CLStimulator(
            N_pulses_stim = 1, 
            N_stim_train = N_pulses, 
            ITI = ITI, 
            pulse_duration = pulse_duration, 
            IPI = IPI, 
            device_ID = stim_device_ID
        )
    else:
        sm = 'SEMI_CL'
        stim = SemiCLStimulator(
            N_pulses = N_pulses, 
            ITI = ITI, 
            pulse_duration = pulse_duration, 
            IPI = IPI, 
            device_ID = stim_device_ID
        )

    filter_track = HighPassFilter(
        freq_corner = freq_high_pass, 
        freq_sample = final_freq_sample
    )
    filters_EMG = [
        HighPassFilter(freq_corner = freq_high_pass, freq_sample = final_freq_sample) 
        for _ in range(len(channels_EMG))
    ]

    filename_out_data = find_filename(
        participant_ID = participant_ID, 
        channel_track = channel_track,
        freq_target = freq_target,
        stim_mode = sm,
        phase_target = phase_target,
        label = condition_label,
        path = out_path,
        format = 'hdf5'
        )    
    
    fs = filename_out_data.split('.')
    filename_stim = '.'.join(fs[:-1]) + '.pkl'

    analysis_process = Process(
        target=tracking, 
        args=(port, topic, plot_port, plot_topic, tracker, stim, filter_track, filters_EMG), 
        kwargs={
            'filename_stim' : filename_stim, 
            'channel_track' : channel_track, 
            'channels_ref' : channels_ref, 
            'channels_EMG' : channels_EMG
        }
    )

    saver_process = threading.Thread(
        target = write_stream, 
        args = (port, topic, filename_out_data)
    )

    plot_process = Process(
        target = plot_stream, 
        args = (plot_port, plot_topic),
        kwargs = {
            'n_samples' : N_plot_samples, 
            'labels' : plot_labels, 
            'autoscale' : plot_autoscale, 
            'signal_range' : plot_signal_range,
            'EEG_scale_factor' : plot_EEG_scale_factor
            }
    )

    analysis_process.start()
    saver_process.start()
    plot_process.start()
    read_thread.start()

    sleep(recording_duration) 
    
    stop_stream_event.set()
    read_thread.join()
    saver_process.join()
    analysis_process.join()
    plot_process.join()
    
    if filename_data is None:
        impedance_final = get_impedance(amplifier_ID)
    else:
        impedance_final = [1.0 for _ in range(0,32)]

    metadata_dict = {
        'impedance_init' : impedance_init,
        'impedance_final' : impedance_final,
        'channel_names' : channel_names,
        'channels_ref' : channels_ref,
        'freq_sample' : final_freq_sample,
        'recording_duration' : recording_duration,
        'oscilltrack_suppresion' : oscilltrack_suppresion,
        'replay_file' : '',
        'participant_ID' : participant_ID,
        'stim_mode' : sm,
        'N_pulses_per_train' : N_pulses,
        'pulse_duration' : pulse_duration,
        'IPI' : 0.0 if is_CL_stim else IPI,
        'ITI' : ITI,
        'phase_target' : phase_target,
        'freq_target' : freq_target,
        'condition_label' : condition_label
    }
    add_metadata(metadata =  metadata_dict, filename = filename_out_data)

def run_replay(freq_sample, freq_high_pass, filename_stim,
        channel_track, channels_ref, participant_ID, channels_EMG = [],
        N_plot_samples = 1000, plot_labels = ["Tracked channel"], plot_signal_range = (-0.0002, 0.0002), 
        plot_EEG_scale_factor = 1.0, plot_autoscale = False, 
        recording_duration = 10, condition_label = '', filename_data = None, amplifier_ID = 0):
    """
    Run the typical pipeline of a replay experiment : [read -> write] concurrent with [read -> replay -> plot]

    The [replay] part of the pipeline triggers stimulations at the stimulation times,
    as they are read from a pkl file containing all stimulation parameters. 
    Replay performs every step of track (see run_track above) except for the actual tracking with Oscilltrack.
    That is, data is acquired from the [read] part, referenced with mean-subtraction and high-pass filtered, 
    before sent to be plotted in the [plot] part.

    Arguments :
        freq_sample : number
            The sampling frequency at which data is read (either from an EEG amplifier or from a file).
        freq_target : number
            The target frequency that the Oscilltrack algorithm tracks.
        filename_stim : string
            Path to pkl file containing all stimulation parameters, including stimulation times that were triggered during the tracking experiment (see run_track above). 
            This file is used to initialise a Stimulator object, either closed-loop or semi-closed-loop, using the stored parameters. 
            See the definition of CLStimulator and SemiCLStimulator in stimulate.py for a list of parameters.
        channel_track : integer
            The index of the data channel that Oscilltrack uses to track freq_target. 
            This corresponds to the column index of each data sample that contains the channel of interest.
        channels_ref : list or numpy.array of integers
            Collection containing the indices of all channels that are used for referencing.
            Referencing is applied as subtraction of the mean value over all channels in channels_ref from the tracked channel in channel_track.
            This operation is performed before high-pass filtering and tracking with Oscilltrack.
        channels_EMG : list or numpy.array of integers, optional
            Defaults to empty list. Collection containing the indices of any additional channels that are included in the plot, along with channel_track.
            If this collection is empty, no such channels will be plotted. 
            If it is not empty, the channels will be high-pass filtered using freq_high_pass before plotting.
        participant_ID : integer, optional
            The ID of the participant of the current experiment. This value is included in the output data filename as _P{participant_ID}_ .
        N_plot_samples : integer, optional, optional
            Defaults to 1000. The number of most recent samples to be included in the plot.
        plot_labels : list of strings, optional
            Defaults to ["Tracked channel"]. A list of the labels for each channel that is plotted.
            The first element is the label of the channel in channel_track and every next label corresponds to the channels in channels_EMG.
            The default value matches the default of channels_EMG=[], where only channel_track is plotted.
        plot_signal_range : tuple of numbers, optional
            Defaults to (-0.0002, 0.0002). The suggested range of a single signal in the form of a tuple of (lower_bound, upper_bound).
            During plotting this range will be multiplied by the number of channels to be plotted (channel_track and channels_EMG)
            to calculate the final y-axis range. Each plotted signal is offsetted along the y-axis to distinguish between them.
            The offset values cover the range of the two middle quarters of the final y-axis range. 
            So this argument determines how much room should be left for each signal, so that after the y-axis offsets, signals will not overlap.
        plot_EEG_scale_factor : number, optional
            Defaults to 1 . The scaling factor that is multiplied to the EEG signal that is tracked (channel_track) before plotting it.
            This can be used to magnify the signal so it is more visible in the final plot.
        plot_autoscale : bool, optional
            Defaults to False . Determined whether the y-axis is autoscaled during plotting. 
            WARNING : Switching autoscaling on (plot_autoscale = True) will slow down the plotting function considerably!
        recording_duration : number, optional
            Defaults to 10 seconds. The number of seconds that the current single experiment recording runs for.
        out_path : string, optional
            Defaults to './out_data/'. Path to the folder where output data and pkl files (stimulation parameters) are saved.
            WARNING: Path to folder must already exist in order for this to work.
        condition_label : string, optional
            Defaults to empty string (''). A label containing any additional information that should be included in the filename
            of output data and pkl files (stimulation parameters).
        filename_data : string, optional
            Defaults to None. Path to a hdf5 or csv file containing data. If a path is given, then data is read from the given file to emulate an experimental recording.
            If the default value is used, then data is read from an EEG amplifier.
        amplifier_ID : integer, optional
            Defaults to 0 . The ID of the EEG amplifier to be used when filename_data is None. 
            Typically the default value should be accurate, unless more amplifier-like devices are plugged in the computer.

    Returns :
        None. The replay pipeline is run and one hdf5 file is saved, containing the raw data (without filtering or referencing).
        The output filename of a replay experiment contains a "_REPLAY_" string before the final version indicator.
    """

    port = 5555
    topic = 'sample'
    plot_port = 5556
    plot_topic = 'plot'

    fs = filename_stim.split('.')
    fs_name = '.'.join(fs[:-1])
    fs_name_split = fs_name.split('_')
    filename_out_data = '_'.join(fs_name_split[:-1]) + '_REPLAY_' + fs_name_split[-1] + '.hdf5'

    if Path(filename_out_data).is_file():
        raise ValueError("File already exists! Change .pkl file")

    stop_stream_event = threading.Event()
    if filename_data is None:
        final_freq_sample = get_freq_sample(freq_sample, amplifier_ID)
        impedance_init = get_impedance(amplifier_ID)
        channel_names = get_channel_names(amplifier_ID)

        read_thread = threading.Thread(
            target=read_from_stream, 
            args=(final_freq_sample, stop_stream_event, port, topic)
        )
    else:
        final_freq_sample = freq_sample
        impedance_init = [0.0 for _ in range(0,32)]
        channel_names = ['' for _ in range(0,32)]

        read_thread = threading.Thread(
            target = read_from_file,
            args = (filename_data, 8, freq_sample, stop_stream_event, port, topic)
        )
        
    if is_CL_stim(filename_stim): 
        sm = 'FULL_CL'
        stim = init_CLStimulator(filename_stim)
        N_pulses = stim.N_stim_train
    else:
        sm = 'SEMI_CL'
        stim = init_SemiCLStimulator(filename_stim)
        N_pulses = stim.N_pulses

    filter_track = HighPassFilter(
        freq_corner = freq_high_pass, 
        freq_sample = final_freq_sample
    )
    filters_EMG = [
        HighPassFilter(freq_corner = freq_high_pass, freq_sample = final_freq_sample) 
        for _ in range(len(channels_EMG))
    ]

    analysis_process = Process(
        target=replay, 
        args=(port, topic, plot_port, plot_topic, stim, filter_track, filters_EMG), 
        kwargs={
            'channel_track' : channel_track, 
            'channels_ref' : channels_ref, 
            'channels_EMG' : channels_EMG
        }
    )

    saver_process = threading.Thread(
        target = write_stream, 
        args = (port, topic, filename_out_data)
    )
    
    plot_process = Process(
        target = plot_stream, 
        args = (plot_port, plot_topic),
        kwargs = {
            'n_samples' : N_plot_samples, 
            'labels' : plot_labels, 
            'autoscale' : plot_autoscale, 
            'signal_range' : plot_signal_range,
            'EEG_scale_factor' : plot_EEG_scale_factor
            }
    )

    read_thread.start()
    saver_process.start()
    analysis_process.start()
    plot_process.start()

    recording_duration = stim.stim_times[-1] - stim.stim_times[0] + 3
    sleep(recording_duration) 
    
    stop_stream_event.set()
    plot_process.join()
    saver_process.join()
    analysis_process.join()
    read_thread.join()

    if filename_data is None:
        impedance_final = get_impedance(amplifier_ID)
    else:
        impedance_final= [1.0 for _ in range(0,32)]

    metadata_dict = {
        'impedance_init' : impedance_init,
        'impedance_final' : impedance_final,
        'channel_names' : channel_names,
        'channels_ref' : channels_ref,
        'freq_sample' : final_freq_sample,
        'recording_duration' : recording_duration,
        'replay_file' : filename_stim,
        'participant_ID' : participant_ID,
        'stim_mode' : sm,
        'N_pulses_per_train' : N_pulses,
        'pulse_duration' : stim.pulse_duration,
        'IPI' : 0.0 if is_CL_stim else stim.IPI,
        'ITI' : stim.ITI,
        'condition_label' : condition_label
    }
    add_metadata(metadata =  metadata_dict, filename = filename_out_data)
