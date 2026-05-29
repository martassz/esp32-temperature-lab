import time
from measurements.streaming_measurement import StreamingTempMeasurement

class PartOneMeasurement(StreamingTempMeasurement):
    DISPLAY_NAME = "Část 1: Odporové snímače"
    DURATION_S = 3600.0 
    SAMPLE_RATE_HZ = 1.0
    SHOW_REFERENCE_CURVE = True

    def __init__(self, serial_mgr, pwm_channel=0, pwm_value=0, adc_filter=False):
        super().__init__(serial_mgr)
        
        self._pwm_channel = pwm_channel
        self._pwm_value = pwm_value
        self._adc_filter = adc_filter

    def on_start(self):
        """
        Pre-execution setup specific to Part 1:
        Configures hardware actuator limits and ADC filter state before
        invoking the primary telemetry stream.
        """
        if self.serial.is_open():
            # Configure active hardware actuator channel
            print(f"PartOne: Nastavuji PWM CH{self._pwm_channel} -> {self._pwm_value}%")
            self.serial.write_line(f"SET PWM {self._pwm_channel} {self._pwm_value}")
            time.sleep(0.1)
            
            # Dispatch signal processing configuration to the MCU
            filter_val = 1 if self._adc_filter else 0
            print(f"PartOne: Nastavuji Filter -> {filter_val}")
            self.serial.write_line(f"SET FILTER {filter_val}")
            time.sleep(0.1)
            
        super().on_start()