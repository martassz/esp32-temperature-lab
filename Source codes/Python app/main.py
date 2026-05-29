import sys

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    # Initialize the core application instance
    app = QApplication(sys.argv)

    # Instantiate and display the primary GUI window
    window = MainWindow()
    window.show()

    # Enter the main event loop and ensure clean exit upon termination
    sys.exit(app.exec())


if __name__ == "__main__":
    main()