from .streaming_measurement import StreamingTempMeasurement
from .regulation_controller import PIController 

class PartThreeTestMeasurement(StreamingTempMeasurement):
    DISPLAY_NAME = "Měření překmitu"
    DURATION_S = 3600.0
    SAMPLE_RATE_HZ = 1.0
    SHOW_REFERENCE_CURVE = True

    def __init__(self, serial_mgr, target_temp=25.0):
        super().__init__(serial_mgr)
        
        # Tady je tvůj kompletní regulátor s rozděleným k_heat a k_cool
        self.controller = PIController(
            kp_heat=19.27,
            ki_heat=0.075,
            kd_heat=500.0,

            kp_cool=260,
            ki_cool=4.5,
            kd_cool=450.0,

            out_min=-100, 
            out_max=100,
            int_active_threshold=3.75,
            deadband=0.0
        )
        self.target_temp = float(target_temp)
        self.last_pwm_heat = 0
        self.last_pwm_cool = 0

    def set_target_temperature(self, temp: float):
        self.target_temp = max(18.0, min(40.0, temp))

    def on_start(self):
        self.controller.reset()
        super().on_start()

    def on_stop(self):
        super().on_stop()
        if self.serial.is_open():
            self.serial.write_line("SET PWM 0 0") 
            self.serial.write_line("SET PWM 1 0") 

    def perform_regulation_logic(self, values: dict) -> dict:
        current_temp = values.get("T_TMP")
        if current_temp is None and "T_BME" in values:
             current_temp = values["T_BME"]

        if current_temp is not None:
            action = self.controller.update(self.target_temp, current_temp)
            
            pwm_heat = round(action, 1) if action > 0 else 0
            pwm_cool = round(abs(action), 1) if action <= 0 else 0

            if self.serial.is_open():
                if pwm_heat != self.last_pwm_heat:
                    self.serial.write_line(f"SET PWM 0 {pwm_heat}")
                    self.last_pwm_heat = pwm_heat
                if pwm_cool != self.last_pwm_cool:
                    self.serial.write_line(f"SET PWM 1 {pwm_cool}")
                    self.last_pwm_cool = pwm_cool
            
            values["PWM"] = int(action) 
            values["Target"] = self.target_temp

            # Zapíšeme PWM a Target do hlavního pole pro export, aby byly v CSV
            if self.recorded_data:
                self.recorded_data[-1]["PWM"] = values["PWM"]
                self.recorded_data[-1]["Target"] = values["Target"]

        return values