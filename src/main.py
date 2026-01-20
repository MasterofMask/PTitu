"""
Punto de entrada de la aplicación
"""
import sys
from pathlib import Path

# Añadir el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow


def main():
    """Función principal"""
    app = QApplication(sys.argv)
    app.setApplicationName("PTITU")
    app.setOrganizationName("PTITU")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()