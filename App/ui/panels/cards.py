from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QFrame, QVBoxLayout, 
    QLabel, QScrollArea
)
from PySide6.QtCore import Qt
from core.sensors import get_sensor_name, get_sensor_unit, get_sensor_sort_key

class ValueCardsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Zvětšíme výšku celého panelu, aby se tam pohodlně vešly vyšší karty
        self.setFixedHeight(140) 
        self._labels = {} 
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Horizontální scroll je automatický
        scroll.setStyleSheet("background-color: #1e1e1e; border: none;")
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: #1e1e1e;")
        
        self.cards_layout = QHBoxLayout(self.container)
        # Trochu zvětšíme horní/dolní okraj
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
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._labels.clear()
        self._labels = {} # Důležité: vyčistit i slovník labelů!

    def _create_card(self, key: str, initial_text: str):
        pretty_name = get_sensor_name(key)

        frame = QFrame()
        frame.setObjectName("ValueCard")
        # Pevná šířka 170px je ideální
        frame.setFixedWidth(170)
        # Výšku necháme počítat automaticky nebo dáme min-height,
        # aby karty neposkakovaly při změně délky textu.
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
        # Větší odsazení, aby text nebyl nalepený
        l.setContentsMargins(8, 12, 8, 12)
        l.setSpacing(5)
        
        # --- NADPIS (S WORD WRAP) ---
        lbl_title = QLabel(pretty_name)
        lbl_title.setObjectName("ValueTitle")
        lbl_title.setAlignment(Qt.AlignCenter)
        # KLÍČOVÉ: Povolit zalamování řádků
        lbl_title.setWordWrap(True) 
        
        # Zmenšil jsem font na 13px, aby se dlouhé názvy vešly lépe
        # Line-height (odsazení řádků) řeší Qt automaticky docela dobře
        lbl_title.setStyleSheet("color: #007acc; font-size: 13px; font-weight: bold;")
        
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