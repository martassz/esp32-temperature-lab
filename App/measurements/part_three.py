from PySide6.QtCore import Signal
from .streaming_measurement import StreamingTempMeasurement
from .regulation_controller import PIController 

class PartThreeMeasurement(StreamingTempMeasurement):
    DISPLAY_NAME = "Část 3: Regulace teploty"
    DURATION_S = 3600.0
    SAMPLE_RATE_HZ = 1.0
    SHOW_REFERENCE_CURVE = True

    def __init__(self, serial_mgr, target_temp=25.0, on_steady_state=None):
        super().__init__(serial_mgr)
        self.on_steady_state = on_steady_state
        
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

        # --- NOVÉ PROMĚNNÉ PŘIDAT SEM ---
        self.on_steady_state = on_steady_state
        self.meas_state = "ČEKÁNÍ"
        self.settle_timer = 0
        self.steady_samples_count = 0
        self.steady_data = []  
        
        self.tolerance = 0.025
        self.settle_required_s = 10
        self.measure_required_count = 10

    def set_target_temperature(self, temp: float):
        self.target_temp = max(18.0, min(40.0, temp))

    def on_start(self):
        self.controller.reset()
        self.meas_state = "ČEKÁNÍ"
        self.settle_timer = 0
        self.steady_samples_count = 0
        self.steady_data = []
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

            # --- TUTO NOVOU ČÁST PŘIDEJ SEM ---
            # Propíšeme PWM a Target zpětně do hlavního záznamníku dat
            if self.recorded_data:
                self.recorded_data[-1]["PWM"] = values["PWM"]
                self.recorded_data[-1]["Target"] = values["Target"]

            if self.meas_state != "DOMĚŘENO":
                odchylka = abs(current_temp - self.target_temp)
                
                if self.meas_state == "ČEKÁNÍ":
                    if odchylka <= self.tolerance:
                        self.settle_timer += 1
                        if self.settle_timer >= self.settle_required_s:
                            print("Teplota stabilizována mimo překmit. Začínám odpočet měření.")
                            self.meas_state = "MĚŘENÍ"
                    else:
                        self.settle_timer = 0 
                
                elif self.meas_state == "MĚŘENÍ":
                    # Zkopírujeme si aktuální ustálený řádek k sobě
                    if self.recorded_data:
                        self.steady_data.append(self.recorded_data[-1].copy())

                    self.steady_samples_count += 1
                    if self.steady_samples_count >= self.measure_required_count:
                        self.meas_state = "DOMĚŘENO"
                        if self.on_steady_state:
                            self.on_steady_state()
            # --- KONEC NOVÉ ČÁSTI ---

        return values
    
    def export_to_csv(self, filename: str, allowed_sensors=None) -> bool:
        if allowed_sensors is not None:
            allowed_sensors = set(allowed_sensors)
            allowed_sensors.update(["H_BME"])
            
        original_data = self.recorded_data
        self.recorded_data = self.steady_data
        
        result = super().export_to_csv(filename, allowed_sensors)
        
        self.recorded_data = original_data
        return result