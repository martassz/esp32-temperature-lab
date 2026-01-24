import time

class PIController:
    def __init__(self, 
                 kp_heat: float, kp_cool: float, 
                 ki_heat: float, ki_cool: float,
                 kd_heat: float = 0.0, kd_cool: float = 0.0,
                 out_min: float = -100.0, out_max: float = 100.0, 
                 int_active_threshold: float = 2.0,
                 deadband: float = 0.1):
        
        self.kp_heat = kp_heat
        self.kp_cool = kp_cool
        self.ki_heat = ki_heat
        self.ki_cool = ki_cool
        self.kd_heat = kd_heat
        self.kd_cool = kd_cool
        
        self.out_min = out_min
        self.out_max = out_max
        self.int_active_threshold = int_active_threshold
        self.deadband = deadband
        
        self._integral = 0.0
        self._last_time = None
        self._last_error = 0.0
        self._last_input = 0.0
    
    def update(self, setpoint: float, measured_value: float) -> float:
        current_time = time.time()
        
        if self._last_time is None:
            self._last_time = current_time
            self._last_error = setpoint - measured_value
            self._last_input = measured_value
            return 0.0
            
        dt = current_time - self._last_time
        self._last_time = current_time
        
        if dt > 5.0: dt = 0.0 
        if dt <= 0: return 0.0

        error = setpoint - measured_value
        
        # --- 1. ZÁCHRANNÁ BRZDA INTEGRÁLU (NOVÉ) ---
        # Pokud máme topit (error > 0), ale integrál je záporný (zůstatek z chlazení),
        # okamžitě ho vynuluj. A naopak.
        if error > 0 and self._integral < 0:
            self._integral = 0.0
        elif error < 0 and self._integral > 0:
            self._integral = 0.0
        
        # --- 2. DEADBAND ---
        if abs(error) < self.deadband:
            pass # V deadbandu držíme poslední hodnotu integrálu (nezerujeme, aby to nepadalo)
        else:
            # --- 3. I-SLOŽKA ---
            # Počítáme jen pokud jsme v aktivním okně
            if abs(error) < self.int_active_threshold:
                self._integral += (error * dt)
            else:
                self._integral = 0.0

        self._last_error = error

        # --- 4. D-SLOŽKA ---
        d_input = (measured_value - self._last_input) / dt
        self._last_input = measured_value
        
        # --- 5. VÝPOČET VÝSTUPU ---
        mode = "OFF"
        if error > 0: # Topení
            p_term = self.kp_heat * error
            i_term = self.ki_heat * self._integral
            d_term = -self.kd_heat * d_input
            mode = "HEAT"
        else: # Chlazení
            p_term = self.kp_cool * error
            i_term = self.ki_cool * self._integral
            d_term = -self.kd_cool * d_input 
            mode = "COOL"
        
        # Pokud je error přesně 0 (vzácné), výstup by měl být 0 (nebo jen I složka)
        if error == 0:
             p_term, d_term = 0, 0
             i_term = self._integral # Držíme teplotu
        
        output = p_term + i_term + d_term
        
        # --- 6. SATURACE ---
        if output > self.out_max:
            output = self.out_max
            if error > 0: self._integral -= error * dt # Anti-windup
        elif output < self.out_min:
            output = self.out_min
            if error < 0: self._integral -= error * dt

        # --- DIAGNOSTIKA ---
        print(f"[{mode}] Err={error:.2f} | P={p_term:.1f} | I={i_term:.1f} | D={d_term:.1f} | Out={output:.0f}%")

        return output

    def reset(self):
        self._integral = 0.0
        self._last_time = None
        self._last_error = 0.0
        self._last_input = 0.0