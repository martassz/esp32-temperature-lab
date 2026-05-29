from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QFrame, QVBoxLayout, 
    QLabel, QScrollArea
)
from PySide6.QtCore import Qt
from core.sensors import get_sensor_name, get_sensor_unit, get_sensor_sort_key

class ValueCardsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Expand height boundary to comfortably accommodate multi-line card text
        self.setFixedHeight(140) 
        self._labels = {} 
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        # Suppress vertical scroll as the horizontal layout handles the primary axis overflow
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) 
        scroll.setStyleSheet("background-color: #1e1e1e; border: none;")
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: #1e1e1e;")
        
        self.cards_layout = QHBoxLayout(self.container)
        self.cards_layout.setContentsMargins(20, 10, 20, 10)
        self.cards_layout.setSpacing(15)
        self.cards_layout.addStretch()
        
        scroll.setWidget(self.container)
        main_layout.addWidget(scroll)

    def update_values(self, values: dict):
        sorted_keys = sorted(values.keys(), key=get_sensor_sort_key)
        
        for key in sorted_keys:
            val = values[key]
            unit = get_sensor_unit(key)
            text_val = f"{val:.2f} {unit}"
            
            if key in self._labels:
                self._labels[key].setText(text_val)
            else:
                self._create_card(key, text_val)

    def clear(self):
        # Purge all dynamically generated card widgets and clear internal references
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._labels.clear()
        self._labels = {}

    def _create_card(self, key: str, initial_text: str):
        pretty_name = get_sensor_name(key)

        frame = QFrame()
        frame.setObjectName("ValueCard")
        # Enforce fixed width for consistent alignment across the panel
        frame.setFixedWidth(170)
        # Minimum height ensures layout stability when word wrapping executes
        frame.setMinimumHeight(100) 
        
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
        l.setContentsMargins(8, 12, 8, 12)
        l.setSpacing(5)
        
        lbl_title = QLabel(pretty_name)
        lbl_title.setObjectName("ValueTitle")
        lbl_title.setAlignment(Qt.AlignCenter)
        # Enable word wrapping to handle extended sensor nomenclatures
        lbl_title.setWordWrap(True) 
        
        lbl_title.setStyleSheet("color: #007acc; font-size: 13px; font-weight: bold;")
        
        lbl_val = QLabel(initial_text)
        lbl_val.setObjectName("ValueNumber")
        lbl_val.setAlignment(Qt.AlignCenter)
        lbl_val.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: bold;")
        
        l.addWidget(lbl_title)
        l.addWidget(lbl_val)
        
        self._labels[key] = lbl_val
        idx = self.cards_layout.count() - 1
        self.cards_layout.insertWidget(idx, frame)