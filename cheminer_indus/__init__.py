# -*- coding: utf-8 -*-
"""
TRACK-EAU-POLL QGIS Plugin
"""
def classFactory(iface):
    # Charge et instancie la classe principale depuis plugin.py
    from .plugin import TrackEauPollPlugin
    return TrackEauPollPlugin(iface)
