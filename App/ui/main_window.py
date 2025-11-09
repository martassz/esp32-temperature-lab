from typing import Optional, Type, Dict

from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QTimer, Slot, Signal
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QPushButton,
    QComboBox,
    QLabel,
    QProgressBar,
    QMessageBox,
)

from core.serial_manager import SerialManager
from ui.realtime_plot import RealtimePlotWidget
from measurements.base import BaseMeasurement
from measurements.streaming_measurement import StreamingTempMeasurement
from measurements.bme_dallas_slow import BmeDallasSlowMeasurement


class MainWindow(QMainWindow):
    # Signály pro bezpečný přenos z vláken do UI
    measurement_data_signal = Signal(float, dict)
    measurement_progress_signal = Signal(float)
    measurement_finished_signal = Signal()

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Temp-Lab PC GUI")
        self.resize(1000, 600)

        self.serial_mgr = SerialManager()
        self.current_measurement: Optional[BaseMeasurement] = None

        # Registry dostupných měření:
        # Stačí přidat nový řádek a nové měření je k dispozici v UI.
        self._measurement_types: Dict[str, Type[BaseMeasurement]] = {
            "Test měření 10s": StreamingTempMeasurement,
            "Test pomalejší měření 60s": BmeDallasSlowMeasurement,
            
            # sem později:
            # "Peltier PWM + teploty": PeltierMeasurement,
            # "Stabilita teploty": StabilityMeasurement,
        }

        self._build_ui()
        self._populate_measurements()
        self._refresh_ports()

        self._progress_timer = QTimer(self)
        self._progress_timer.timeout.connect(self._update_ui_state)
        self._progress_timer.start(300)

        self.measurement_data_signal.connect(self._on_measurement_data_ui)
        self.measurement_progress_signal.connect(self._on_measurement_progress_ui)
        self.measurement_finished_signal.connect(self._on_measurement_finished_ui)

    # --- UI setup ---

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)

        # Panel vlevo: seznam měření
        left_panel = QVBoxLayout()
        left_label = QLabel("Typ měření")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        left_label.setFont(font)

        self.measurement_list = QListWidget()

        left_panel.addWidget(left_label)
        left_panel.addWidget(self.measurement_list)

        # Vpravo: COM, graf, ovládání
        right_panel = QVBoxLayout()

        # Horní panel: COM port
        com_layout = QHBoxLayout()
        com_label = QLabel("COM port:")
        self.com_combo = QComboBox()
        self.com_refresh_btn = QPushButton("Obnovit")
        self.com_connect_btn = QPushButton("Připojit")
        com_layout.addWidget(com_label)
        com_layout.addWidget(self.com_combo)
        com_layout.addWidget(self.com_refresh_btn)
        com_layout.addWidget(self.com_connect_btn)

        # Graf
        # Výchozí okno grafu podle základního měření; při startu jiného
        # měření můžeme přenastavit podle jeho DURATION_S.
        self.plot_widget = RealtimePlotWidget(
            time_window_s=StreamingTempMeasurement.DURATION_S
        )

        # Spodní panel: Start/Stop + progress
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.progress)

        # Poskládat pravý panel
        right_panel.addLayout(com_layout)
        right_panel.addWidget(self.plot_widget)
        right_panel.addLayout(control_layout)

        # Celé okno
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 3)

        # Signály tlačítek
        self.com_refresh_btn.clicked.connect(self._refresh_ports)
        self.com_connect_btn.clicked.connect(self._toggle_connection)
        self.start_btn.clicked.connect(self._start_selected_measurement)
        self.stop_btn.clicked.connect(self._stop_measurement)

    def _populate_measurements(self):
        font = QFont()
        font.setPointSize(12)
        self.measurement_list.setFont(font)

        self.measurement_list.clear()
        for name in self._measurement_types.keys():
            self.measurement_list.addItem(name)

        if self.measurement_list.count() > 0:
            self.measurement_list.setCurrentRow(0)

    # --- COM porty ---

    @Slot()
    def _refresh_ports(self):
        ports = self.serial_mgr.list_ports()
        self.com_combo.clear()
        self.com_combo.addItems(ports)

    @Slot()
    def _toggle_connection(self):
        if self.serial_mgr.is_open():
            self.serial_mgr.close()
            self.com_connect_btn.setText("Připojit")
            return

        port = self.com_combo.currentText()
        if not port:
            QMessageBox.warning(self, "COM port", "Vyber COM port.")
            return

        try:
            self.serial_mgr.open(port)
            self.com_connect_btn.setText("Odpojit")
        except Exception as e:
            QMessageBox.critical(self, "Chyba", f"Nelze otevřít port {port}:\n{e}")

    # --- Start/Stop měření ---

    @Slot()
    def _start_selected_measurement(self):
        if not self.serial_mgr.is_open():
            QMessageBox.warning(self, "Měření", "Nejprve se připoj k ESP32 (COM port).")
            return

        if self.current_measurement and self.current_measurement.is_running():
            return

        item = self.measurement_list.currentItem()
        name = item.text() if item else ""
        cls = self._measurement_types.get(name)

        if cls is None:
            QMessageBox.warning(self, "Měření", "Neznámý typ měření.")
            return

        self.current_measurement = cls(self.serial_mgr)

        # Případně upravit časové okno grafu podle konkrétního měření
        duration = getattr(self.current_measurement, "DURATION_S", 10.0)
        self.plot_widget.set_time_window(duration)

        # Callbacky: jen emitují signály, které Qt doručí do GUI vlákna
        self.current_measurement.set_callbacks(
            on_data=lambda t_s, values: self.measurement_data_signal.emit(t_s, values),
            on_progress=lambda f: self.measurement_progress_signal.emit(f),
            on_finished=lambda: self.measurement_finished_signal.emit(),
        )

        self.plot_widget.clear()
        self.progress.setValue(0)

        self.current_measurement.start()
        self._update_ui_state()

    @Slot()
    def _stop_measurement(self):
        if self.current_measurement:
            self.current_measurement.stop()
        self._update_ui_state()

    # --- Sloty běžící v GUI vlákně (napojené na signály) ---

    @Slot(float, dict)
    def _on_measurement_data_ui(self, t_s: float, values: dict):
        self.plot_widget.add_point(t_s, values)

    @Slot(float)
    def _on_measurement_progress_ui(self, fraction: float):
        val = max(0, min(100, int(fraction * 100)))
        self.progress.setValue(val)

    @Slot()
    def _on_measurement_finished_ui(self):
        self._update_ui_state()

    # --- UI stav ---

    def _update_ui_state(self):
        running = self.current_measurement.is_running() if self.current_measurement else False
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        # Připojení lze měnit jen když nic neběží
        self.com_combo.setEnabled(not running)
        self.com_refresh_btn.setEnabled(not running)
        self.com_connect_btn.setEnabled(not running or not self.serial_mgr.is_open())
