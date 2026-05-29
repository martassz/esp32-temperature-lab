import os

from typing import Optional, Set
from PySide6.QtCore import Slot, QTimer, Signal
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox, QFileDialog
)

from core.serial_manager import SerialManager
from core.parser import parse_json_message
from core.measurement_manager import MeasurementManager 
from ui.styles import STYLESHEET

from ui.panels.sidebar import Sidebar
from ui.panels.cards import ValueCardsPanel
from ui.realtime_plot import RealtimePlotWidget
from ui.dialogs.sensor_config import SensorConfigDialog
from ui.dialogs.measurement_config import MeasurementConfigDialog
from measurements.part_one import PartOneMeasurement
from measurements.part_two import PartTwoMeasurement
from measurements.part_three import PartThreeMeasurement
from measurements.part_three_test import PartThreeTestMeasurement 

class MainWindow(QMainWindow):
    # Custom signals for asynchronous communication events
    handshake_received_signal = Signal()
    connection_lost_signal = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Porovnávání způsobů měření teploty prostředí")
        self.resize(1200, 750)
        self.setStyleSheet(STYLESHEET)

        # State variables for deferred PWM configuration
        self._pending_pwm_channel = 0
        self._pending_pwm_value = 0

        # Initialize hardware communication and measurement logic managers
        self.serial_mgr = SerialManager()
        self.serial_mgr.set_connection_lost_callback(self.connection_lost_signal.emit)
        self.connection_lost_signal.connect(self._on_unexpected_disconnect)
        
        self.meas_mgr = MeasurementManager(self.serial_mgr)
        
        # Sensor inventory and filtering states
        self.allowed_sensors: Set[str] = set()
        self.detected_sensors: list[str] = []
        self.measurement_params = {}

        # Connect measurement manager signals to UI slots
        self.meas_mgr.data_received.connect(self._on_measurement_data)
        self.meas_mgr.progress_updated.connect(self._on_measurement_progress)
        self.meas_mgr.finished.connect(self._on_measurement_finished)
        self.meas_mgr.error_occurred.connect(lambda msg: QMessageBox.warning(self, "Chyba", msg))

        self.handshake_received_signal.connect(self._on_handshake_ok)

        # Timer to handle connection timeouts during the handshake phase
        self.handshake_timer = QTimer()
        self.handshake_timer.setSingleShot(True)
        self.handshake_timer.timeout.connect(self._on_handshake_timeout)

        self._init_ui()
        
        # Select the first available measurement type by default
        available_types = self.meas_mgr.get_available_types()
        if available_types:
            first_type = available_types[0]
            self._on_measurement_type_changed(first_type)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Initialize and connect the sidebar panel
        self.sidebar = Sidebar(self.meas_mgr.get_available_types())
        self.sidebar.connect_requested.connect(self._handle_connect_request)
        self.sidebar.disconnect_requested.connect(self._handle_disconnect_request)
        self.sidebar.start_measurement_clicked.connect(self._start_measurement)
        self.sidebar.stop_measurement_clicked.connect(self._stop_measurement)
        self.sidebar.sensor_settings_clicked.connect(self._open_sensor_settings)
        self.sidebar.measurement_type_changed.connect(self._on_measurement_type_changed)
        self.sidebar.pwm_changed.connect(self._on_pwm_changed)
        self.sidebar.export_clicked.connect(self._on_export_clicked)
        self.sidebar.measurement_settings_clicked.connect(self._open_measurement_settings)

        # Set up the main data visualization area
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        self.cards_panel = ValueCardsPanel()
        right_layout.addWidget(self.cards_panel)
        
        self.plot_widget = RealtimePlotWidget(time_window_s=60.0)
        right_layout.addWidget(self.plot_widget, stretch=1)

        layout.addWidget(self.sidebar)
        layout.addLayout(right_layout)

    @Slot(str)
    def _on_measurement_type_changed(self, type_name: str):
        # Purge existing visualization data upon measurement profile switch
        self.plot_widget.clear()
        self.cards_panel.clear()

        self._set_default_allowed_sensors(type_name)

        show_ref = self.meas_mgr.should_show_reference(type_name)
        self.plot_widget.set_reference_mode(show_ref)

        # Configure dynamic UI components based on the selected measurement profile
        if type_name == PartOneMeasurement.DISPLAY_NAME:
            self.sidebar.show_pwm_controls()
            self.plot_widget.set_dual_axis_mode(True)

        elif type_name == PartTwoMeasurement.DISPLAY_NAME:
            self.sidebar.show_pwm_controls(show_filter=False)
            self.plot_widget.set_dual_axis_mode(False)

        elif type_name == PartThreeMeasurement.DISPLAY_NAME:
            self.sidebar.show_regulation_controls()
            self.plot_widget.set_dual_axis_mode(False)
            self.plot_widget.set_time_window(10.0)

        else:
            self.sidebar.show_simple_controls()
            self.plot_widget.set_dual_axis_mode(False)

        # Manage specific export button visibility for automated vs. test regulation
        if type_name in [PartThreeMeasurement.DISPLAY_NAME, PartThreeTestMeasurement.DISPLAY_NAME]:
            self.sidebar.show_regulation_controls()
            self.plot_widget.set_dual_axis_mode(False)
            self.plot_widget.set_time_window(10.0)
            
            if type_name == PartThreeMeasurement.DISPLAY_NAME:
                self.sidebar.btn_export.hide()
            else:
                self.sidebar.btn_export.show()
        else:
            if hasattr(self.sidebar, 'btn_export'):
                self.sidebar.btn_export.show()
        

    @Slot(str)
    def _start_measurement(self, type_name: str):
        self.cards_panel.clear()
        self.plot_widget.clear()
        self.sidebar.progress.setValue(0)
        
        filter_state = self.sidebar.is_filter_checked()
        
        # Assemble runtime parameters based on the active measurement profile
        kwargs = {}
        if type_name in [PartOneMeasurement.DISPLAY_NAME, PartTwoMeasurement.DISPLAY_NAME]:
            kwargs = {
                "pwm_channel": self._pending_pwm_channel,
                "pwm_value": self._pending_pwm_value,
                "adc_filter": filter_state
            }
        elif type_name == PartThreeMeasurement.DISPLAY_NAME:
            target = self.sidebar.sb_target.value()
            kwargs = {
                "target_temp": target,
                "on_steady_state": self._handle_auto_steady_state_end
            }

        elif type_name == PartThreeTestMeasurement.DISPLAY_NAME:
            target = self.sidebar.sb_target.value()
            kwargs = {
                "target_temp": target
            }

        params = self.measurement_params.get(type_name)
        duration_s = params["duration"] if params else None
        sample_rate_hz = params["rate"] if params else None

        # Dispatch the start command to the measurement manager
        self.meas_mgr.start_measurement(type_name, duration_s=duration_s, sample_rate_hz=sample_rate_hz, **kwargs)
        
        if self.meas_mgr.is_running():
            self.sidebar.set_measurement_running(True)
            
        # Adjust plotting viewport based on the scheduled duration
        dur = duration_s if duration_s else self.meas_mgr.get_duration()
        self.plot_widget.set_time_window(60.0 if dur > 300 else dur)

        

    @Slot()
    def _stop_measurement(self):
        self.meas_mgr.stop_measurement()

    def _get_best_export_path(self):
        """Resolves the most appropriate default directory for data export."""
        candidates = []
        
        # Query Windows-specific profile paths
        if os.name == 'nt':
            user_profile = os.environ.get('USERPROFILE')
            if user_profile:
                candidates.append(os.path.join(user_profile, 'Downloads'))
                candidates.append(os.path.join(user_profile, 'Desktop'))

        # Fallback to standard cross-platform home directory structures
        home = os.path.expanduser("~")
        candidates.append(os.path.join(home, 'Downloads'))
        candidates.append(os.path.join(home, 'Desktop'))
        candidates.append(os.path.join(home, 'Documents'))
        candidates.append(home)

        # Validate existence of the resolved paths
        for path in candidates:
            try:
                if path and os.path.exists(path):
                    return path
            except Exception:
                continue
                
        return ""

    @Slot()
    def _on_export_clicked(self):
        default_dir = self._get_best_export_path()

        filename, _ = QFileDialog.getSaveFileName(self, "Uložit CSV", default_dir, "CSV (*.csv)")
        if not filename:
            return

        sensors_to_export = self.allowed_sensors
        current_type = self.sidebar.combo_type.currentText()
        
        # Exclude voltage sensors from export unless explicitly required by the profile
        if not sensors_to_export and current_type != PartOneMeasurement.DISPLAY_NAME:
            sensors_to_export = {s for s in self.detected_sensors if not s.startswith("V_")}

        if self.meas_mgr.export_data(filename, sensors_to_export):
            QMessageBox.information(self, "OK", "Data exportována.")
        else:
            QMessageBox.warning(self, "Chyba", "Nelze exportovat data (žádná data k dispozici?).")

    @Slot(int, int)
    def _on_pwm_changed(self, channel: int, value: int):
        # Buffer the selected PWM parameters to be applied upon measurement start
        self._pending_pwm_channel = channel
        self._pending_pwm_value = value

    @Slot(float, dict)
    def _on_measurement_data(self, t_s: float, values: dict):
        current_type = self.sidebar.combo_type.currentText()

        # Inject regulation metadata (PWM/Target) into the telemetry stream if applicable
        if current_type in [PartThreeMeasurement.DISPLAY_NAME, PartThreeTestMeasurement.DISPLAY_NAME]:
             meas = self.meas_mgr._current_measurement
             if hasattr(meas, "perform_regulation_logic"):
                 values = meas.perform_regulation_logic(values)

        # Strip raw voltage readings for thermal-only measurement profiles
        if current_type != PartOneMeasurement.DISPLAY_NAME:
            values = {k: v for k, v in values.items() if not k.startswith("V_")}

        # Apply active user-defined sensor filters
        if self.allowed_sensors:
            filtered = {k: v for k, v in values.items() if k in self.allowed_sensors}
            
            # Re-inject regulation parameters bypassing the standard sensor filter
            if current_type in [PartThreeMeasurement.DISPLAY_NAME, PartThreeTestMeasurement.DISPLAY_NAME]:
                if "PWM" in values: filtered["PWM"] = values["PWM"]
                if "Target" in values: filtered["Target"] = values["Target"]
        else:
            filtered = values
            
        # Dispatch filtered payload to the UI card components
        if filtered:
            self.cards_panel.update_values(filtered)
            
        # Prepare the dataset for plotting by omitting non-graphable metrics
        plot_values = filtered.copy()
        
        if current_type in [PartThreeMeasurement.DISPLAY_NAME, PartThreeTestMeasurement.DISPLAY_NAME]:
            keys_to_remove = [k for k in plot_values.keys() if "PWM" in k or k == "H_BME"]
            for k in keys_to_remove:
                del plot_values[k]

        self.plot_widget.add_point(t_s, plot_values)

    @Slot(float)
    def _on_measurement_progress(self, fraction: float):
        val = max(0, min(100, int(fraction * 100)))
        self.sidebar.progress.setValue(val)

    @Slot()
    def _on_measurement_finished(self):
        # Ignore spurious finish signals originating from aborted sessions
        if self.meas_mgr.is_running():
            return
            
        self.sidebar.set_measurement_running(False)
        
        # Suppress the default completion prompt for profiles with custom termination handling
        if self.sidebar.combo_type.currentText() != PartThreeMeasurement.DISPLAY_NAME:
            QMessageBox.information(self, "Hotovo", "Měření dokončeno.")
    
    @Slot(str)
    def _handle_connect_request(self, port: str):
        try:
            self.serial_mgr.open(port)
            self.serial_mgr.set_line_callback(self._wait_for_handshake)
            self.sidebar.set_waiting_state()
            self.handshake_timer.start(3000)
        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Port nelze otevřít:\n{e}")
            self.sidebar.set_connected_state(False)

    def _wait_for_handshake(self, line: str):
        # Parse the initial hardware state vector to determine available peripherals
        msg = parse_json_message(line)
        if msg and msg.get("type") == "hello":
            self.detected_sensors = []
            
            if str(msg.get("tmp")).lower() == "true":
                self.detected_sensors.append("T_TMP")

            if str(msg.get("bme")).lower() == "true":
                self.detected_sensors.extend(["T_BME", "H_BME"])
            
            if str(msg.get("adc")).lower() == "true":
                self.detected_sensors.extend(["V_ADS_R", "V_ADS_NTC", "V_ESP_R", "V_ESP_NTC"])
                
            try:
                dallas_count = int(msg.get("dallas", 0))
                for i in range(dallas_count):
                    self.detected_sensors.append(f"T_DS{i}")
            except: pass

            if str(msg.get("pt1000")).lower() == "true":
                self.detected_sensors.extend(["V_PT1000", "T_PT1000"])
            
            print(f"Detekováno: {self.detected_sensors}")
            self.handshake_received_signal.emit()

    @Slot()
    def _on_handshake_ok(self):
        self.handshake_timer.stop()
        self.sidebar.set_connected_state(True)

        current_type = self.sidebar.combo_type.currentText()
        self._set_default_allowed_sensors(current_type)

        QMessageBox.information(self, "Připojeno", "Spojení navázáno.")

    @Slot()
    def _on_handshake_timeout(self):
        self.serial_mgr.close()
        self.sidebar.set_connected_state(False)
        QMessageBox.warning(self, "Timeout", "ESP32 neodpovědělo.")

    @Slot()
    def _handle_disconnect_request(self):
        self.meas_mgr.stop_measurement()
        self.serial_mgr.close()

        self.detected_sensors = []
        self.allowed_sensors = set()

        self.sidebar.set_connected_state(False)
        self.sidebar.set_measurement_running(False)
        self.cards_panel.clear()
        self.plot_widget.clear()
        
    @Slot()
    def _set_default_allowed_sensors(self, current_type: str):
        """Constructs the default active sensor mask based on the selected profile."""
        if not self.detected_sensors:
            self.allowed_sensors = set()
            return

        sensors_to_show = list(self.detected_sensors)
        
        if current_type == PartOneMeasurement.DISPLAY_NAME:
            sensors_to_show = [s for s in sensors_to_show if s == "T_TMP" or s.startswith("V_")]
        elif current_type == PartTwoMeasurement.DISPLAY_NAME:
            sensors_to_show = [s for s in sensors_to_show if s == "T_TMP" or s.startswith("T_DS")]
        else:
            sensors_to_show = [s for s in sensors_to_show if not s.startswith("V_")]

        self.allowed_sensors = set(sensors_to_show)

    def _open_sensor_settings(self):
        current_type = self.sidebar.combo_type.currentText()
        sensors_to_show = list(self.detected_sensors)
        
        # Restrict the available configuration options depending on the active measurement mode
        if current_type == PartOneMeasurement.DISPLAY_NAME:
            sensors_to_show = [s for s in sensors_to_show if s == "T_TMP" or s.startswith("V_")]
        elif current_type == PartTwoMeasurement.DISPLAY_NAME:
            sensors_to_show = [s for s in sensors_to_show if s == "T_TMP" or s.startswith("T_DS")]
        else:
            sensors_to_show = [s for s in sensors_to_show if not s.startswith("V_")]

        dlg = SensorConfigDialog(self.allowed_sensors, sensors_to_show, self)
        
        if dlg.exec():
            self.allowed_sensors = dlg.get_allowed_sensors()
            # Force a re-render of the value cards to eliminate stale data
            self.cards_panel.clear()

    @Slot()
    def _open_measurement_settings(self):
        current_type = self.sidebar.combo_type.currentText()

        # Extract baseline parameters from the measurement class definitions
        if current_type not in self.measurement_params:
            cls = self.meas_mgr._types.get(current_type)
            def_dur = int(getattr(cls, 'DURATION_S', 600))
            def_rate = float(getattr(cls, 'SAMPLE_RATE_HZ', 1.0))
            self.measurement_params[current_type] = {"duration": def_dur, "rate": def_rate}

        params = self.measurement_params[current_type]

        dlg = MeasurementConfigDialog(params["duration"], params["rate"], self)
        if dlg.exec():
            # Update the configuration state and adjust the plotting viewport accordingly
            new_dur, new_rate = dlg.get_values()
            self.measurement_params[current_type] = {"duration": new_dur, "rate": new_rate}
            self.plot_widget.set_time_window(60.0 if new_dur > 300 else new_dur)

    @Slot()
    def _on_unexpected_disconnect(self):
        """Triggered upon hardware interface failure or abrupt port closure."""
        # Prevent redundant dialogs if the disconnection sequence has already run
        if not self.sidebar._is_connected: 
            return

        self._handle_disconnect_request()
        QMessageBox.critical(self, "Chyba spojení", "Zařízení bylo neočekávaně odpojeno!")

    @Slot(float)
    def _on_target_temp_changed(self, val):
        current_type = self.sidebar.combo_type.currentText()
        
        if current_type == PartThreeMeasurement.DISPLAY_NAME:
             # Propagate the updated setpoint directly to the active controller instance
             meas = self.meas_mgr._current_measurement
             if isinstance(meas, PartThreeMeasurement):
                 meas.set_target_temperature(val)
             else:
                 pass

    def _handle_auto_steady_state_end(self):
            """Executes automated shutdown and prompt sequence upon achieving regulation stability."""
            self._stop_measurement()
            
            QMessageBox.information(
                self, 
                "Měření dokončeno", 
                "Bylo změřeno 10 vzorků.\n"
                "Nyní vyberte, kam chcete CSV uložit."
            )
            
            self._on_export_clicked()

    def closeEvent(self, event):
        # Guarantee safe closure of the serial interface before terminating the process
        if self.serial_mgr.is_open():
             self._handle_disconnect_request()
             
        event.accept()