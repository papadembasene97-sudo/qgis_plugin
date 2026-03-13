# -*- coding: utf-8 -*-
"""
TRACK-EAU-POLL QGIS Plugin
"""
from .utils.qt_compat import ensure_qt_compat

ensure_qt_compat()

def classFactory(iface):
    # Charge et instancie la classe principale depuis plugin.py
    from .plugin import TrackEauPollPlugin
    return TrackEauPollPlugin(iface)
