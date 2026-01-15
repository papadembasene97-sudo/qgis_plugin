# cheminer_indus/core/dialogs.py

from qgis.PyQt.QtWidgets import QMessageBox

def show_warning(parent, text: str):
    QMessageBox.warning(parent, "Avertissement", text)
