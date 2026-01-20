from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QFrame, QVBoxLayout, 
    QLabel, QScrollArea
)
from PySide6.QtCore import Qt

# Importujeme funkci pro hezké názvy
try:
    from core.sensors import get_sensor_name
except ImportError:
    from ui.realtime_plot import RealtimePlotWidget
    get_sensor_name = RealtimePlotWidget.format_sensor_name

class ValueCardsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(130)
        self._labels = {} 
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background-color: #1e1e1e; border: none;")
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: #1e1e1e;")
        
        self.cards_layout = QHBoxLayout(self.container)
        self.cards_layout.setContentsMargins(20, 15, 20, 15)
        self.cards_layout.setSpacing(15)
        self.cards_layout.addStretch()
        
        scroll.setWidget(self.container)
        main_layout.addWidget(scroll)

    def update_values(self, values: dict):
        for key, val in values.items():
            unit = "°C"
            
            # Identifikace jednotek
            if key.startswith("V_") or key.startswith("ADC") or key.startswith("ESP"):
                unit = "mV"
            elif key.startswith("PWM"):
                unit = "%"
            
            text_val = f"{val:.2f} {unit}"
            
            if key in self._labels:
                self._labels[key].setText(text_val)
            else:
                self._create_card(key, text_val)

    def clear(self):
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._labels.clear()

    def _create_card(self, key: str, initial_text: str):
        pretty_name = get_sensor_name(key)

        frame = QFrame()
        frame.setObjectName("ValueCard")
        frame.setFixedWidth(170)
        
        # --- STYL KARTY ---
        frame.setStyleSheet("""
            QFrame#ValueCard {
                background-color: #333337;
                border: 1px solid #505050;
                border-radius: 8px;
            }
            QLabel {
                background-color: transparent;
                border: none;
            }
        """)
        
        l = QVBoxLayout(frame)
        l.setContentsMargins(10, 10, 10, 10)
        l.setSpacing(2)
        
        # --- NADPIS (NÁZEV SENZORU) ---
        lbl_title = QLabel(pretty_name)
        lbl_title.setObjectName("ValueTitle")
        lbl_title.setAlignment(Qt.AlignCenter)
        
        # ZMĚNA: Použita barva #007acc (stejná jako v Sidebaru)
        lbl_title.setStyleSheet("color: #007acc; font-size: 14px; font-weight: bold;")
        
        # --- HODNOTA ---
        lbl_val = QLabel(initial_text)
        lbl_val.setObjectName("ValueNumber")
        lbl_val.setAlignment(Qt.AlignCenter)
        lbl_val.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: bold;")
        
        l.addWidget(lbl_title)
        l.addWidget(lbl_val)
        
        self._labels[key] = lbl_val
        idx = self.cards_layout.count() - 1
        self.cards_layout.insertWidget(idx, frame)