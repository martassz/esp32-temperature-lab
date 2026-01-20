import time
from measurements.streaming_measurement import StreamingTempMeasurement

class PartOneMeasurement(StreamingTempMeasurement):
    DISPLAY_NAME = "Část 1: Odporové snímače"
    DURATION_S = 3600.0 
    SAMPLE_RATE_HZ = 1.0
    SHOW_REFERENCE_CURVE = True

    # --- ZDE BYLA CHYBA: Musíš přidat 'adc_filter=False' do závorky ---
    def __init__(self, serial_mgr, pwm_channel=0, pwm_value=0, adc_filter=False):
        super().__init__(serial_mgr)
        
        self._pwm_channel = pwm_channel
        self._pwm_value = pwm_value
        self._adc_filter = adc_filter

    def on_start(self):
        """
        Specifická logika pro start Části 1:
        Nastavíme PWM, Filtr a pak pustíme standardní měření.
        """
        if self.serial.is_open():
            # 1. Nastavení PWM
            print(f"PartOne: Nastavuji PWM CH{self._pwm_channel} -> {self._pwm_value}%")
            self.serial.write_line(f"SET PWM {self._pwm_channel} {self._pwm_value}")
            time.sleep(0.1)
            
            # 2. Nastavení Filtru
            filter_val = 1 if self._adc_filter else 0
            print(f"PartOne: Nastavuji Filter -> {filter_val}")
            self.serial.write_line(f"SET FILTER {filter_val}")
            time.sleep(0.1)
            
        super().on_start()