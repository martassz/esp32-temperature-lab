import time

class PIController:
    def __init__(self, 
                 kp_heat: float, kp_cool: float, 
                 ki_heat: float, ki_cool: float,
                 kd_heat: float = 0.0, kd_cool: float = 0.0,
                 out_min: float = -100.0, out_max: float = 100.0, 
                 int_active_threshold: float = 2.0,
                 deadband: float = 0.1):
        
        # Core PID tuning coefficients
        self.kp_heat = kp_heat
        self.kp_cool = kp_cool
        self.ki_heat = ki_heat
        self.ki_cool = ki_cool
        self.kd_heat = kd_heat
        self.kd_cool = kd_cool
        
        # Operational constraints and bounds
        self.out_min = out_min
        self.out_max = out_max
        self.int_active_threshold = int_active_threshold
        self.deadband = deadband
        
        # Runtime state registers
        self._integral = 0.0
        self._last_time = None
        self._last_error = 0.0
        self._last_input = 0.0  
    
    def update(self, setpoint: float, measured_value: float) -> float:
        current_time = time.time()
        
        # --- 0. INITIALIZATION ---
        if self._last_time is None:
            self._last_time = current_time
            self._last_error = setpoint - measured_value
            self._last_input = measured_value
            return 0.0
            
        dt = current_time - self._last_time
        self._last_time = current_time
        
        # Enforce delta-time caps to prevent massive integral jumps after arbitrary pauses
        if dt > 5.0: dt = 0.0 
        if dt <= 0: return 0.0

        # --- 1. SIGNAL CONDITIONING (EMA - 0.5 / 0.5) ---
        # Applies a fast exponential moving average filter to suppress high-frequency noise
        # without introducing critical phase delays to the control loop.
        if self._last_input != 0.0:
            measured_value = (0.5 * measured_value) + (0.5 * self._last_input)

        error = setpoint - measured_value
        
        # --- 2. COEFFICIENT ROUTING (P and D components) ---
        if error > 0:
            kp, kd = self.kp_heat, self.kd_heat
            mode = "HEAT"
        else:
            kp, kd = self.kp_cool, self.kd_cool
            mode = "COOL"

        # --- 3. I-COMPONENT: THERMAL ACCUMULATION ---
        # The integral gain dynamically adapts to the current thermal bias of the system
        # to properly counteract asymmetric hardware efficiencies.
        if self._integral >= 0:
            ki_active = self.ki_heat  
        else:
            ki_active = self.ki_cool  

        if abs(error) < self.deadband:
            pass
        elif abs(error) < self.int_active_threshold:
            # Symmetrical accumulation rate logic within the active threshold
            self._integral += (error * ki_active * dt)
        else:
            self._integral = 0.0

        ki = ki_active

        # B) ANTI-WINDUP CLAMPING
        # Establishes a hard ceiling to prevent deep integral saturation, ensuring
        # the system can reactively transition states without excessive overshoot.
        I_LIMIT = 45.0
        
        if self._integral > I_LIMIT:
            self._integral = I_LIMIT
        elif self._integral < -I_LIMIT:
            self._integral = -I_LIMIT

        # --- 4. D-COMPONENT (DERIVATIVE) ---
        d_input = (measured_value - self._last_input) / dt
        self._last_input = measured_value
        
        # --- 5. OUTPUT COMPUTATION ---
        p_term = kp * error
        i_term = self._integral  
        d_term = -kd * d_input   
        
        # Suppress phantom control signals within perfect state equilibrium
        if error == 0:
             p_term, d_term = 0, 0
        
        output = p_term + i_term + d_term

        # --- 6. ACTUATOR SATURATION SCALING ---
        if output > self.out_max:
            output = self.out_max
            # Secondary clamp: Prevent integral growth if hardware is completely maxed out
            if error > 0: self._integral -= (error * ki * dt) 
        elif output < self.out_min:
            output = self.out_min
            if error < 0: self._integral -= (error * ki * dt)

        # --- DIAGNOSTICS ---
        print(f"[{mode}] Err={error:.3f} | P={p_term:.1f} | I={i_term:.1f} | D={d_term:.1f} | Out={output:.0f}%")

        return output

    def reset(self):
        self._integral = 0.0
        self._last_time = None
        self._last_error = 0.0
        self._last_input = 0.0