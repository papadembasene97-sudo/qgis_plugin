# -*- coding: utf-8 -*-
# cheminer_indus/core/autosave_manager.py

from __future__ import annotations

import os
import json
from typing import Optional, Dict, Any

from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox
from qgis.core import Qgis

# Important : indique explicitement ce que le module exporte
__all__ = ["AutoSaveManager"]


class AutoSaveManager:
    """
    Gestionnaire de sauvegarde automatique de l'état du plugin dans un fichier .txt (JSON).

    - Propose à l'utilisateur de choisir/créer un fichier projet
    - Sauvegarde l'état après les actions importantes
    - Permet de recharger automatiquement l'état au démarrage
    """

    def __init__(self, iface, plugin_name: str = "CheminerIndus"):
        self.iface = iface
        self.plugin_name = plugin_name
        self.path: Optional[str] = None

    # ------------------------------------------------------------------
    # Demande creation / chargement fichier de sauvegarde
    # ------------------------------------------------------------------
    def ensure_project(self, parent) -> None:
        """
        Si aucun fichier projet n'est encore choisi, demande à l'utilisateur
        s'il souhaite en créer/choisir un, puis mémorise le chemin.
        """
        if self.path:
            return

        resp = QMessageBox.question(
            parent,
            "Sauvegarde automatique",
            (
                "Voulez-vous créer ou choisir un fichier de projet pour la "
                "sauvegarde automatique de CheminerIndus ?\n\n"
                "Ce fichier conservera l'état du cheminement (sélections, visites,\n"
                "industriel désigné, astreinte, étiquettes, bassin de collecte...)."
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if resp != QMessageBox.Yes:
            return

        path, _ = QFileDialog.getSaveFileName(
            parent,
            "Fichier de projet CheminerIndus",
            "",
            "Texte (*.txt)"
        )
        if not path:
            return

        self.path = path

    # ------------------------------------------------------------------
    # Sauvegarde
    # ------------------------------------------------------------------
    def save(self, state: Dict[str, Any]) -> None:
        """
        Sauvegarde l'état complet du plugin dans le fichier projet.
        """
        if not self.path:
            return

        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

        except Exception as e:
            msg = f"Erreur sauvegarde automatique : {e}"
            try:
                self.iface.messageBar().pushWarning(self.plugin_name, msg)
            except Exception:
                print("[{}][AutoSave] {}".format(self.plugin_name, msg))

    # ------------------------------------------------------------------
    # Chargement
    # ------------------------------------------------------------------
    def load(self) -> Dict[str, Any]:
        """
        Charge l'état depuis le fichier projet (si présent).
        """
        if not self.path or not os.path.exists(self.path):
            return {}

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)

        except Exception as e:
            msg = f"Erreur chargement automatique : {e}"
            try:
                self.iface.messageBar().pushWarning(self.plugin_name, msg)
            except Exception:
                print("[{}][AutoSave] {}".format(self.plugin_name, msg))

            return {}
