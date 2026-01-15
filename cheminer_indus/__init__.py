# -*- coding: utf-8 -*-
"""
CheminerIndus QGIS Plugin
"""
def classFactory(iface):
    # Charge et instancie la classe principale depuis plugin.py
    from .plugin import CheminerIndusPlugin
    return CheminerIndusPlugin(iface)
