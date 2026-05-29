from typing import Optional, Dict, Type, Set, Any
from PySide6.QtCore import QObject, Signal, QTimer

from core.serial_manager import SerialManager
from measurements.base import BaseMeasurement
from measurements.part_one import PartOneMeasurement
from measurements.part_two import PartTwoMeasurement
from measurements.part_three import PartThreeMeasurement
from measurements.part_three_test import PartThreeTestMeasurement

class MeasurementManager(QObject):
    data_received = Signal(float, dict)
    progress_updated = Signal(float)
    finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, serial_mgr: SerialManager):
        super().__init__()
        self._serial_mgr = serial_mgr
        self._current_measurement: Optional[BaseMeasurement] = None
        
        # Registry mapping display nomenclature to backend handler classes
        self._types = {
            PartOneMeasurement.DISPLAY_NAME: PartOneMeasurement,
            PartTwoMeasurement.DISPLAY_NAME: PartTwoMeasurement,
            PartThreeMeasurement.DISPLAY_NAME: PartThreeMeasurement,
            PartThreeTestMeasurement.DISPLAY_NAME: PartThreeTestMeasurement,
        }

        # Keep-alive heartbeat timer to prevent embedded system timeouts
        self._watchdog_timer = QTimer(self)
        self._watchdog_timer.timeout.connect(self._send_heartbeat)

    def get_available_types(self):
        return list(self._types.keys())

    def start_measurement(self, type_name: str, duration_s: float = None, sample_rate_hz: float = None, **kwargs):
        cls = self._types.get(type_name)
        if not cls:
            self.error_occurred.emit(f"Neznámý typ měření: {type_name}")
            return

        self.stop_measurement()

        try:
            self._current_measurement = cls(self._serial_mgr, **kwargs)
            
            # Dynamically override execution constants if instructed by UI
            if duration_s is not None:
                self._current_measurement.DURATION_S = float(duration_s)
            if sample_rate_hz is not None:
                self._current_measurement.SAMPLE_RATE_HZ = float(sample_rate_hz)
            
            self._current_measurement.set_callbacks(
                on_data=self._on_data_callback,
                on_progress=self.progress_updated.emit,
                on_finished=self.finished.emit
            )

            self._serial_mgr.set_line_callback(self._current_measurement.handle_line)
            self._current_measurement.start()
            
            # Dispatch periodic ping to maintain open communication lock
            self._watchdog_timer.start(2000)
            
        except TypeError as e:
            self.error_occurred.emit(f"Chyba při inicializaci měření: {e}")
            print(f"Init Error: {e}")

    def stop_measurement(self):
        self._watchdog_timer.stop() 
        if self._current_measurement:
            self._current_measurement.stop()

    def _send_heartbeat(self):
        """Transmits periodic payload to prevent target device from sleeping."""
        if self._serial_mgr.is_open():
            self._serial_mgr.write_line("PING")

    def export_data(self, filename: str, allowed_sensors: Optional[Set[str]] = None) -> bool:
        if not self._current_measurement: return False
        
        if hasattr(self._current_measurement, "export_to_csv"):
            return self._current_measurement.export_to_csv(filename, allowed_sensors)
        return False

    def is_running(self) -> bool:
        return self._current_measurement.is_running() if self._current_measurement else False

    def get_duration(self) -> float:
        if self._current_measurement and hasattr(self._current_measurement, "DURATION_S"):
            return self._current_measurement.DURATION_S
        return 60.0

    def _on_data_callback(self, t_s: float, values: dict):
        # --- THERMAL SAFETY INTERLOCK ---
        # Automatically interrupts current sequence if critical structural limits are breached
        for key, value in values.items():
            if key.startswith("T_") and isinstance(value, (int, float)):
                if value >= 42.0:
                    self.stop_measurement()
                    self.error_occurred.emit(
                        f"BEZPEČNOSTNÍ ZASTAVENÍ: Teplota na senzoru {key} dosáhla {value:.1f} °C "
                        "(limit je 42.0 °C)!"
                    )
                    return 

        self.data_received.emit(t_s, values)

    def should_show_reference(self, type_name: str) -> bool:
        measure_cls = self._types.get(type_name)
        if measure_cls:
            return getattr(measure_cls, "SHOW_REFERENCE_CURVE", False)
        return False