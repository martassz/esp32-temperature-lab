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
    handshake_received_signal = Signal()
    connection_lost_signal = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Porovnávání způsobů měření teploty prostředí")
        self.resize(1200, 750)
        self.setStyleSheet(STYLESHEET)

        # Proměnné pro odložené nastavení PWM
        self._pending_pwm_channel = 0
        self._pending_pwm_value = 0

        self.serial_mgr = SerialManager()
        self.serial_mgr.set_connection_lost_callback(self.connection_lost_signal.emit)
        self.connection_lost_signal.connect(self._on_unexpected_disconnect)
        self.meas_mgr = MeasurementManager(self.serial_mgr)
        self.allowed_sensors: Set[str] = set()
        
        self.detected_sensors: list[str] = []

        self.measurement_params = {}

        self.meas_mgr.data_received.connect(self._on_measurement_data)
        self.meas_mgr.progress_updated.connect(self._on_measurement_progress)
        self.meas_mgr.finished.connect(self._on_measurement_finished)
        self.meas_mgr.error_occurred.connect(lambda msg: QMessageBox.warning(self, "Chyba", msg))

        self.handshake_received_signal.connect(self._on_handshake_ok)

        self.handshake_timer = QTimer()
        self.handshake_timer.setSingleShot(True)
        self.handshake_timer.timeout.connect(self._on_handshake_timeout)

        self._init_ui()
        
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
        # Vyčistit graf při změně typu
        self.plot_widget.clear()
        self.cards_panel.clear()

        self._set_default_allowed_sensors(type_name)

        show_ref = self.meas_mgr.should_show_reference(type_name)
        self.plot_widget.set_reference_mode(show_ref)

        if type_name == PartOneMeasurement.DISPLAY_NAME:
            # Část 1: PWM + Filtr + Duální osa
            self.sidebar.show_pwm_controls()
            self.plot_widget.set_dual_axis_mode(True)

        elif type_name == PartTwoMeasurement.DISPLAY_NAME:
            # Část 2: PWM + BEZ filtru + Jednoduchá osa
            self.sidebar.show_pwm_controls(show_filter=False)
            self.plot_widget.set_dual_axis_mode(False)

        elif type_name == PartThreeMeasurement.DISPLAY_NAME:
            self.sidebar.show_regulation_controls()
            self.plot_widget.set_dual_axis_mode(False)
            self.plot_widget.set_time_window(10.0)

        else:
            self.sidebar.show_simple_controls()
            self.plot_widget.set_dual_axis_mode(False)

        # Najdi stávající podmínku pro PartThreeMeasurement a rozšiř ji takto:
        if type_name in [PartThreeMeasurement.DISPLAY_NAME, PartThreeTestMeasurement.DISPLAY_NAME]:
            self.sidebar.show_regulation_controls()
            self.plot_widget.set_dual_axis_mode(False)
            self.plot_widget.set_time_window(10.0)
            
            # Skryjeme tlačítko POUZE pro automatickou část 3, pro testovací ho necháme viditelné!
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

        # Předáme manageru
        self.meas_mgr.start_measurement(type_name, duration_s=duration_s, sample_rate_hz=sample_rate_hz, **kwargs)
        
        if self.meas_mgr.is_running():
            self.sidebar.set_measurement_running(True)
            
        # Zobrazení osy grafu
        dur = duration_s if duration_s else self.meas_mgr.get_duration()
        self.plot_widget.set_time_window(60.0 if dur > 300 else dur)

        

    @Slot()
    def _stop_measurement(self):
        self.meas_mgr.stop_measurement()

    def _get_best_export_path(self):
        """Najde nejlepší dostupnou složku pro uložení souboru."""
        candidates = []
        
        # 1. Zkusíme Windows systémovou cestu k profilu
        if os.name == 'nt':
            user_profile = os.environ.get('USERPROFILE')
            if user_profile:
                candidates.append(os.path.join(user_profile, 'Downloads'))
                candidates.append(os.path.join(user_profile, 'Desktop'))

        # 2. Zkusíme standardní konstrukci přes domovskou složku
        home = os.path.expanduser("~")
        candidates.append(os.path.join(home, 'Downloads'))
        candidates.append(os.path.join(home, 'Desktop'))
        candidates.append(os.path.join(home, 'Documents'))
        candidates.append(home) # Poslední záchrana - domovská složka uživatele

        # Projdeme kandidáty a vrátíme první, který reálně existuje na disku
        for path in candidates:
            try:
                if path and os.path.exists(path):
                    return path
            except Exception:
                continue
                
        return "" # Pokud vše selže, vrátí prázdný řetězec (= složka aplikace)

    @Slot()
    def _on_export_clicked(self):
        default_dir = self._get_best_export_path()

        filename, _ = QFileDialog.getSaveFileName(self, "Uložit CSV", default_dir, "CSV (*.csv)")
        if not filename:
            return

        sensors_to_export = self.allowed_sensors
        
        current_type = self.sidebar.combo_type.currentText()
        
        if not sensors_to_export and current_type != PartOneMeasurement.DISPLAY_NAME:
            sensors_to_export = {s for s in self.detected_sensors if not s.startswith("V_")}

        if self.meas_mgr.export_data(filename, sensors_to_export):
            QMessageBox.information(self, "OK", "Data exportována.")
        else:
            QMessageBox.warning(self, "Chyba", "Nelze exportovat data (žádná data k dispozici?).")

    @Slot(int, int)
    def _on_pwm_changed(self, channel: int, value: int):
        # Jen uložíme hodnotu, odeslání řeší samotná třída měření po startu
        self._pending_pwm_channel = channel
        self._pending_pwm_value = value
        # ZDE JSME ODSTRANILI ŘÁDEK SE self._pending_filter, KTERÝ ZPŮSOBOVAL CHYBU

    @Slot(float, dict)
    def _on_measurement_data(self, t_s: float, values: dict):
        current_type = self.sidebar.combo_type.currentText()

        # 1. Logika regulace (Část 3) - Přidá PWM a Target do 'values'
        if current_type in [PartThreeMeasurement.DISPLAY_NAME, PartThreeTestMeasurement.DISPLAY_NAME]:
             meas = self.meas_mgr._current_measurement
             if hasattr(meas, "perform_regulation_logic"):
                 values = meas.perform_regulation_logic(values)

        # 2. Filtrace napětí (pro Část 2 a 3 odstraníme V_ senzory)
        if current_type != PartOneMeasurement.DISPLAY_NAME:
            values = {k: v for k, v in values.items() if not k.startswith("V_")}

        # 3. Uživatelský výběr senzorů (allowed_sensors)
        if self.allowed_sensors:
            filtered = {k: v for k, v in values.items() if k in self.allowed_sensors}
            
            # --- OPRAVA CHYBY Č. 2 ---
            # Pokud jsme v Části 3 nebo Měření překmitu, musíme ručně vrátit PWM a Target, 
            # protože ty nejsou v seznamu 'allowed_sensors' (nejsou v dialogu)
            if current_type in [PartThreeMeasurement.DISPLAY_NAME, PartThreeTestMeasurement.DISPLAY_NAME]:
                if "PWM" in values: filtered["PWM"] = values["PWM"]
                if "Target" in values: filtered["Target"] = values["Target"]
        else:
            filtered = values
            
        # 4. Aktualizace KARET (Zobrazíme vše)
        if filtered:
            self.cards_panel.update_values(filtered)
            
        # 5. Aktualizace GRAFU (Odstraníme PWM a vlhkost)
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
        # Obrana proti "zbloudilým" signálům ze starého měření
        if self.meas_mgr.is_running():
            return
            
        self.sidebar.set_measurement_running(False)
        
        # Schováme běžné okno pro Část 3, protože ta má svoje vlastní specifické
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
        """Automaticky nastaví povolené senzory podle aktuálně vybrané části."""
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

        # Rovnou uložíme do aktivního filtru aplikace
        self.allowed_sensors = set(sensors_to_show)

    def _open_sensor_settings(self):
        # 1. Zjistíme, jaký je aktuálně vybraný mód
        current_type = self.sidebar.combo_type.currentText()
        
        # 2. Vytvoříme seznam senzorů k zobrazení
        # Začneme se všemi detekovanými
        sensors_to_show = list(self.detected_sensors)
        
        # 3. Aplikujeme filtr podle typu měření:
        if current_type == PartOneMeasurement.DISPLAY_NAME:
            # ČÁST 1: Ponecháme POUZE referenční senzor (T_TMP) a napětí (V_)
            sensors_to_show = [s for s in sensors_to_show if s == "T_TMP" or s.startswith("V_")]
            
        elif current_type == PartTwoMeasurement.DISPLAY_NAME:
            # ČÁST 2: Ponecháme POUZE referenční senzor a Dallasy
            sensors_to_show = [s for s in sensors_to_show if s == "T_TMP" or s.startswith("T_DS")]
            
        else:
            # ČÁST 3 (a případné další): Schováme napětí, necháme všechny teploty
            sensors_to_show = [s for s in sensors_to_show if not s.startswith("V_")]

        # 4. Otevřeme dialog s vyfiltrovaným seznamem
        dlg = SensorConfigDialog(self.allowed_sensors, sensors_to_show, self)
        
        if dlg.exec():
            # Uložíme nově vybrané
            self.allowed_sensors = dlg.get_allowed_sensors()
            
            # Překreslení karet, aby nezůstaly viset staré hodnoty
            self.cards_panel.clear()

    @Slot()
    def _open_measurement_settings(self):
        current_type = self.sidebar.combo_type.currentText()

        # Zjistíme defaultní hodnoty pro danou část přímo z její třídy, pokud je ještě nemáme v paměti
        if current_type not in self.measurement_params:
            cls = self.meas_mgr._types.get(current_type)
            def_dur = int(getattr(cls, 'DURATION_S', 600))
            def_rate = float(getattr(cls, 'SAMPLE_RATE_HZ', 1.0))
            self.measurement_params[current_type] = {"duration": def_dur, "rate": def_rate}

        params = self.measurement_params[current_type]

        # Otevřeme dialog s aktuálními hodnotami
        dlg = MeasurementConfigDialog(params["duration"], params["rate"], self)
        if dlg.exec():
            # Pokud uživatel klikl na Uložit, přepíšeme paměť
            new_dur, new_rate = dlg.get_values()
            self.measurement_params[current_type] = {"duration": new_dur, "rate": new_rate}
            
            # Upravíme i osu grafu podle nového času
            self.plot_widget.set_time_window(60.0 if new_dur > 300 else new_dur)

    @Slot()
    def _on_unexpected_disconnect(self):
        """Zavolá se, když SerialManager detekuje pád spojení (vytržení kabelu)."""
        # Pokud už jsme odpojení, nic neděláme (prevence zdvojených hlášek)
        if not self.sidebar._is_connected: 
            return

        # Využijeme existující logiku pro odpojení (zastaví měření, vyčistí UI)
        self._handle_disconnect_request()
        
        # Informujeme uživatele
        QMessageBox.critical(self, "Chyba spojení", "Zařízení bylo neočekávaně odpojeno!")

    @Slot(float)
    def _on_target_temp_changed(self, val):
        # OPRAVA: Zjistíme typ měření ze Sidebaru, ne z manageru (tam to neexistuje)
        current_type = self.sidebar.combo_type.currentText()
        
        if current_type == PartThreeMeasurement.DISPLAY_NAME:
             # Sáhneme si pro instanci přímo do manageru
             meas = self.meas_mgr._current_measurement
             if isinstance(meas, PartThreeMeasurement):
                 meas.set_target_temperature(val)
             else:
                 # Pokud měření ještě neběží, uložíme si hodnotu pro start
                 # (tuto logiku už máme vyřešenou v _start_measurement načtením ze sidebaru,
                 #  takže zde nemusíme dělat nic)
                 pass

    def _handle_auto_steady_state_end(self):
            """Zavolá se automaticky, jakmile regulace zaznamená 10 vteřin stabilního stavu."""
            # 1. Zastavíme měření (tím se pošle STOP do ESP32 a vypne se PWM)
            self._stop_measurement()
            
            # 2. Informujeme studenty
            QMessageBox.information(
                self, 
                "Měření dokončeno", 
                "Bylo změřeno 10 vzorků.\n"
                "Nyní vyberte, kam chcete CSV uložit."
            )
            
            # 3. Vyvoláme stávající exportní funkci, kterou už v kódu máme!
            self._on_export_clicked()

    def closeEvent(self, event):
        if self.serial_mgr.is_open():
             self._handle_disconnect_request()
             
        event.accept()