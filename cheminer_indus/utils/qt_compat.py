# -*- coding: utf-8 -*-
"""Compatibilité Qt entre QGIS 3 (PyQt5) et QGIS 4 (PyQt6)."""

from qgis.PyQt.QtCore import Qt


def _alias(name: str, enum_name: str, member_name: str) -> None:
    """Expose Qt.<name> si seule la forme Qt.<enum_name>.<member_name> existe."""
    if hasattr(Qt, name):
        return
    enum_obj = getattr(Qt, enum_name, None)
    if enum_obj is None:
        return
    value = getattr(enum_obj, member_name, None)
    if value is None:
        return
    setattr(Qt, name, value)


def ensure_qt_compat() -> None:
    """Crée les alias Qt utilisés dans le plugin pour PyQt6."""
    _alias("FramelessWindowHint", "WindowType", "FramelessWindowHint")
    _alias("WA_TranslucentBackground", "WidgetAttribute", "WA_TranslucentBackground")
    _alias("AlignCenter", "AlignmentFlag", "AlignCenter")
    _alias("LeftDockWidgetArea", "DockWidgetArea", "LeftDockWidgetArea")
    _alias("RightDockWidgetArea", "DockWidgetArea", "RightDockWidgetArea")
    _alias("SmoothTransformation", "TransformationMode", "SmoothTransformation")
    _alias("WaitCursor", "CursorShape", "WaitCursor")
    _alias("Checked", "CheckState", "Checked")


ensure_qt_compat()
