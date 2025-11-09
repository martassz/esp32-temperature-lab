import threading
import time
from typing import Optional

from measurements.base import BaseMeasurement
from core.parser import parse_json_message, extract_data_values


class StreamingTempMeasurement(BaseMeasurement):
    """
    Měření přes JSON protokol z ESP32.

    ESP32 posílá zprávy tvaru:
      {"type":"data","t_ms":1234,"T_BME":..,"T_DS0":..}

    Tady:
      - čas pro graf bereme z t_ms (zarovnání na 0..DURATION_S)
      - máme watchdog na vypadlou komunikaci
    """

    DURATION_S = 11.0
    SAMPLE_RATE_HZ = 1.0
    NO_DATA_TIMEOUT_S = 3.0  # když po startu / během měření nic nepřijde

    def __init__(self, serial_mgr):
        super().__init__(serial_mgr)
        self._stop_flag = False
        self._worker_thread: Optional[threading.Thread] = None
        self._last_data_time = 0.0
        self._t0_ms: Optional[float] = None  # první t_ms z ESP

    # --- lifecycle ---

    def on_start(self):
        if not self.serial.is_open():
            self.stop()
            return

        self._stop_flag = False
        now = time.time()
        self._last_data_time = now
        self._t0_ms = None

        # Přesměruj příchozí řádky na tohle měření
        self.serial.set_line_callback(self.handle_line)

        # Nastavíme vzorkovací frekvenci na ESP a spustíme
        self.serial.write_line(f"SET RATE {self.SAMPLE_RATE_HZ}")
        self.serial.write_line("START")

        # Watchdog / časování v separátním vlákně
        self._worker_thread = threading.Thread(
            target=self._watchdog_loop, daemon=True
        )
        self._worker_thread.start()

    def on_stop(self):
        self._stop_flag = True

        # pošleme STOP, pokud je link živý
        if self.serial.is_open():
            try:
                self.serial.write_line("STOP")
            except Exception:
                pass

        # odpojíme callback
        self.serial.set_line_callback(None)

    # --- příjem dat z SerialManageru ---

    def handle_line(self, line: str):
        if not self.is_running():
            return

        msg = parse_json_message(line)
        if not msg:
            return

        if msg.get("type") != "data":
            return

        values = extract_data_values(msg)
        if not values:
            return

        t_ms = msg.get("t_ms")
        now_pc = time.time()
        self._last_data_time = now_pc

        # inicializace referenčního času z prvního vzorku
        if isinstance(t_ms, (int, float)) and self._t0_ms is None:
            self._t0_ms = float(t_ms)

        # čas do grafu:
        if isinstance(t_ms, (int, float)) and self._t0_ms is not None:
            t_s = max(0.0, (float(t_ms) - self._t0_ms) / 1000.0)
        else:
            # fallback, kdyby náhodou t_ms chybělo
            t_s = self.now_s()

        self.emit_data(t_s, values)

    # --- interní watchdog ---

    def _watchdog_loop(self):
        """
        - hlídá délku měření
        - hlídá, jestli z ESP chodí data
        - při timeoutu korektně shodí měření a zavře port
        """
        while not self._stop_flag and self.is_running():
            now = time.time()
            elapsed = self.now_s()

            # progress bar podle plánované délky
            self.emit_progress(min(1.0, elapsed / self.DURATION_S))

            # komunikace chcípla -> konec + zavřít port
            if (now - self._last_data_time) > self.NO_DATA_TIMEOUT_S:
                if self.serial.is_open():
                    self.serial.close()
                self.stop()
                return

            # konec měření po DURATION_S
            if elapsed >= self.DURATION_S:
                self.stop()
                return

            time.sleep(0.1)
