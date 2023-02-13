import eego_sdk
import numpy as np

def stream_data():
    factory = eego_sdk.factory()
    amplifiers = factory.getAmplifiers()
    amplifier = amplifiers[0]
    
    rates = amplifier.getSamplingRatesAvailable()
    ref_ranges = amplifier.getReferenceRangesAvailable()
    bip_ranges = amplifier.getBipolarRangesAvailable()
    stream = amplifier.OpenEegStream(rates[0], ref_ranges[0], bip_ranges[0])
    
    for _ in range(0, 50):
        d = np.array(stream.getData())
        print(d)
        print(d.shape)
    

stream_data()

