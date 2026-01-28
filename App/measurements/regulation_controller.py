import time

class PIController:
    def __init__(self, 
                 kp_heat: float, kp_cool: float, 
                 ki_heat: float, ki_cool: float,
                 kd_heat: float = 0.0, kd_cool: float = 0.0,
                 out_min: float = -100.0, out_max: float = 100.0, 
                 int_active_threshold: float = 2.0,
                 deadband: float = 0.1):
        
        # Konstanty regulátoru
        self.kp_heat = kp_heat
        self.kp_cool = kp_cool
        self.ki_heat = ki_heat
        self.ki_cool = ki_cool
        self.kd_heat = kd_heat
        self.kd_cool = kd_cool
        
        # Limity a nastavení
        self.out_min = out_min
        self.out_max = out_max
        self.int_active_threshold = int_active_threshold
        self.deadband = deadband
        
        # Stavové proměnné
        self._integral = 0.0
        self._last_time = None
        self._last_error = 0.0
        self._last_input = 0.0  
    
    def update(self, setpoint: float, measured_value: float) -> float:
        current_time = time.time()
        
        # --- 0. INICIALIZACE ---
        if self._last_time is None:
            self._last_time = current_time
            self._last_error = setpoint - measured_value
            self._last_input = measured_value
            return 0.0
            
        dt = current_time - self._last_time
        self._last_time = current_time
        
        if dt > 5.0: dt = 0.0 
        if dt <= 0: return 0.0

        # --- 1. FILTR ŠUMU (EMA - 0.5 / 0.5) ---
        # Zrychlený filtr. Odstraní šum, ale nezpožďuje signál.
        # Důležité pro to, aby regulátor viděl "pravdu" včas.
        if self._last_input != 0.0:
            measured_value = (0.5 * measured_value) + (0.5 * self._last_input)

        # Výpočet chyby
        error = setpoint - measured_value
        
        # --- 2. VÝBĚR KONSTANT (TOPENÍ vs CHLAZENÍ) ---
        # Podle toho, jestli jsme pod nebo nad cílem, vybereme sadu parametrů.
        if error > 0:
            kp, ki, kd = self.kp_heat, self.ki_heat, self.kd_heat
            mode = "HEAT"
        else:
            kp, ki, kd = self.kp_cool, self.ki_cool, self.kd_cool
            mode = "COOL"

        # --- 3. I-SLOŽKA: CHYTRÝ ALGORITMUS (CLAMPING) ---
        
        # A) Načítání integrálu
        if abs(error) < self.deadband:
            pass # V toleranci neděláme nic
        elif abs(error) < self.int_active_threshold:
            # POZOR ZMĚNA: Násobíme Ki už zde. 
            # self._integral nyní přímo reprezentuje "akumulovaný výkon v %".
            self._integral += (error * ki * dt)
        else:
            # Jsme moc daleko, integrál by jen škodil.
            self._integral = 0.0

        # B) BEZPEČNOSTNÍ LIMIT (ANTI-WINDUP CLAMPING)
        # Toto je ten "strop", o kterém jsme mluvili.
        # 35.0 % je hodnota, která stačí na udržení teploty, ale nezpůsobí velký přelet.
        # Integrál se o tento strop "opře" a nebude růst dál.
        I_LIMIT = 45.0
        
        if self._integral > I_LIMIT:
            self._integral = I_LIMIT
        elif self._integral < -I_LIMIT:
            self._integral = -I_LIMIT
            
        # Zrušili jsme to staré "nulování při přechodu nuly", 
        # protože způsobovalo propady teploty.

        # --- 4. D-SLOŽKA (DERIVACE) ---
        d_input = (measured_value - self._last_input) / dt
        self._last_input = measured_value
        
        # --- 5. VÝPOČET VÝSTUPU ---
        p_term = kp * error
        i_term = self._integral  # Ki už je započítáno v integrálu
        d_term = -kd * d_input   # Brzda
        
        # Speciální případ pro nulovou chybu
        if error == 0:
             p_term, d_term = 0, 0
        
        output = p_term + i_term + d_term

        # --- 6. SATURACE (OŘEZÁNÍ NA 100%) ---
        if output > self.out_max:
            output = self.out_max
            # Zabráníme dalšímu růstu integrálu, pokud jsme na 100% (extra pojistka)
            if error > 0: self._integral -= (error * ki * dt) 
        elif output < self.out_min:
            output = self.out_min
            if error < 0: self._integral -= (error * ki * dt)

        # --- DIAGNOSTIKA ---
        print(f"[{mode}] Err={error:.3f} | P={p_term:.1f} | I={i_term:.1f} | D={d_term:.1f} | Out={output:.0f}%")

        return output

    def reset(self):
        self._integral = 0.0
        self._last_time = None
        self._last_error = 0.0
        self._last_input = 0.0