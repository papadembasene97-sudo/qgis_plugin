# cheminer_indus/plugin.py

from .gui.main_dock import MainDock

class CheminerIndusPlugin:
    """
    Colle simple pour charger/décharger le dock.
    """
    def __init__(self, iface):
        self.iface = iface
        self.dock = None

    def initGui(self):
        self.dock = MainDock(self.iface)
        self.dock.init_gui()

    def unload(self):
        if self.dock:
            self.dock.unload()
            self.dock = None
