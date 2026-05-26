from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton
)
from PySide6.QtCore import Qt

class MeasurementConfigDialog(QDialog):
    def __init__(self, current_duration: int, current_rate_hz: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Parametry měření")
        self.setFixedSize(320, 180)
        self.setStyleSheet("""
            QDialog { background-color: #252526; color: #e0e0e0; }
            QLabel { color: #e0e0e0; font-weight: bold; }
            
            /* OPRAVA ČÍSELNÍKU VČETNĚ ŠIPEK */
            QSpinBox { 
                background-color: #333337; 
                color: white; 
                border: 1px solid #505050; 
                border-radius: 3px;
                padding: 4px;
                padding-right: 22px; 
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                background-color: #3e3e42;
                border-left: 1px solid #505050;
            }
            QSpinBox::up-button { border-bottom: 1px solid #505050; }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover { background-color: #505050; }
            /* --------------------------- */

            QPushButton { padding: 6px; border-radius: 3px; font-weight: bold; }
            QPushButton#BtnCancel { background-color: #3e3e42; border: 1px solid #505050; color: white; }
            QPushButton#BtnCancel:hover { background-color: #505050; }
        """)

        layout = QVBoxLayout(self)

        # --- Délka měření ---
        dur_layout = QHBoxLayout()
        dur_layout.addWidget(QLabel("Délka měření [s]:"))
        self.spin_dur = QSpinBox()
        self.spin_dur.setRange(1, 99999)  
        self.spin_dur.setValue(int(current_duration))
        dur_layout.addWidget(self.spin_dur)
        layout.addLayout(dur_layout)

        # --- PERIODA ukládání (Změněno z Hz na sekundy!) ---
        rate_layout = QHBoxLayout()
        rate_layout.addWidget(QLabel("Perioda zápisu [s]:"))
        
        # Převod z aktuální frekvence na periodu: Perioda = 1 / Frekvence
        current_period = 1
        if current_rate_hz > 0:
            current_period = max(1, int(round(1.0 / current_rate_hz)))

        self.spin_period = QSpinBox()
        self.spin_period.setRange(1, 99999) 
        self.spin_period.setValue(current_period)
        rate_layout.addWidget(self.spin_period)
        layout.addLayout(rate_layout)

        layout.addStretch()

        # --- Chybová hláška ---
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #da3633; font-weight: bold; font-size: 11px;")
        self.lbl_error.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_error)

        # --- Tlačítka ---
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Uložit")
        self.btn_ok.setCursor(Qt.PointingHandCursor)
        self.btn_ok.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("Zrušit")
        btn_cancel.setObjectName("BtnCancel")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        self.spin_dur.valueChanged.connect(self._validate_inputs)
        self.spin_period.valueChanged.connect(self._validate_inputs)

        self._validate_inputs()

    def _validate_inputs(self):
        dur = self.spin_dur.value()
        period = self.spin_period.value()
        error_msgs = []

        if dur < 60 or dur > 3600:
            error_msgs.append("Čas musí být 60 až 3600 s")
            
        if period < 1 or period > 60:
            error_msgs.append("Perioda musí být 1 až 60 s")

        if error_msgs:
            self.lbl_error.setText(" | ".join(error_msgs))
            self.btn_ok.setEnabled(False)
            self.btn_ok.setStyleSheet("background-color: #3e3e42; color: #808080; border: 1px solid #505050;")
        else:
            self.lbl_error.setText("")
            self.btn_ok.setEnabled(True)
            self.btn_ok.setStyleSheet("background-color: #007acc; color: white; border: none;")

    def get_values(self):
        # Před odesláním do ESP32 převedeme sekundy nenápadně zpět na frekvenci [Hz]
        rate_hz = 1.0 / self.spin_period.value()
        return self.spin_dur.value(), rate_hz