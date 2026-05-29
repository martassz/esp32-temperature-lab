from measurements.streaming_measurement import StreamingTempMeasurement


class BmeDallasSlowMeasurement(StreamingTempMeasurement):
    """
    Demonstrative measurement profile utilizing the JSON protocol.
    
    Architectural purpose:
      - Showcases custom configuration overrides for measurement duration
        and sampling frequency.
      - Acts as a scalable template for specialized long-duration logging.
    """

    DURATION_S = 600.0      
    SAMPLE_RATE_HZ = 0.5