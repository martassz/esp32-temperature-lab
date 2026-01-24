from .streaming_measurement import StreamingTempMeasurement
from .regulation_controller import PIController 

class PartThreeMeasurement(StreamingTempMeasurement):
    DISPLAY_NAME = "Část 3: Regulace teploty"
    DURATION_S = 3600.0
    SAMPLE_RATE_HZ = 1.0  # Důležité: Rodičovská třída toto použije pro SET RATE

    def __init__(self, serial_mgr, target_temp=25.0):
        # Předáme manager rodiči
        super().__init__(serial_mgr)
        
        # Inicializace regulátoru
        self.controller = PIController(
            kp_heat=30.0,    # Brždění
            ki_heat=2.0,   # Integrace pro přesné dotažení
            kd_heat=900.0,
            
            kp_cool=40.0,   # Chlazení může být agresivnější
            ki_cool=0.4,
            kd_cool=800.0,
            
            out_min=-100, 
            out_max=100,
            int_active_threshold=0.25, # Integrál se zapne až 0.25°C od cíle
            deadband=0.0              # Tolerance 0.0°C (neřešíme šum)
        )
        self.target_temp = float(target_temp)
        
        self.last_pwm_heat = 0
        self.last_pwm_cool = 0

    def set_target_temperature(self, temp: float):
        self.target_temp = max(18.0, min(40.0, temp))

    def on_start(self):
        # 1. Reset regulátoru
        self.controller.reset()
        
        # 2. Zavoláme rodiče -> ten pošle "SET RATE 1" a "START"
        super().on_start()

    def on_stop(self):
        # 1. Zavoláme rodiče -> ten pošle "STOP"
        super().on_stop()
        
        # 2. Bezpečnostní vypnutí akčních členů (pro jistotu)
        if self.serial.is_open():
            self.serial.write_line("SET PWM 0 0") 
            self.serial.write_line("SET PWM 1 0") 

    # Metodu handle_line() jsme smazali -> použije se ta z StreamingTempMeasurement,
    # která správně parsuje data z ESP32.

    def perform_regulation_logic(self, values: dict) -> dict:
        """
        Počítá akční zásah regulátoru. Volá se z UI (_on_measurement_data).
        """
        current_temp = values.get("T_TMP")
        
        # Fallback na Dallas
        if current_temp is None and "T_BME" in values:
             current_temp = values["T_BME"]

        if current_temp is not None:
            # Výpočet PI
            action = self.controller.update(self.target_temp, current_temp)
            
            # Split-range (Topení vs. Chlazení)
            pwm_heat = 0
            pwm_cool = 0
            
            if action > 0:
                pwm_heat = int(action)
            else:
                pwm_cool = int(abs(action))

            # Odeslání do ESP (jen změny)
            if self.serial.is_open():
                if pwm_heat != self.last_pwm_heat:
                    self.serial.write_line(f"SET PWM 0 {pwm_heat}")
                    self.last_pwm_heat = pwm_heat
                
                if pwm_cool != self.last_pwm_cool:
                    self.serial.write_line(f"SET PWM 1 {pwm_cool}")
                    self.last_pwm_cool = pwm_cool
            
            # Data pro vizualizaci
            values["PWM"] = int(action) 
            values["Target"] = self.target_temp

        return values