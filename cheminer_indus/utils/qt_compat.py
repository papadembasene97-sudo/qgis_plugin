# -*- coding: utf-8 -*-
"""Compatibilité Qt entre QGIS 3 (PyQt5) et QGIS 4 (PyQt6)."""

from qgis.PyQt.QtCore import Qt


def _value(name: str, enum_name: str, member_name: str):
    """Retourne Qt.<name> ou Qt.<enum_name>.<member_name>."""
    if hasattr(Qt, name):
        return getattr(Qt, name)
    enum_obj = getattr(Qt, enum_name, None)
    if enum_obj is None:
        raise AttributeError(f"Qt.{name} introuvable")
    value = getattr(enum_obj, member_name, None)
    if value is None:
        raise AttributeError(f"Qt.{enum_name}.{member_name} introuvable")
    return value


def _alias(name: str, value) -> None:
    """Expose Qt.<name> pour garder la compatibilité Qt5 quand possible."""
    if hasattr(Qt, name):
        return
    try:
        setattr(Qt, name, value)
    except Exception:
        # Certaines implémentations Qt peuvent interdire setattr sur Qt.
        pass


QT_FRAMELESS_WINDOW_HINT = _value("FramelessWindowHint", "WindowType", "FramelessWindowHint")
QT_WA_TRANSLUCENT_BACKGROUND = _value("WA_TranslucentBackground", "WidgetAttribute", "WA_TranslucentBackground")
QT_ALIGN_CENTER = _value("AlignCenter", "AlignmentFlag", "AlignCenter")
QT_LEFT_DOCK_WIDGET_AREA = _value("LeftDockWidgetArea", "DockWidgetArea", "LeftDockWidgetArea")
QT_RIGHT_DOCK_WIDGET_AREA = _value("RightDockWidgetArea", "DockWidgetArea", "RightDockWidgetArea")
QT_SMOOTH_TRANSFORMATION = _value("SmoothTransformation", "TransformationMode", "SmoothTransformation")
QT_WAIT_CURSOR = _value("WaitCursor", "CursorShape", "WaitCursor")
QT_CHECKED = _value("Checked", "CheckState", "Checked")
QT_USER_ROLE = _value("UserRole", "ItemDataRole", "UserRole")
QT_MOVE_ACTION = _value("MoveAction", "DropAction", "MoveAction")


def ensure_qt_compat() -> None:
    """Crée les alias Qt5 les plus utilisés par le plugin."""
    _alias("FramelessWindowHint", QT_FRAMELESS_WINDOW_HINT)
    _alias("WA_TranslucentBackground", QT_WA_TRANSLUCENT_BACKGROUND)
    _alias("AlignCenter", QT_ALIGN_CENTER)
    _alias("LeftDockWidgetArea", QT_LEFT_DOCK_WIDGET_AREA)
    _alias("RightDockWidgetArea", QT_RIGHT_DOCK_WIDGET_AREA)
    _alias("SmoothTransformation", QT_SMOOTH_TRANSFORMATION)
    _alias("WaitCursor", QT_WAIT_CURSOR)
    _alias("Checked", QT_CHECKED)
    _alias("UserRole", QT_USER_ROLE)
    _alias("MoveAction", QT_MOVE_ACTION)


ensure_qt_compat()
