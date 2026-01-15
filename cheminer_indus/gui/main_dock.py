# -*- coding: utf-8 -*-
# cheminer_indus/gui/main_dock.py

from __future__ import annotations

import os, json, datetime, tempfile
from typing import Optional, List, Tuple, Set, Dict, Any

from qgis.PyQt.QtCore import Qt, QDate, QTime, QDateTime, QSize, QTimer
from qgis.PyQt.QtGui import QIcon, QPixmap, QColor, QMovie
from qgis.PyQt.QtWidgets import (
    QAction, QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QGridLayout, QMessageBox, QTabWidget,
    QFileDialog, QCheckBox, QDialog, QGroupBox, QTextEdit, QColorDialog,
    QSizePolicy, QApplication, QRadioButton
)

from qgis.core import (
    QgsProject, QgsExpression, QgsFeatureRequest, QgsVectorLayer,
    QgsFeature, QgsGeometry, QgsPointXY, Qgis
)

from ..utils.config             import ICONS_DIR
from ..core.selection           import MapSelectionTool, AstreintSelectionTool
from ..core.tracer              import NetworkTracer
from ..core.industrials         import IndustrialsService
from ..core.diagnostics         import Diagnostics
from ..core.highlight_manager   import HighlightManager
from ..animation.flow_animator  import FlowAnimator
from ..report.pdf_generator     import PDFGenerator
from ..report.photos            import PhotoManager
from ..gui.industrial_dock      import IndustrialDock
from ..gui.diagnostics_dock     import DiagnosticsDock
from ..gui.ai_tab               import AITab
from ..utils.geom_utils         import concave_envelope_from_selected
from ..core.autosave_manager    import AutoSaveManager
from ..gui.main_dock_optimized  import OptimizedNodeOps


# Catégories utilisées dans LABEL_CI
CAT_DEPART       = "Départ_Cheminement"
CAT_VISITE_OUI   = "Pollué"
CAT_VISITE_NON   = "Non_Pollué"
CAT_ASTREINTE    = "Astreinte"
CAT_INDUS_DES    = "Origine_Pollution"


def _safe_json(o: Any) -> Any:
    """Convertit QDate/QTime/QDateTime et autres objets en types JSON."""
    if isinstance(o, (QDate,)):
        return o.toString("yyyy-MM-dd")
    if isinstance(o, (QTime,)):
        return o.toString("HH:mm:ss")
    if isinstance(o, (QDateTime,)):
        return o.toString("yyyy-MM-dd HH:mm:ss")
    try:
        json.dumps(o)
        return o
    except Exception:
        return str(o)


class MainDock:
    """
    Dock principal : CHEMINEMENT, VISITE-INDUS, ACTIONS, COUCHES
    """

    # ---------------------------------------------------------
    # Construction
    # ---------------------------------------------------------
    def __init__(self, iface):
        self.iface  = iface
        self.canvas = iface.mapCanvas()
        self.dock   = None
        self._action = None

        # couches
        self.canal_layer   : Optional[QgsVectorLayer] = None
        self.ouvr_layer    : Optional[QgsVectorLayer] = None
        self.fosse_layer   : Optional[QgsVectorLayer] = None
        self.indus_layer   : Optional[QgsVectorLayer] = None
        self.liaison_layer : Optional[QgsVectorLayer] = None
        self.astreint_layer : Optional[QgsVectorLayer] = None
        self.label_layer   : Optional[QgsVectorLayer] = None  # LABEL_CI

        # services / managers
        self.tracer         : Optional[NetworkTracer] = None
        self.indus_svc      : Optional[IndustrialsService] = None
        self.highlight_mgr   = HighlightManager(self.canvas)
        self.flow_anim       = FlowAnimator(self.canvas)
        self.ph_mgr          = PhotoManager()
        self.auto_mgr        = AutoSaveManager(self.iface, plugin_name="CheminerIndus")

        # UI state
        self.industrial_dock: Optional[IndustrialDock] = None
        self.diag_dock      : Optional[DiagnosticsDock] = None
        self._last_indus_data: Dict[str, Dict[str, str]] = {}

        # selection tools
        self.tool_select    = None
        self.tool_visit     = None
        self.tool_astreint  = None

        # visites & pollueur & astreinte
        self.visited: List[Dict[str, object]] = []
        self.polluter_id   : str = ""
        self.polluter_note : str = ""
        self.astreint_details: Dict[str, object] = {}

        # masque étiquettes (via LABEL_CI)
        self._mask_on = False

        # Optimisations pour désélection de nœuds
        self._node_ops: Optional[OptimizedNodeOps] = None

        # widgets
        self.canal_combo = self.ouvr_combo = self.fosse_combo = None
        self.indus_combo = self.liaison_combo = self.astreint_combo = None
        self.id_input = self.search_input = None
        self.trace_btn = self.flux_btn = None
        self.direction_combo = self.cat_combo = self.func_combo = None
        self.visit_input = None
        self.btn_show_indus = None
        self.note_text = None
        self.catchment_chk = None
        self.color_btn = None  # bouton Couleurs

        # flux labels
        self._flux_labels = {'01': 'Eaux Pluviales', '02': 'Eaux Usées', '03': 'Unitaire'}

        # champs éventuels côté tracer
        self.field_alias = {
            'cat':  ['contcanass', 'categorie', 'cat_reseau'],
            'func': ['fonccanass', 'fonction', 'function'],
            'type': ['typreseau', 'type_reseau'],
            'len':  ['l_longcana_reelle', 'longueur', 'length']
        }

        self._last_trace_nodes: Set[str] = set()

    # ---------------------------------------------------------
    # Integration QGIS
    # ---------------------------------------------------------
    def init_gui(self):
        icon = QIcon(os.path.join(ICONS_DIR, 'icon.png'))
        act = QAction(icon, "CheminerIndus", self.iface.mainWindow())
        act.triggered.connect(self._show_with_splash)
        self.iface.addToolBarIcon(act)
        self.iface.addPluginToMenu("&CheminerIndus", act)
        self._action = act

    def unload(self):
        if self._action:
            try:
                self.iface.removeToolBarIcon(self._action)
                self.iface.removePluginMenu("&CheminerIndus", self._action)
            except Exception:
                pass
        if self.dock:
            self.iface.removeDockWidget(self.dock)
        if self.industrial_dock:
            self.iface.removeDockWidget(self.industrial_dock)
        if self.diag_dock:
            self.iface.removeDockWidget(self.diag_dock)

    # ---------------------------------------------------------
    # UI + Splash screen GIF
    # ---------------------------------------------------------
    def _show_with_splash(self):
        """
        Affiche un écran GIF centré pendant quelques secondes, puis ouvre le dock.
        """
        parent = self.iface.mainWindow()

        # Création d'un petit dialog sans bordure
        from qgis.PyQt.QtWidgets import QDialog
        splash = QDialog(parent)
        splash.setModal(False)
        splash.setWindowFlag(Qt.FramelessWindowHint)
        splash.setAttribute(Qt.WA_TranslucentBackground, True)

        v = QVBoxLayout(splash)
        v.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel()
        lbl.setAlignment(Qt.AlignCenter)
        v.addWidget(lbl)

        gif_path = os.path.join(ICONS_DIR, "splash.gif")
        movie = QMovie(gif_path)
        movie.setScaledSize(QSize(300, 200))
        lbl.setMovie(movie)
        movie.start()

        # Centrage sur la fenêtre QGIS
        parent_geo = parent.geometry()
        splash.resize(300, 200)
        x = parent_geo.center().x() - splash.width() // 2
        y = parent_geo.center().y() - splash.height() // 2
        splash.move(x, y)
        splash.show()

        def finish():
            movie.stop()
            splash.close()
            self._show()

        # 3 secondes d'affichage
        QTimer.singleShot(3000, finish)

    def _show(self):
        if self.dock:
            self.iface.removeDockWidget(self.dock)

        self.dock = QDockWidget("CHEMINEMENT RESEAUX", self.iface.mainWindow())
        self.dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        main = QWidget()
        lay  = QVBoxLayout(main)

        # -------------------------------------------------
        # En-tête avec logo à hauteur FIXE
        # -------------------------------------------------
        head = QHBoxLayout()

        logo_container = QWidget()
        logo_container.setFixedHeight(70)
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)

        logo = QLabel()
        pix = QPixmap(os.path.join(ICONS_DIR, 'icon.png'))
        scaled = pix.scaledToHeight(70, Qt.SmoothTransformation)
        logo.setPixmap(scaled)
        logo.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        logo_layout.addWidget(logo, alignment=Qt.AlignRight | Qt.AlignVCenter)

        head.addStretch()
        head.addWidget(logo_container)
        lay.addLayout(head)

        # -------------------------------------------------
        # Onglets
        # -------------------------------------------------
        tabs = QTabWidget()
        lay.addWidget(tabs)

        # ordre : CHEMINEMENT, VISITE-INDUS, ACTIONS, COUCHES, IA
        tabs.addTab(self._tab_trace(),       "CHEMINEMENT")
        tabs.addTab(self._tab_visit_indus(), "VISITE-INDUS")
        tabs.addTab(self._tab_actions(),     "ACTIONS")
        tabs.addTab(self._tab_layers(),      "COUCHES")
        tabs.addTab(self._tab_ai(),          "🤖 IA")

        self.dock.setWidget(main)
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dock)

        self._populate_layers()
        self._init_autosave()

    # ---------------------------------------------------------
    # Utilitaires génériques (sablier, autosave, inversion)
    # ---------------------------------------------------------
    def _run_with_wait_cursor(self, func, *args, **kwargs):
        """
        Exécute une fonction en affichant un sablier et un message
        'Traitement en cours...' dans la barre de messages de QGIS.
        """
        msg_bar = None
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                msg_bar = self.iface.messageBar().createMessage(
                    "CheminerIndus", "Traitement en cours..."
                )
                self.iface.messageBar().pushWidget(msg_bar, Qgis.Info)
            except Exception:
                msg_bar = None
            return func(*args, **kwargs)
        finally:
            try:
                if msg_bar:
                    self.iface.messageBar().clearWidgets()
            except Exception:
                pass
            try:
                QApplication.restoreOverrideCursor()
            except Exception:
                pass

    def _confirm_reset(self):
        """
        Demande à l'utilisateur de confirmer la réinitialisation avant d'appeler _reset().
        """
        msg = (
            "Voulez-vous vraiment réinitialiser le plugin ?\n\n"
            "- Toutes les sélections seront perdues\n"
            "- Les visites de nœuds seront effacées\n"
            "- L'industriel désigné et la note seront supprimés\n"
            "- L'astreinte rattachée sera oubliée\n"
        )
        resp = QMessageBox.question(
            self.iface.mainWindow(),
            "Confirmation de réinitialisation",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if resp == QMessageBox.Yes:
            self._reset()

    def _map_inversion_label(self, code: str) -> str:
        """
        Retourne un libellé lisible pour le code d'inversion.
        Si code vide/inconnu -> 'Inversion à vérifier'.
        """
        mapping = {
            '1': "Inversion EP dans EU avérée",
            '2': "Inversion EU dans EP avérée",
            '3': "Trop-plein EP dans EU",
            '4': "Trop-plein EU dans EP",
        }
        code = (code or "").strip()
        if not code:
            return "Inversion à vérifier"
        return mapping.get(code, "Inversion à vérifier")

    # Autosave
    def _init_autosave(self):
        """
        Propose un fichier projet pour la sauvegarde automatique, puis recharge
        l'état s'il existe déjà dans ce fichier.
        """
        try:
            self.auto_mgr.ensure_project(self.iface.mainWindow())
            st = self.auto_mgr.load()
            if st:
                self._apply_session_state(st, show_message=False)
        except Exception:
            # Ne pas casser l'ouverture du plugin
            pass

    def _autosave(self):
        """
        Sauvegarde l'état courant si un fichier projet a été défini.
        """
        try:
            if self.auto_mgr and self.auto_mgr.path:
                self.auto_mgr.save(self._session_state())
        except Exception:
            pass

    # Wrappers avec sablier
    def _do_trace_with_wait(self):
        res = self._run_with_wait_cursor(self._do_trace)
        self._autosave()
        return res

    def _open_diagnostic_with_wait(self):
        res = self._run_with_wait_cursor(self._open_diagnostic)
        self._autosave()
        return res

    def _make_report_with_wait(self):
        res = self._run_with_wait_cursor(self._make_report)
        # rapport ne modifie pas l'état, autosave non indispensable
        return res

    # ---------------------------------------------------------
    # Onglet COUCHES
    # ---------------------------------------------------------
    def _tab_layers(self) -> QWidget:
        w = QWidget(); l = QVBoxLayout(w)

        self.canal_combo    = QComboBox()
        self.ouvr_combo     = QComboBox()
        self.fosse_combo    = QComboBox()
        self.indus_combo    = QComboBox()
        self.liaison_combo  = QComboBox()
        self.astreint_combo = QComboBox()

        l.addWidget(QLabel("Canalisations :"));          l.addWidget(self.canal_combo)
        l.addWidget(QLabel("Ouvrages :"));               l.addWidget(self.ouvr_combo)
        l.addWidget(QLabel("Cours d'eau / fossés :"));   l.addWidget(self.fosse_combo)
        l.addWidget(QLabel("Industriels :"));            l.addWidget(self.indus_combo)
        l.addWidget(QLabel("Liaisons Indus :"));         l.addWidget(self.liaison_combo)
        l.addWidget(QLabel("Astreinte-Exploit :"));      l.addWidget(self.astreint_combo)

        return w

    def _populate_layers(self):
        for c in (self.canal_combo, self.ouvr_combo, self.fosse_combo,
                  self.indus_combo, self.liaison_combo, self.astreint_combo):
            c.clear()

        # trouver/assurer LABEL_CI si présent
        self.label_layer = None
        for lyr in QgsProject.instance().mapLayers().values():
            name = lyr.name().lower()
            if "canal" in name:
                self.canal_combo.addItem(lyr.name(), lyr)
            if "ouvr" in name or "ouvrage" in name:
                self.ouvr_combo.addItem(lyr.name(), lyr)
            if "cours" in name or "fosse" in name:
                self.fosse_combo.addItem(lyr.name(), lyr)
            if "indus" in name or "industriel" in name:
                self.indus_combo.addItem(lyr.name(), lyr)
            if "liaison" in name:
                self.liaison_combo.addItem(lyr.name(), lyr)
            if "astreint" in name or "astreinte" in name:
                self.astreint_combo.addItem(lyr.name(), lyr)
            if lyr.name() == "LABEL_CI" and isinstance(lyr, QgsVectorLayer) and lyr.isValid():
                self.label_layer = lyr

        # Si LABEL_CI introuvable : créer une mémoire (sécurité)
        if not self.label_layer:
            vdef = "Point?crs=EPSG:2154&field=categorie:string&field=label:string"
            self.label_layer = QgsVectorLayer(vdef, "LABEL_CI", "memory")
            QgsProject.instance().addMapLayer(self.label_layer)

    # ---------------------------------------------------------
    # Onglet CHEMINEMENT
    # ---------------------------------------------------------
    def _tab_trace(self) -> QWidget:
        w = QWidget(); g = QGridLayout(w)

        self.id_input = QLineEdit()
        g.addWidget(QLabel("ID ouvrage départ :"), 0, 0)
        g.addWidget(self.id_input, 0, 1)

        # select on map
        btn_sel = QPushButton("Sélection carte"); btn_sel.setIcon(QIcon(os.path.join(ICONS_DIR,'select.png')))
        btn_sel.setCheckable(True); btn_sel.clicked.connect(self._toggle_select)
        g.addWidget(btn_sel, 1, 0, 1, 2)

        # search
        self.search_input = QLineEdit()
        btn_search = QPushButton("Rechercher"); btn_search.setIcon(QIcon(os.path.join(ICONS_DIR,'filtre.png')))
        btn_search.clicked.connect(self._search)
        hb = QHBoxLayout(); hb.addWidget(self.search_input); hb.addWidget(btn_search)
        g.addWidget(QLabel("Recherche :"), 2, 0); g.addLayout(hb, 2, 1)

        # mode + filtres
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["Amont vers Aval", "Aval vers Amont", "Cheminement pour Industriels"])
        g.addWidget(QLabel("Type :"), 3, 0); g.addWidget(self.direction_combo, 3, 1)

        self.cat_combo = QComboBox()
        for txt,val in [("",""),("Eaux Pluviales","01"),("Eaux Usées","02"),("Unitaire","03")]:
            self.cat_combo.addItem(txt,val)
        g.addWidget(QLabel("Catégorie :"), 4, 0); g.addWidget(self.cat_combo, 4, 1)

        self.func_combo = QComboBox()
        for txt,val in [("",""),("Transport","01"),("Collecte","02")]:
            self.func_combo.addItem(txt,val)
        g.addWidget(QLabel("Fonction :"), 5, 0); g.addWidget(self.func_combo, 5, 1)

        # buttons
        self.trace_btn = QPushButton("Cheminer"); self.trace_btn.setIcon(QIcon(os.path.join(ICONS_DIR,'trace.png')))
        self.trace_btn.clicked.connect(self._do_trace_with_wait)

        self.flux_btn = QPushButton("Flux"); self.flux_btn.setIcon(QIcon(os.path.join(ICONS_DIR,'flux.png')))
        self.flux_btn.setCheckable(True); self.flux_btn.clicked.connect(self._toggle_flux)

        # ---- Nouveau bouton Couleurs ----
        self.color_btn = QPushButton("Couleurs")
        palette_icon = os.path.join(ICONS_DIR, 'palette.png')
        self.color_btn.setIcon(QIcon(palette_icon) if os.path.exists(palette_icon) else QIcon())
        self.color_btn.setToolTip("Régler les couleurs des flux (EP, EU, Défaut)")
        self.color_btn.clicked.connect(self._open_flux_colors)

        hb2 = QHBoxLayout(); hb2.addWidget(self.trace_btn); hb2.addWidget(self.flux_btn); hb2.addWidget(self.color_btn)
        g.addLayout(hb2, 6, 0, 1, 2)

        return w

    # ---------------------------------------------------------
    # Onglet VISITE-INDUS
    # ---------------------------------------------------------
    def _tab_visit_indus(self) -> QWidget:
        w = QWidget(); l = QVBoxLayout(w)

        # bloc visites
        box_v = QGroupBox("Visites de nœuds"); lv = QVBoxLayout(box_v)
        hb = QHBoxLayout()
        self.visit_input = QLineEdit(); hb.addWidget(self.visit_input)
        btn_pick = QPushButton(); btn_pick.setIcon(QIcon(os.path.join(ICONS_DIR,'select.png')))
        btn_pick.setCheckable(True); btn_pick.setToolTip("Sélectionner un nœud sur la carte")
        btn_pick.clicked.connect(self._toggle_visit_select); hb.addWidget(btn_pick)
        lv.addLayout(hb)

        btn_visit = QPushButton("Visiter (Pollué O/N)"); btn_visit.setIcon(QIcon(os.path.join(ICONS_DIR,'pollueur.png')))
        btn_visit.clicked.connect(self._visit)
        lv.addWidget(btn_visit)
        l.addWidget(box_v)

        # bloc indus
        box_i = QGroupBox("Industriels"); li = QVBoxLayout(box_i)
        self.btn_show_indus = QPushButton("Afficher Indus connectés"); self.btn_show_indus.setIcon(QIcon(os.path.join(ICONS_DIR,'table.png')))
        self.btn_show_indus.clicked.connect(self._open_or_update_industrial_dock)
        li.addWidget(self.btn_show_indus)

        # note pollution (grande zone)
        self.note_text = QTextEdit(); self.note_text.setPlaceholderText("Note de pollution (si désignation)…")
        li.addWidget(self.note_text)

        # rattacher astreinte
        btn_att = QPushButton("Rattacher Astreinte"); btn_att.setIcon(QIcon(os.path.join(ICONS_DIR,'attach.png')))
        btn_att.clicked.connect(self._attach_astreint); li.addWidget(btn_att)

        l.addWidget(box_i)
        return w

    # ---------------------------------------------------------
    # Onglet ACTIONS
    # ---------------------------------------------------------
    def _tab_actions(self) -> QWidget:
        w = QWidget(); l = QVBoxLayout(w)

        self.catchment_chk = QCheckBox("Bassin de collecte")
        self.catchment_chk.setToolTip("Affiche/masque un contour concave autour du réseau sélectionné")
        self.catchment_chk.stateChanged.connect(self._toggle_catchment)
        l.addWidget(self.catchment_chk)

        btn_diag = QPushButton("Diagnostics"); btn_diag.setIcon(QIcon(os.path.join(ICONS_DIR,'table.png')))
        btn_diag.clicked.connect(self._open_diagnostic_with_wait); l.addWidget(btn_diag)

        btn_pdf = QPushButton("Générer PDF"); btn_pdf.setIcon(QIcon(os.path.join(ICONS_DIR,'report.png')))
        btn_pdf.clicked.connect(self._make_report_with_wait); l.addWidget(btn_pdf)

        btn_ph = QPushButton("Ajouter Photos (+ commentaires)"); btn_ph.setIcon(QIcon(os.path.join(ICONS_DIR,'save.png')))
        btn_ph.clicked.connect(lambda: self.ph_mgr.add(self.dock)); l.addWidget(btn_ph)

        # masquer étiquettes
        btn_mask = QPushButton("Masquer/Demasquer étiquettes")
        btn_mask.setIcon(QIcon(os.path.join(ICONS_DIR,'filtre.png')))
        btn_mask.setCheckable(True); btn_mask.clicked.connect(self._toggle_mask_labels)
        l.addWidget(btn_mask)

        # save/load session
        hb = QHBoxLayout()
        btn_save = QPushButton("Sauvegarder session"); btn_save.clicked.connect(self._save_session)
        btn_load = QPushButton("Charger session");     btn_load.clicked.connect(self._load_session)
        hb.addWidget(btn_save); hb.addWidget(btn_load); l.addLayout(hb)

        # créer tables minimales
        btn_schema = QPushButton("Créer tables minimales"); btn_schema.clicked.connect(self._create_minimal_tables)
        l.addWidget(btn_schema)

        # reset (avec confirmation)
        btn_rst = QPushButton("Réinitialiser"); btn_rst.setIcon(QIcon(os.path.join(ICONS_DIR,'reset.png')))
        btn_rst.clicked.connect(self._confirm_reset); l.addWidget(btn_rst)
        return w

    # ---------------------------------------------------------
    # Onglet IA
    # ---------------------------------------------------------
    def _tab_ai(self) -> QWidget:
        """Crée l'onglet IA pour prédiction et visualisation 3D"""
        return AITab(self)

    # ---------------------------------------------------------
    # Sélection / Recherche
    # ---------------------------------------------------------
    def _toggle_select(self, checked: bool):
        if checked:
            self.ouvr_layer = self.ouvr_combo.currentData()
            if not self.ouvr_layer or not self.ouvr_layer.isValid():
                QMessageBox.warning(self.iface.mainWindow(),"CheminerIndus","Couche OUVRAGE invalide.")
                return
            self.tool_select = MapSelectionTool(self.canvas, self.ouvr_layer, id_field='idouvrage')
            self.tool_select.featureIdentified.connect(self._on_select)
            self.canvas.setMapTool(self.tool_select)
        else:
            self.canvas.unsetMapTool(self.canvas.mapTool())

    def _on_select(self, oid: str):
        self.id_input.setText(oid)
        self.canvas.unsetMapTool(self.canvas.mapTool())

    def _toggle_visit_select(self, checked: bool):
        if checked:
            self.ouvr_layer = self.ouvr_combo.currentData()
            if not self.ouvr_layer or not self.ouvr_layer.isValid():
                QMessageBox.warning(self.iface.mainWindow(),"CheminerIndus","Couche OUVRAGE invalide.")
                return
            self.tool_visit = MapSelectionTool(self.canvas, self.ouvr_layer, id_field='idouvrage')
            self.tool_visit.featureIdentified.connect(self._on_visit_select)
            self.canvas.setMapTool(self.tool_visit)
        else:
            self.canvas.unsetMapTool(self.canvas.mapTool())

    def _on_visit_select(self, oid: str):
        self.visit_input.setText(oid)
        self.canvas.unsetMapTool(self.canvas.mapTool())

    def _search(self):
        oid = (self.search_input.text() or "").strip()
        if not oid:
            QMessageBox.information(self.iface.mainWindow(),"Recherche","Saisir un ID.")
            return
        self.ouvr_layer = self.ouvr_combo.currentData()
        if not self.ouvr_layer or not self.ouvr_layer.isValid():
            QMessageBox.warning(self.iface.mainWindow(),"CheminerIndus","Couche OUVRAGE invalide.")
            return
        expr = QgsExpression("\"idouvrage\" = '{}'".format(oid.replace("'", "''")))
        req  = QgsFeatureRequest(expr)
        for f in self.ouvr_layer.getFeatures(req):
            g = f.geometry()
            if g:
                self.canvas.setExtent(g.boundingBox()); self.canvas.refresh()
                QMessageBox.information(self.iface.mainWindow(),"Recherche","Ouvrage {} trouvé.".format(oid))
                return
        QMessageBox.information(self.iface.mainWindow(),"Recherche","Ouvrage {} non trouvé.".format(oid))

    # ---------------------------------------------------------
    # Traçage
    # ---------------------------------------------------------
    def _do_trace(self):
        start_id = (self.id_input.text() or "").strip()
        if not start_id:
            QMessageBox.warning(self.iface.mainWindow(),"CheminerIndus","Veuillez saisir un ID départ.")
            return

        # couches
        self.canal_layer   = self.canal_combo.currentData()
        self.fosse_layer   = self.fosse_combo.currentData()
        self.indus_layer   = self.indus_combo.currentData()
        self.liaison_layer = self.liaison_combo.currentData()
        self.ouvr_layer    = self.ouvr_combo.currentData()

        if not self.canal_layer or not self.ouvr_layer:
            QMessageBox.warning(self.iface.mainWindow(),"CheminerIndus","Sélectionnez au minimum CANALISATION et OUVRAGE.")
            return

        mode = self.direction_combo.currentText()
        filters = {'category': self.cat_combo.currentData() or '',
                   'function': self.func_combo.currentData() or ''}

        if mode == "Cheminement pour Industriels":
            self._trace_for_industrials(start_id, filters)
            self._autosave()
            return

        # Tracer réseau
        self.tracer = NetworkTracer(
            canal_layer=self.canal_layer,
            fosse_layer=self.fosse_layer,
            field_alias=self.field_alias,
            filters=filters
        )
        downstream = (mode == "Amont vers Aval")
        canal_ids, fosse_ids = self.tracer.trace(start_id, downstream=downstream)

        # sélection
        self.canal_layer.removeSelection()
        if canal_ids: self.canal_layer.selectByIds(canal_ids)
        if self.fosse_layer and self.fosse_layer.isValid():
            self.fosse_layer.removeSelection()
            if fosse_ids: self.fosse_layer.selectByIds(fosse_ids)

        # nœuds atteints (pour liaisons)
        nodes = self._collect_nodes_from_ids(canal_ids, fosse_ids, downstream)
        self._last_trace_nodes = nodes

        # liaisons atteintes
        self._select_liaisons_from_nodes(sorted(nodes))

        # flux résumé
        dist = round(self.tracer.total_length, 2)
        codes = [c for c in self.tracer.flux_types if c]
        labels = sorted({ self._flux_labels.get(c, c) for c in codes }) or ["Aucun"]
        QMessageBox.information(self.iface.mainWindow(),"Cheminement",
            "Longueur : {} m\nFlux : {}".format(dist, " / ".join(labels)))

        # bassin concave si demandé (Aval→Amont uniquement)
        if (not downstream) and self.catchment_chk and self.catchment_chk.isChecked():
            self._generate_catchment()

        self._autosave()

    def _trace_for_industrials(self, start_id: str, filters: Dict[str,str]):
        """
        Cheminement spécifique pour les industriels :
        - trace en aval→amont,
        - sélectionne les liaisons,
        - sélectionne les industriels dans la couche INDUITS,
        - remplit le dock industriels.
        """
        self.tracer = NetworkTracer(
            canal_layer=self.canal_layer,
            fosse_layer=self.fosse_layer,
            field_alias=self.field_alias,
            filters=filters
        )
        # amont
        canal_ids, fosse_ids = self.tracer.trace(start_id, downstream=False)

        # sélection réseau
        self.canal_layer.removeSelection()
        if canal_ids:
            self.canal_layer.selectByIds(canal_ids)
        if self.fosse_layer and self.fosse_layer.isValid():
            self.fosse_layer.removeSelection()
            if fosse_ids:
                self.fosse_layer.selectByIds(fosse_ids)

        # nœuds atteints
        nodes = self._collect_nodes_from_ids(canal_ids, fosse_ids, downstream=False)
        self._last_trace_nodes = nodes

        # liaisons + indus
        if not self.indus_svc:
            self.indus_svc = IndustrialsService(self.indus_layer, self.liaison_layer)

        self.indus_svc.select_liaisons_from_nodes(nodes)  # sélectionne liaisons dans la couche
        ind_ids = self.indus_svc.select_industrials_from_selected_liaisons()  # renvoie les IDs texte

        # Sélection explicite des industriels sur la carte
        if self.indus_layer and self.indus_layer.isValid():
            self.indus_layer.removeSelection()
            if ind_ids:
                esc = lambda s: (s or "").replace("'", "''")
                values = ",".join("'{}'".format(esc(i)) for i in ind_ids if i)
                expr = QgsExpression("trim(\"id\") IN ({})".format(values))
                req = QgsFeatureRequest(expr)
                fids = [f.id() for f in self.indus_layer.getFeatures(req)]
                if fids:
                    self.indus_layer.selectByIds(fids)

        details = self.indus_svc.fetch_many(ind_ids)
        self._last_indus_data = details
        self._open_or_update_industrial_dock(data=details)

        # résumé
        dist = round(self.tracer.total_length, 2)
        codes = [c for c in self.tracer.flux_types if c]
        labels = sorted({ self._flux_labels.get(c, c) for c in codes }) or ["Aucun"]
        QMessageBox.information(
            self.iface.mainWindow(),
            "Cheminement (Industriels)",
            "Industriels : {}\nLongueur : {} m\nFlux : {}".format(len(ind_ids), dist, " / ".join(labels))
        )

    # ---------------------------------------------------------
    # Collecte de nœuds depuis des IDs sélectionnés
    # ---------------------------------------------------------
    def _collect_nodes_from_ids(self, canal_ids: List[int], fosse_ids: List[int], downstream: bool) -> Set[str]:
        nodes: Set[str] = set()
        if self.canal_layer and canal_ids:
            req = QgsFeatureRequest().setFilterFids(canal_ids)
            for f in self.canal_layer.getFeatures(req):
                nid = f['idnterm'] if downstream else f['idnini']
                if nid and str(nid) != 'INCONNU': nodes.add(str(nid))
                nid2 = f['idnini'] if downstream else f['idnterm']
                if nid2 and str(nid2) != 'INCONNU': nodes.add(str(nid2))
        if self.fosse_layer and fosse_ids:
            req = QgsFeatureRequest().setFilterFids(fosse_ids)
            for f in self.fosse_layer.getFeatures(req):
                nid = f['idnterm'] if downstream else f['idnini']
                if nid and str(nid) != 'INCONNU': nodes.add(str(nid))
                nid2 = f['idnini'] if downstream else f['idnterm']
                if nid2 and str(nid2) != 'INCONNU': nodes.add(str(nid2))
        start = (self.id_input.text() or "").strip()
        if start: nodes.add(start)
        return nodes

    def _select_liaisons_from_nodes(self, nodes: List[str], clear: bool = True):
        if not self.liaison_layer:
            return
        if clear:
            self.liaison_layer.removeSelection()
        if not nodes:
            return
        esc = lambda s: (s or "").replace("'", "''")
        values = ",".join("'{}'".format(esc(n.strip())) for n in nodes)
        exprL = QgsExpression("trim(\"id_ouvrage\") IN ({})".format(values))
        reqL  = QgsFeatureRequest(exprL)
        ids   = [f.id() for f in self.liaison_layer.getFeatures(reqL)]
        if ids:
            self.liaison_layer.selectByIds(ids)

    # ---------------------------------------------------------
    # VISITES / BRANCHES
    # ---------------------------------------------------------
    def _visit(self):
        node_id = (self.visit_input.text() or "").strip()
        if not node_id:
            QMessageBox.information(self.iface.mainWindow(),"Info","Saisir un ID visite.")
            return

        # Initialiser l'optimiseur si nécessaire et construire les caches
        if not self._node_ops:
            self._node_ops = OptimizedNodeOps(
                self.canal_layer, self.fosse_layer, 
                self.liaison_layer, self.indus_layer
            )
        else:
            # Mettre à jour les couches au cas où elles auraient changé
            self._node_ops.canal_layer = self.canal_layer
            self._node_ops.fosse_layer = self.fosse_layer
            self._node_ops.liaison_layer = self.liaison_layer
            self._node_ops.indus_layer = self.indus_layer
            # Invalider les caches pour refléter les changements
            self._node_ops.invalidate_caches()

        # 1) Confirmer la pollution au nœud
        resp = QMessageBox.question(
            self.iface.mainWindow(), "Pollué ?",
            "Pollution détectée sur ce nœud ?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.No
        )
        if resp == QMessageBox.Cancel:
            return
        polluted = (resp == QMessageBox.Yes)
        self.visited.append({'id': node_id, 'pollution': polluted})

        # 2) Branches AMONT du nœud (canal, fosse) + liaisons au nœud
        branches: List[Tuple[str,int,Optional[str],Optional[str]]] = []
        if self.canal_layer:
            expr_c = QgsExpression("trim(\"idnterm\") = '{}' AND trim(\"idnini\") != 'INCONNU'".format(node_id.replace("'","''")))
            for feat in self.canal_layer.getFeatures(QgsFeatureRequest(expr_c)):
                branches.append(("canal", feat.id(), feat['idnini'], None))
        if self.fosse_layer:
            expr_f = QgsExpression("trim(\"idnterm\") = '{}' AND trim(\"idnini\") != 'INCONNU'".format(node_id.replace("'","''")))
            for feat in self.fosse_layer.getFeatures(QgsFeatureRequest(expr_f)):
                branches.append(("fosse", feat.id(), feat['idnini'], None))
        if self.liaison_layer:
            expr_l = QgsExpression("trim(\"id_ouvrage\") = '{}'".format(node_id.replace("'","''")))
            for lf in self.liaison_layer.getFeatures(QgsFeatureRequest(expr_l)):
                branches.append(("liaison", lf.id(), None, lf['id_industriel']))

        # 3) Si aucune branche amont, on gère tout de même l'aval quand pollution = OUI
        if not branches and not polluted:
            QMessageBox.information(self.iface.mainWindow(),"Branches","Aucune branche amont.")
        # 4) Choix des branches AMONT à conserver/désélectionner selon pollution
        chosen_keep: Set[int] = set()
        if branches:
            if polluted:
                # On propose de COCHER les branches AMONT à CONSERVER (polluées)
                if len(branches) == 1:
                    chosen_keep = {branches[0][1]}
                else:
                    dlg = QDialog(self.iface.mainWindow()); dlg.setWindowTitle("Branches amont à CONSERVER (Noeud: {})".format(node_id))
                    v = QVBoxLayout(dlg); checks = []
                    for typ,fid,amont,indus in branches:
                        label = "Conserver {} id={}".format(typ.upper(), fid)
                        if amont: label += " (amont={})".format(amont)
                        if indus: label += " (indus={})".format(indus)
                        cb = QCheckBox(label); cb.setChecked(False)
                        v.addWidget(cb); checks.append((cb,typ,fid,amont,indus))
                    h = QHBoxLayout(); ok = QPushButton("OK"); cancel = QPushButton("Annuler")
                    ok.clicked.connect(dlg.accept); cancel.clicked.connect(dlg.reject)
                    h.addWidget(ok); h.addWidget(cancel); v.addLayout(h)
                    if dlg.exec_() == QDialog.Accepted:
                        chosen_keep = {fid for cb,_,fid,_,_ in checks if cb.isChecked()}
                    else:
                        return
                # Désélectionner toutes les branches AMONT non cochées (et tout leur amont récursif + indus)
                removed_indus_up = self._node_ops.bulk_deselect_unselected_branches_optimized(node_id, branches, chosen_keep)
            else:
                # Pollué = NON → tout l'amont doit être désélectionné automatiquement
                removed_indus_up = self._node_ops.bulk_deselect_unselected_branches_optimized(node_id, branches, chosen_ids=set())
        else:
            removed_indus_up = set()

        # 5) Si Pollué = OUI → nettoyage strict entre départ et ce nœud sur la sélection
        removed_indus_down = set()
        keep_cids: Set[int] = set()
        keep_fids: Set[int] = set()
        keep_nodes: Set[str] = set()

        if polluted:
            # 5.a Désélectionner l'AVAL de ce nœud (sur la sélection courante) - VERSION OPTIMISÉE
            sel_c, sel_f = self._selected_id_sets()
            cids_ds, fids_ds, nodes_ds = self._node_ops.walk_downstream_on_selected_optimized(node_id, sel_c, sel_f)
            if self.canal_layer and cids_ds:
                self.canal_layer.deselect(list(cids_ds))
            if self.fosse_layer and fids_ds:
                self.fosse_layer.deselect(list(fids_ds))
            removed_indus_down = self._node_ops.deselect_liaisons_and_indus_from_nodes_optimized(nodes_ds)

            # 5.b Construire l'ensemble KEEP = branches cochées + tout leur amont (sur la sélection)
            for typ, fid, amont, _ in branches:
                if fid not in chosen_keep:
                    continue
                if typ == "canal":
                    keep_cids.add(fid)
                elif typ == "fosse":
                    keep_fids.add(fid)
                # Remonter sur la sélection à partir de l'amont de la branche cochée - VERSION OPTIMISÉE
                if amont:
                    sel_c, sel_f = self._selected_id_sets()
                    kc, kf, kn = self._node_ops.walk_upstream_on_selected_optimized(amont, sel_c, sel_f)
                    keep_cids.update(kc); keep_fids.update(kf); keep_nodes.update(kn)
            # Inclure le nœud visité dans l'ensemble KEEP de nœuds
            keep_nodes.add(node_id.strip())

            # 5.c Purge finale : tout ce qui reste sélectionné mais pas dans KEEP → on enlève
            sel_c, sel_f = self._selected_id_sets()
            rem_c = list(sel_c - keep_cids)
            rem_f = list(sel_f - keep_fids)
            if self.canal_layer and rem_c:
                self.canal_layer.deselect(rem_c)
            if self.fosse_layer and rem_f:
                self.fosse_layer.deselect(rem_f)

            # Exclure les liaisons/indus des nœuds associés aux tronçons supprimés
            nodes_removed: Set[str] = set()
            # récupérer nœuds depuis les tronçons retirés
            def _nodes_from_ids(layer, ids):
                out = set()
                if not layer or not ids:
                    return out
                req = QgsFeatureRequest().setFilterFids(ids)
                for f in layer.getFeatures(req):
                    try:
                        ni = (f['idnini'] or "").strip()
                        nt = (f['idnterm'] or "").strip()
                        if ni and ni.upper() != "INCONNU": out.add(str(ni))
                        if nt and nt.upper() != "INCONNU": out.add(str(nt))
                    except Exception:
                        pass
                return out
            nodes_removed.update(_nodes_from_ids(self.canal_layer, rem_c))
            nodes_removed.update(_nodes_from_ids(self.fosse_layer, rem_f))
            # Attention à ne pas supprimer ce qui est dans KEEP
            nodes_removed.difference_update(keep_nodes)
            if nodes_removed:
                removed_indus_down.update(self._node_ops.deselect_liaisons_and_indus_from_nodes_optimized(nodes_removed))

        # 6) Exclure dans le tableau des indus
        removed_indus_all = set()
        removed_indus_all.update(removed_indus_up or set())
        removed_indus_all.update(removed_indus_down or set())
        if self.industrial_dock and removed_indus_all:
            try:
                self.industrial_dock.exclude_ids(sorted(removed_indus_all))
            except Exception:
                pass

        self.canvas.refresh()
        self._autosave()

    # --- Parcours amont existant ---
    def _iter_incoming_edges_mixed(self, node: str):
        out = []
        if self.canal_layer:
            expr = QgsExpression("trim(\"idnterm\") = '{}' AND trim(\"idnini\") != 'INCONNU'".format(node.replace("'","''")))
            for f in self.canal_layer.getFeatures(QgsFeatureRequest(expr)):
                out.append(("canal", self.canal_layer, f))
        if self.fosse_layer:
            expr = QgsExpression("trim(\"idnterm\") = '{}' AND trim(\"idnini\") != 'INCONNU'".format(node.replace("'","''")))
            for f in self.fosse_layer.getFeatures(QgsFeatureRequest(expr)):
                out.append(("fosse", self.fosse_layer, f))
        return out

    def _walk_upstream_mixed(self, start_node: Optional[str]):
        if not start_node:
            return set(), set(), set()
        seen_nodes: Set[str] = set()
        cids: Set[int] = set()
        fids: Set[int] = set()
        stack = [str(start_node)]
        while stack:
            cur = stack.pop()
            if cur in seen_nodes:
                continue
            seen_nodes.add(cur)
            for typ, layer, feat in self._iter_incoming_edges_mixed(cur):
                fid = feat.id()
                if typ == "canal":
                    if fid in cids: continue
                    cids.add(fid)
                else:
                    if fid in fids: continue
                    fids.add(fid)
                nxt = (feat['idnini'] or "").strip()
                if nxt and nxt.upper() != "INCONNU":
                    stack.append(str(nxt))
        return cids, fids, seen_nodes

    # --- Sortant ---
    def _iter_outgoing_edges_mixed(self, node: str):
        out = []
        node_cmp = (node or "").strip().replace("'", "''")
        if self.canal_layer:
            expr = QgsExpression(f"trim(\"idnini\") = '{node_cmp}'")
            for f in self.canal_layer.getFeatures(QgsFeatureRequest(expr)):
                out.append(("canal", self.canal_layer, f))
        if self.fosse_layer:
            expr = QgsExpression(f"trim(\"idnini\") = '{node_cmp}'")
            for f in self.fosse_layer.getFeatures(QgsFeatureRequest(expr)):
                out.append(("fosse", self.fosse_layer, f))
        return out

    def _walk_downstream_mixed(self, start_node: Optional[str]):
        """Ancienne marche aval globale (non utilisée pour le nettoyage 'entre départ et nœud')."""
        if not start_node:
            return set(), set(), set()
        seen_nodes: Set[str] = set()
        cids: Set[int] = set()
        fids: Set[int] = set()
        stack = [str(start_node).strip()]
        while stack:
            cur = stack.pop()
            if cur in seen_nodes:
                continue
            seen_nodes.add(cur)
            for typ, layer, feat in self._iter_outgoing_edges_mixed(cur):
                fid = feat.id()
                if typ == "canal":
                    if fid in cids: 
                        continue
                    cids.add(fid)
                else:
                    if fid in fids: 
                        continue
                    fids.add(fid)
                nxt = ""
                try:
                    nxt = (feat['idnterm'] or "").strip()
                except Exception:
                    nxt = ""
                if nxt and nxt.upper() != "INCONNU":
                    stack.append(str(nxt))
        return cids, fids, seen_nodes

    # --- NOUVEAU : marches limitées à la SÉLECTION (chemin courant) ---
    def _selected_id_sets(self) -> Tuple[Set[int], Set[int]]:
        """Renvoie les ID sélectionnés pour canal et fosse (filtre pour marche 'sur sélection')."""
        sel_c = set(self.canal_layer.selectedFeatureIds()) if self.canal_layer else set()
        sel_f = set(self.fosse_layer.selectedFeatureIds()) if self.fosse_layer else set()
        return sel_c, sel_f

    def _walk_downstream_on_selected(self, start_node: Optional[str]):
        """Aval sur la sélection courante (nettoyage 'entre départ et nœud visité')."""
        if not start_node:
            return set(), set(), set()
        sel_c, sel_f = self._selected_id_sets()
        seen_nodes: Set[str] = set()
        cids: Set[int] = set()
        fids: Set[int] = set()
        stack = [str(start_node).strip()]
        while stack:
            cur = stack.pop()
            if cur in seen_nodes:
                continue
            seen_nodes.add(cur)
            for typ, layer, feat in self._iter_outgoing_edges_mixed(cur):
                fid = feat.id()
                if typ == "canal":
                    if fid not in sel_c or fid in cids: continue
                    cids.add(fid)
                else:
                    if fid not in sel_f or fid in fids: continue
                    fids.add(fid)
                nxt = (feat['idnterm'] or "").strip()
                if nxt and nxt.upper() != "INCONNU":
                    stack.append(str(nxt))
        return cids, fids, seen_nodes

    def _walk_upstream_on_selected(self, start_node: Optional[str]):
        """Amont sur la sélection courante (pour construire l'ensemble KEEP)."""
        if not start_node:
            return set(), set(), set()
        sel_c, sel_f = self._selected_id_sets()
        seen_nodes: Set[str] = set()
        cids: Set[int] = set()
        fids: Set[int] = set()
        stack = [str(start_node).strip()]
        while stack:
            cur = stack.pop()
            if cur in seen_nodes:
                continue
            seen_nodes.add(cur)
            for typ, layer, feat in self._iter_incoming_edges_mixed(cur):
                fid = feat.id()
                if typ == "canal":
                    if fid not in sel_c or fid in cids: continue
                    cids.add(fid)
                else:
                    if fid not in sel_f or fid in fids: continue
                    fids.add(fid)
                nxt = (feat['idnini'] or "").strip()
                if nxt and nxt.upper() != "INCONNU":
                    stack.append(str(nxt))
        return cids, fids, seen_nodes

    def _deselect_liaisons_and_indus_from_nodes(self, nodes: Set[str]) -> Set[str]:
        """Désélectionne liaisons (id_ouvrage ∈ nodes) et renvoie les IDs d'indus à exclure, puis les désélectionne."""
        removed_indus: Set[str] = set()
        if not nodes or not self.liaison_layer:
            return removed_indus
        esc = lambda s: (s or "").replace("'","''")
        values = ",".join("'{}'".format(esc((n or "").strip())) for n in nodes if (n or "").strip())
        if not values:
            return removed_indus
        exprL = QgsExpression("trim(\"id_ouvrage\") IN ({})".format(values))
        reqL  = QgsFeatureRequest(exprL)
        lids = [f.id() for f in self.liaison_layer.getFeatures(reqL)]
        if lids:
            # collecter indus liés
            for lid in lids:
                try:
                    lf = self.liaison_layer.getFeature(lid)
                    iid = lf['id_industriel']
                    if iid and str(iid) != 'INCONNU':
                        removed_indus.add(str(iid))
                except Exception:
                    pass
            self.liaison_layer.deselect(lids)

        if self.indus_layer and removed_indus:
            exprI = QgsExpression("trim(\"id\") IN ({})".format(",".join("'{}'".format(i.replace("'","''")) for i in removed_indus)))
            reqI  = QgsFeatureRequest(exprI)
            rem_ids = [f.id() for f in self.indus_layer.getFeatures(reqI)]
            if rem_ids:
                self.indus_layer.deselect(rem_ids)
        return removed_indus

    def _bulk_deselect_unselected_branches(self, start_node: str,
                                           branches: List[Tuple[str,int,Optional[str],Optional[str]]],
                                           chosen_ids: Set[int]) -> Set[str]:
        """
        Désélectionne tout l'amont pour les branches NON cochées.
        Retourne l'ensemble des IDs industriels exclus.
        """
        removed_cids: Set[int] = set()
        removed_fids: Set[int] = set()
        removed_lids: Set[int] = set()
        removed_nodes: Set[str] = set()
        removed_indus: Set[str] = set()

        for typ, fid, amont, indus in branches:
            if fid in chosen_ids:
                continue
            if typ == "canal":
                removed_cids.add(fid)
                cids, fids, nodes = self._walk_upstream_mixed(amont)
                removed_cids.update(cids); removed_fids.update(fids); removed_nodes.update(nodes)
            elif typ == "fosse":
                removed_fids.add(fid)
                cids, fids, nodes = self._walk_upstream_mixed(amont)
                removed_cids.update(cids); removed_fids.update(fids); removed_nodes.update(nodes)
            else:
                removed_lids.add(fid)
                if indus:
                    removed_indus.add(str(indus))

        if self.canal_layer and removed_cids:
            self.canal_layer.deselect(list(removed_cids))
        if self.fosse_layer and removed_fids:
            self.fosse_layer.deselect(list(removed_fids))

        # liaisons amont + indus (depuis tous les nœuds collectés)
        if self.liaison_layer:
            ids_to_unselect = list(removed_lids)
            if removed_nodes:
                esc = lambda s: (s or "").replace("'","''")
                values = ",".join("'{}'".format(esc((n or "").strip())) for n in removed_nodes if (n or "").strip())
                if values:
                    exprL = QgsExpression("trim(\"id_ouvrage\") IN ({})".format(values))
                    reqL  = QgsFeatureRequest(exprL)
                    ids_to_unselect += [f.id() for f in self.liaison_layer.getFeatures(reqL)]

            if ids_to_unselect:
                for lid in ids_to_unselect:
                    try:
                        lf = self.liaison_layer.getFeature(lid)
                        iid = lf['id_industriel']
                        if iid and str(iid) != 'INCONNU':
                            removed_indus.add(str(iid))
                    except Exception:
                        pass
                self.liaison_layer.deselect(ids_to_unselect)

        if self.indus_layer and removed_indus:
            exprI = QgsExpression("trim(\"id\") IN ({})".format(",".join("'{}'".format(i.replace("'","''")) for i in removed_indus)))
            reqI  = QgsFeatureRequest(exprI)
            rem_ids = [f.id() for f in self.indus_layer.getFeatures(reqI)]
            if rem_ids:
                self.indus_layer.deselect(rem_ids)

        self.canvas.refresh()
        return removed_indus

    # ---------------------------------------------------------
    # FLUX (animation)
    # ---------------------------------------------------------
    def _toggle_flux(self, checked: bool):
        if checked:
            layers = [x for x in (self.canal_combo.currentData(),
                                  self.fosse_combo.currentData(),
                                  self.liaison_combo.currentData()) if x]
            self.flow_anim.setLayers(layers)
            self.flow_anim.set_speed(1.6)
            self.flow_anim.start()
        else:
            self.flow_anim.stop()

    # ---- Panneau couleurs flux (presets + manuel) ----
    def _open_flux_colors(self):
        dlg = QDialog(self.iface.mainWindow())
        dlg.setWindowTitle("Couleurs des flux")
        v = QVBoxLayout(dlg)

        # Presets
        preset_box = QGroupBox("Préréglages")
        pv = QVBoxLayout(preset_box)
        preset_combo = QComboBox()
        preset_combo.addItem("Classique (EP bleu, EU brun, Défaut jaune)", ("#0066FF", "#7A3B00", "#F6E742"))
        preset_combo.addItem("Contrasté (EP cyan, EU magenta, Défaut rouge)", ("#00BCD4", "#AD1457", "#FF0000"))
        preset_combo.addItem("Daltonisme-friendly (EP bleu, EU orange, Défaut gris)", ("#377eb8", "#ff7f00", "#7f7f7f"))
        pv.addWidget(QLabel("Choisir un préréglage :"))
        pv.addWidget(preset_combo)
        v.addWidget(preset_box)

        # Choix manuels
        box = QGroupBox("Réglage manuel")
        grid = QGridLayout(box)

        cur_ep  = self.flow_anim.col_ep.name()  if isinstance(self.flow_anim.col_ep,  QColor) else "#0066FF"
        cur_eu  = self.flow_anim.col_eu.name()  if isinstance(self.flow_anim.col_eu,  QColor) else "#7A3B00"
        cur_def = self.flow_anim.col_def.name() if isinstance(self.flow_anim.col_def, QColor) else "#FF0000"

        btn_ep  = QPushButton("EP")
        btn_eu  = QPushButton("EU")
        btn_def = QPushButton("Défaut")

        def set_btn_color(btn, hex_color):
            btn.setStyleSheet("QPushButton { background-color: %s; color: white; }" % hex_color)

        set_btn_color(btn_ep,  cur_ep)
        set_btn_color(btn_eu,  cur_eu)
        set_btn_color(btn_def, cur_def)

        def pick(current_hex):
            col = QColorDialog.getColor(QColor(current_hex), dlg, "Choisir une couleur")
            return col.name() if col.isValid() else current_hex

        def on_pick_ep():
            set_btn_color(btn_ep, pick(btn_ep.palette().button().color().name()))
        def on_pick_eu():
            set_btn_color(btn_eu, pick(btn_eu.palette().button().color().name()))
        def on_pick_def():
            set_btn_color(btn_def, pick(btn_def.palette().button().color().name()))

        btn_ep.clicked.connect(on_pick_ep)
        btn_eu.clicked.connect(on_pick_eu)
        btn_def.clicked.connect(on_pick_def)

        grid.addWidget(QLabel("EP (01)"), 0, 0); grid.addWidget(btn_ep, 0, 1)
        grid.addWidget(QLabel("EU (02)"), 1, 0); grid.addWidget(btn_eu, 1, 1)
        grid.addWidget(QLabel("Défaut"),  2, 0); grid.addWidget(btn_def,2, 1)
        v.addWidget(box)

        # Actions
        hb = QHBoxLayout()
        ok = QPushButton("Appliquer")
        cancel = QPushButton("Annuler")
        hb.addWidget(ok); hb.addWidget(cancel)
        v.addLayout(hb)

        def apply_preset_to_buttons():
            ep, eu, df = preset_combo.currentData()
            set_btn_color(btn_ep,  ep)
            set_btn_color(btn_eu,  eu)
            set_btn_color(btn_def, df)

        preset_combo.currentIndexChanged.connect(apply_preset_to_buttons)
        cancel.clicked.connect(dlg.reject)

        def extract_hex(btn):
            st = btn.styleSheet()
            idx = st.find("background-color:")
            if idx >= 0:
                seg = st[idx:].split(";",1)[0]
                hex_ = seg.split(":")[1].strip()
                return hex_
            return "#000000"

        def on_apply():
            ep_hex  = extract_hex(btn_ep)
            eu_hex  = extract_hex(btn_eu)
            df_hex  = extract_hex(btn_def)
            try:
                self.flow_anim.set_colors(QColor(ep_hex), QColor(eu_hex), QColor(df_hex))
                if self.flux_btn and self.flux_btn.isChecked():
                    self.flow_anim.start()
            except Exception as e:
                QMessageBox.critical(self.iface.mainWindow(), "Couleurs flux", f"Erreur d'application des couleurs : {e}")
                return
            dlg.accept()

        ok.clicked.connect(on_apply)
        dlg.exec_()

    # ---------------------------------------------------------
    # CATCHMENT concave
    # ---------------------------------------------------------
    def _generate_catchment(self):
        poly = concave_envelope_from_selected(self.canvas, self.canal_layer, self.fosse_layer, base_px=60.0)
        self.highlight_mgr.show_polygon(poly)

    def _toggle_catchment(self, state: int):
        if state == Qt.Checked:
            self._generate_catchment()
        else:
            self.highlight_mgr.clear()
        self._autosave()

    # ---------------------------------------------------------
    # INDUSTRIELS (dock)
    # ---------------------------------------------------------
    def _refresh_industrial_dock_data(self):
        """
        Rappelé lorsque l'utilisateur clique sur 'Rafraîchir' dans le dock des industriels.
        On recalcule les industriels connectés aux derniers nœuds tracés.
        """
        if not self.indus_svc:
            self.indus_layer   = self.indus_combo.currentData()
            self.liaison_layer = self.liaison_combo.currentData()
            self.indus_svc = IndustrialsService(self.indus_layer, self.liaison_layer)

        if not self._last_trace_nodes:
            return

        ids = self.indus_svc.connected_ids_from_nodes(self._last_trace_nodes)
        details = self.indus_svc.fetch_many(ids)

        # Sélection graphique des indus à partir de ces IDs
        if self.indus_layer and self.indus_layer.isValid():
            self.indus_layer.removeSelection()
            if ids:
                esc = lambda s: (s or "").replace("'", "''")
                values = ",".join("'{}'".format(esc(i)) for i in ids if i)
                expr = QgsExpression("trim(\"id\") IN ({})".format(values))
                req = QgsFeatureRequest(expr)
                fids = [f.id() for f in self.indus_layer.getFeatures(req)]
                if fids:
                    self.indus_layer.selectByIds(fids)

        self._last_indus_data = details # <-- mémorisation
        if self.industrial_dock:
            self.industrial_dock.set_data(details)

    def _open_or_update_industrial_dock(self, data: Optional[Dict[str,Dict[str,str]]] = None):
        if not self.indus_svc:
            self.indus_layer   = self.indus_combo.currentData()
            self.liaison_layer = self.liaison_combo.currentData()
            self.indus_svc = IndustrialsService(self.indus_layer, self.liaison_layer)

        if data is None:
            if self._last_indus_data:
                data = self._last_indus_data
            else:
                ids = self.indus_svc.connected_ids_from_nodes(self._last_trace_nodes) if self._last_trace_nodes else []
                data = self.indus_svc.fetch_many(ids)
                self._last_indus_data = data
        
        if not self.industrial_dock:
            self.industrial_dock = IndustrialDock(self.iface.mainWindow())
            self.industrial_dock.on_zoom_request(self._zoom_to_industrial)
            self.industrial_dock.on_designate_request(self._designate_industrial)
            self.industrial_dock.on_refresh_request(self._refresh_industrial_dock_data)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.industrial_dock)

        self.industrial_dock.set_data(data)
        self.industrial_dock.show()
        self.industrial_dock.raise_()

    def _zoom_to_industrial(self, ind_id: str):
        if not self.indus_layer:
            return
        expr = QgsExpression("\"id\" = '{}'".format(str(ind_id).replace("'","''")))
        for f in self.indus_layer.getFeatures(QgsFeatureRequest(expr)):
            g = f.geometry()
            if g:
                self.canvas.setExtent(g.boundingBox()); self.canvas.refresh()
                break

    # -------- Cheminement depuis l'industriel désigné --------
    def _ask_indus_trace_network(self) -> Optional[str]:
        """
        Demande quel(s) réseau(x) cheminer depuis l'industriel désigné.
        Retourne 'EP', 'EU', 'BOTH' ou None si l'utilisateur annule.
        """
        dlg = QDialog(self.iface.mainWindow())
        dlg.setWindowTitle("Cheminement depuis l'industriel")

        v = QVBoxLayout(dlg)
        lab = QLabel(
            "Depuis l'industriel désigné, quel(s) réseau(x) cheminer en Amont → Aval ?"
        )
        lab.setWordWrap(True)
        v.addWidget(lab)

        rb_ep   = QRadioButton("Réseau EP (01) uniquement")
        rb_eu   = QRadioButton("Réseau EU (02) uniquement")
        rb_both = QRadioButton("Réseaux EP + EU")
        rb_both.setChecked(True)  # valeur par défaut

        v.addWidget(rb_ep)
        v.addWidget(rb_eu)
        v.addWidget(rb_both)

        hb = QHBoxLayout()
        btn_ok = QPushButton("Valider")
        btn_cancel = QPushButton("Annuler")
        hb.addWidget(btn_ok)
        hb.addWidget(btn_cancel)
        v.addLayout(hb)

        btn_ok.clicked.connect(dlg.accept)
        btn_cancel.clicked.connect(dlg.reject)

        if dlg.exec_() != QDialog.Accepted:
            return None

        if rb_ep.isChecked():
            return "EP"
        if rb_eu.isChecked():
            return "EU"
        return "BOTH"

    def _designate_industrial(self, ind_id: str):
        """
        Désigne un industriel pollueur + propose le cheminement Amont→Aval depuis
        les ouvrages reliés (via LIAISON_INDUS).

        Nouveauté :
        - Pour les choix "Réseau EP (01) uniquement" et "Réseau EU (02) uniquement",
          on ne filtre plus les canalisations par catégorie.
        - On NE GARDE comme ouvrages de départ que ceux dont le champ OUVRAGE.typreseau
          correspond au réseau choisi (01 = EP, 02 = EU).
        - Le choix "Réseaux EP + EU" garde tous les ouvrages reliés.
        """
        # 1) Mémoriser note + ID
        self.polluter_note = (self.note_text.toPlainText() or "").strip()
        self.polluter_id = ind_id

        # 2) S'assurer que les couches sont bien récupérées depuis les combos
        if not self.indus_layer or not self.indus_layer.isValid():
            self.indus_layer = self.indus_combo.currentData()
        if not self.liaison_layer or not self.liaison_layer.isValid():
            self.liaison_layer = self.liaison_combo.currentData()
        if not self.canal_layer or not self.canal_layer.isValid():
            self.canal_layer = self.canal_combo.currentData()
        if not self.fosse_layer or not self.fosse_layer.isValid():
            self.fosse_layer = self.fosse_combo.currentData()
        if not self.ouvr_layer or not self.ouvr_layer.isValid():
            self.ouvr_layer = self.ouvr_combo.currentData()

        # 3) Sélectionner TOUTES les liaisons de cet industriel
        if self.liaison_layer and self.liaison_layer.isValid():
            expr_l = QgsExpression(
                "trim(\"id_industriel\") = '{}'".format(ind_id.replace("'", "''"))
            )
            req_l = QgsFeatureRequest(expr_l)
            lids = [f.id() for f in self.liaison_layer.getFeatures(req_l)]
            self.liaison_layer.removeSelection()
            if lids:
                self.liaison_layer.selectByIds(lids)

        # 4) Sélectionner l'industriel lui-même
        if self.indus_layer and self.indus_layer.isValid():
            expr_i = QgsExpression(
                "trim(\"id\") = '{}'".format(ind_id.replace("'", "''"))
            )
            req_i = QgsFeatureRequest(expr_i)
            iids = [f.id() for f in self.indus_layer.getFeatures(req_i)]
            self.indus_layer.removeSelection()
            if iids:
                self.indus_layer.selectByIds(iids)

        # 5) Demander à l'utilisateur quel(s) réseau(x) cheminer
        choice = self._ask_indus_trace_network()
        if not choice:
            # L'utilisateur a annulé : on garde juste la désignation + sélection
            if self.industrial_dock and self.indus_svc:
                details = self.indus_svc.fetch_many([ind_id])
                self.industrial_dock.set_data(details)
            self.canvas.refresh()
            self._autosave()
            return

        # 6) Préparer le "type" voulu côté OUVRAGE.typreseau
        #    EP = '01', EU = '02', BOTH = pas de filtre sur typreseau
        wanted_typreseau = None
        if choice == "EP":
            wanted_typreseau = "01"
        elif choice == "EU":
            wanted_typreseau = "02"

        # 7) Vérifier couche CANALISATION minimale
        if not self.canal_layer or not self.canal_layer.isValid():
            QMessageBox.warning(
                self.iface.mainWindow(),
                "CheminerIndus",
                "Couche CANALISATION invalide pour le cheminement depuis l'industriel."
            )
            self.canvas.refresh()
            self._autosave()
            return

        # 8) Créer un tracer PROPRE (canal + fosse)
        #    ATTENTION : on ne filtre PLUS par catégorie ici, le tri EP/EU se fait
        #    uniquement au niveau des ouvrages de départ via typreseau.
        filters = {
            'category': '',
            'function': ''
        }
        self.tracer = NetworkTracer(
            canal_layer=self.canal_layer,
            fosse_layer=self.fosse_layer,
            field_alias=self.field_alias,
            filters=filters
        )

        # 9) Récupérer les ouvrages reliés à l'industriel via les liaisons sélectionnées
        ouvrages_all: List[str] = []
        if self.liaison_layer and self.liaison_layer.isValid():
            for lf in self.liaison_layer.selectedFeatures():
                try:
                    oid = (lf['id_ouvrage'] or "").strip()
                except Exception:
                    oid = ""
                if oid and oid.upper() != "INCONNU":
                    ouvrages_all.append(oid)

        if not ouvrages_all:
            QMessageBox.information(
                self.iface.mainWindow(),
                "CheminerIndus",
                "Aucun ouvrage relié trouvé pour cet industriel via les liaisons."
            )
            if self.industrial_dock and self.indus_svc:
                details = self.indus_svc.fetch_many([ind_id])
                self.industrial_dock.set_data(details)
            self.canvas.refresh()
            self._autosave()
            return

        # 10) Filtrer les ouvrages selon OUVRAGE.typreseau si EP ou EU sélectionné
        ouvrages: List[str] = list(ouvrages_all)
        if wanted_typreseau and self.ouvr_layer and self.ouvr_layer.isValid():
            filt: List[str] = []
            for oid in ouvrages_all:
                expr_o = QgsExpression(
                    "trim(\"idouvrage\") = '{}'".format(oid.replace("'", "''"))
                )
                req_o = QgsFeatureRequest(expr_o)
                feat_o = next(self.ouvr_layer.getFeatures(req_o), None)
                if not feat_o:
                    continue
                try:
                    tr = str(feat_o['typreseau'] or "").strip()
                except Exception:
                    tr = ""
                if tr == wanted_typreseau:
                    filt.append(oid)
            ouvrages = filt

            if not ouvrages:
                # Aucun ouvrage n'a le typreseau demandé → on informe et on sort proprement
                msg = (
                    "Aucun ouvrage relié à cet industriel n'a un type de réseau = {}.\n\n"
                    "Vérifiez le champ 'typreseau' de la couche OUVRAGE ou choisissez "
                    "l'option 'Réseaux EP + EU'."
                ).format(
                    "EP (01)" if wanted_typreseau == "01" else "EU (02)"
                )
                QMessageBox.information(
                    self.iface.mainWindow(),
                    "CheminerIndus",
                    msg
                )
                if self.industrial_dock and self.indus_svc:
                    details = self.indus_svc.fetch_many([ind_id])
                    self.industrial_dock.set_data(details)
                self.canvas.refresh()
                self._autosave()
                return

        # 11) Nettoyer la sélection actuelle sur canal + fosse
        if self.canal_layer and self.canal_layer.isValid():
            self.canal_layer.removeSelection()
        if self.fosse_layer and self.fosse_layer.isValid():
            self.fosse_layer.removeSelection()

        all_canal_ids: Set[int] = set()
        all_fosse_ids: Set[int] = set()
        all_nodes: Set[str] = set()

        # 12) Lancer le cheminement Amont→Aval depuis CHAQUE ouvrage retenu
        for oid in ouvrages:
            try:
                cids, fids = self.tracer.trace(oid, downstream=True)
            except Exception:
                continue
            if cids:
                all_canal_ids.update(cids)
            if fids:
                all_fosse_ids.update(fids)

            # Collecter les nœuds atteints pour mettre à jour _last_trace_nodes
            nodes = self._collect_nodes_from_ids(list(cids or []), list(fids or []), downstream=True)
            all_nodes.update(nodes)

        # 13) Appliquer les sélections sur le réseau (canalisations + fossés)
        if all_canal_ids and self.canal_layer and self.canal_layer.isValid():
            self.canal_layer.selectByIds(list(all_canal_ids))
        if all_fosse_ids and self.fosse_layer and self.fosse_layer.isValid():
            self.fosse_layer.selectByIds(list(all_fosse_ids))

        # 14) Mettre à jour les nœuds atteints et les liaisons depuis ces nœuds
        self._last_trace_nodes = all_nodes
        self._select_liaisons_from_nodes(sorted(all_nodes), clear=False)

        # 15) Mettre à jour la carte et le tableau des industriels
        self.canvas.refresh()

        if self.industrial_dock and self.indus_svc:
            details = self.indus_svc.fetch_many([ind_id])
            self._last_indus_data = details
            self.industrial_dock.set_data(details)

        self._autosave()


    # ---------------------------------------------------------
    # ASTREINTE
    # ---------------------------------------------------------
    def _attach_astreint(self):
        layer = self.astreint_combo.currentData()
        if not layer or not layer.isValid():
            QMessageBox.warning(self.iface.mainWindow(), "CheminerIndus", "Couche ASTREINTE invalide.")
            return
        self.astreint_layer = layer
        self.tool_astreint = AstreintSelectionTool(self.canvas, layer, id_field='id')
        self.tool_astreint.featureIdentified.connect(self._on_astreint)
        self.canvas.setMapTool(self.tool_astreint)

    def _on_astreint(self, aid: str):
        expr = QgsExpression("trim(\"id\") = '{}'".format(aid.replace("'","''")))
        req  = QgsFeatureRequest(expr)
        feat = next(self.astreint_layer.getFeatures(req), None)
        if feat:
            self.astreint_details = {f: feat[f] for f in feat.fields().names()}
            QMessageBox.information(self.iface.mainWindow(), "Astreinte", "Astreinte {} rattachée.".format(aid))
        self.canvas.unsetMapTool(self.canvas.mapTool())
        self._autosave()

    # ---------------------------------------------------------
    # DIAGNOSTICS
    # ---------------------------------------------------------
    def _open_diagnostic(self):
        if not self.canal_layer or not self.ouvr_layer:
            QMessageBox.warning(self.iface.mainWindow(),"CheminerIndus","Il faut CANALISATION et OUVRAGE.")
            return

        diag = Diagnostics(self.canal_layer, self.ouvr_layer)
        results = diag.run_selected_only()

        if not self.diag_dock:
            self.diag_dock = DiagnosticsDock(self.iface.mainWindow())
            self.diag_dock.on_zoom_request(self._zoom_to_feature_from_diag)
            self.diag_dock.on_refresh_request(self._open_diagnostic_with_wait)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.diag_dock)

        self.diag_dock.set_results(results, canal_layer=self.canal_layer, ouvr_layer=self.ouvr_layer)
        self.diag_dock.show(); self.diag_dock.raise_()

    def _zoom_to_feature_from_diag(self, layer_name: str, fid: int):
        lyr = None
        for L in (self.canal_layer, self.ouvr_layer, self.fosse_layer, self.indus_layer, self.liaison_layer):
            if L and L.name() == layer_name:
                lyr = L; break
        if not lyr:
            return
        feat = lyr.getFeature(fid)
        g = feat.geometry() if feat else None
        if g: self.canvas.setExtent(g.boundingBox()); self.canvas.refresh()

    # ---------------------------------------------------------
    # MASQUER ÉTIQUETTES via LABEL_CI
    # ---------------------------------------------------------
    def _toggle_mask_labels(self, checked: bool):
        if not self.label_layer:
            QMessageBox.warning(self.iface.mainWindow(),"CheminerIndus","La couche LABEL_CI est introuvable.")
            return

        prov = self.label_layer.dataProvider()
        prov.truncate()  # repart propre

        if checked:
            feats: List[QgsFeature] = []

            # OUVRAGE DE DÉPART
            start = (self.id_input.text() or "").strip()
            if self.ouvr_layer and self.ouvr_layer.isValid() and start:
                expr = QgsExpression("trim(\"idouvrage\") = '{}'".format(start.replace("'","''")))
                for f in self.ouvr_layer.getFeatures(QgsFeatureRequest(expr)):
                    g = f.geometry()
                    pt = None
                    if g:
                        try: pt = g.asPoint()
                        except Exception:
                            try: pt = g.centroid().asPoint()
                            except Exception: pt = None
                    if pt:
                        ff = QgsFeature(self.label_layer.fields())
                        ff.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(pt.x(), pt.y())))
                        ff.setAttribute("categorie", CAT_DEPART)
                        ff.setAttribute("label", start)
                        feats.append(ff)

            # NŒUDS VISITÉS
            if self.ouvr_layer and self.ouvr_layer.isValid() and self.visited:
                for v in self.visited:
                    vid_plain = str(v.get('id',"")).strip()
                    if not vid_plain:
                        continue
                    is_pol = bool(v.get('pollution'))
                    cat = CAT_VISITE_OUI if is_pol else CAT_VISITE_NON
                    expr = QgsExpression("trim(\"idouvrage\") = '{}'".format(vid_plain.replace("'","''")))
                    for f in self.ouvr_layer.getFeatures(QgsFeatureRequest(expr)):
                        g = f.geometry()
                        pt = None
                        if g:
                            try: pt = g.asPoint()
                            except Exception:
                                try: pt = g.centroid().asPoint()
                                except Exception: pt = None
                        if pt:
                            ff = QgsFeature(self.label_layer.fields())
                            ff.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(pt.x(), pt.y())))
                            ff.setAttribute("categorie", cat)
                            ff.setAttribute("label", vid_plain)
                            feats.append(ff)

            # ASTREINTE
            if self.astreint_layer and self.astreint_details:
                aid = str(self.astreint_details.get('id','')).strip()
                if aid:
                    expr = QgsExpression("trim(\"id\") = '{}'".format(aid.replace("'","''")))
                    for f in self.astreint_layer.getFeatures(QgsFeatureRequest(expr)):
                        g = f.geometry()
                        pt = None
                        if g:
                            try: pt = g.asPoint()
                            except Exception:
                                try: pt = g.centroid().asPoint()
                                except Exception: pt = None
                        if pt:
                            ff = QgsFeature(self.label_layer.fields())
                            ff.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(pt.x(), pt.y())))
                            ff.setAttribute("categorie", CAT_ASTREINTE)
                            ff.setAttribute("label", aid)
                            feats.append(ff)

            # INDUSTRIEL DÉSIGNÉ
            if self.indus_layer and self.indus_layer.isValid() and self.polluter_id:
                expr = QgsExpression("trim(\"id\") = '{}'".format(self.polluter_id.replace("'","''")))
                for f in self.indus_layer.getFeatures(QgsFeatureRequest(expr)):
                    g = f.geometry()
                    pt = None
                    if g:
                        try: pt = g.asPoint()
                        except Exception:
                            try: pt = g.centroid().asPoint()
                            except Exception: pt = None
                    if pt:
                        nom = ""
                        for k in ("Nom","nom","name","Name"):
                            try:
                                nom = f[k]
                                if nom: break
                            except Exception:
                                pass
                        nom = str(nom or self.polluter_id)
                        ff = QgsFeature(self.label_layer.fields())
                        ff.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(pt.x(), pt.y())))
                        ff.setAttribute("categorie", CAT_INDUS_DES)
                        ff.setAttribute("label", nom)
                        feats.append(ff)

            if feats:
                prov.addFeatures(feats)

            self.label_layer.triggerRepaint()
            self._mask_on = True
        else:
            self._mask_on = False
            self.label_layer.triggerRepaint()

        self.canvas.refresh()
        self._autosave()

    # ---------------------------------------------------------
    # REPORT
    # ---------------------------------------------------------
    def _make_report(self):
        try:
            save_path, _ = QFileDialog.getSaveFileName(self.iface.mainWindow(), "Enregistrer PDF", "", "PDF (*.pdf)")
            if not save_path:
                return

            # Capture carte
            tmp_dir = tempfile.gettempdir()
            screenshot = os.path.join(tmp_dir, "cheminer_carte.png")
            self.canvas.grab().save(screenshot)

            # Construire le PDF
            pdf = PDFGenerator(
                logo_path=os.path.join(ICONS_DIR,'logo.png'),
                legend_path=os.path.join(ICONS_DIR,'legende.png')
            )
            pdf.alias_nb_pages()
            if pdf.page_no() == 0:
                pdf.add_page()

            # ——— Page 1 : Contexte / Visites / Industriel ———
            pdf.set_global_header("SOURCE: BD SIG DU SIAH - "+datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
            pdf.set_title_top("RAPPORT DE CHEMINEMENT")

            # Contexte
            pdf.section_title("Contexte d'observation")
            pdf.set_font('Helvetica','',10)
            pdf.cell(0, 8, "Ouvrage de départ : {}".format(self.id_input.text()), ln=True)
            pdf.ln(2)

            # Visites
            pdf.section_title("Visite d'ouvrage")
            if self.visited:
                for v in self.visited:
                    pdf.cell(0, 6, "- {} : Pollué = {}".format(v['id'], "OUI" if v['pollution'] else "NON"), ln=True)
            else:
                pdf.cell(0,6,"Aucune visite.", ln=True)
            pdf.ln(3)

            # Industriel désigné
            if self.polluter_id:
                d = {}
                if not self.indus_svc and self.indus_combo:
                    self.indus_svc = IndustrialsService(self.indus_combo.currentData(), self.liaison_combo.currentData())
                if self.indus_svc:
                    info = self.indus_svc.fetch_many([self.polluter_id])
                    d = info.get(self.polluter_id, {})
                pdf.section_title("Industriel à l'origine de la pollution")
                pdf.table_industrial_info(d, bordered=True)

                # Note synchronisée
                self.polluter_note = (self.note_text.toPlainText() or "").strip()
                if self.polluter_note:
                    pdf.sub_section("Note de pollution")
                    pdf.multi_cell(0, 5, self.polluter_note)
                    pdf.ln(2)

            # ——— Page Astreinte ———
            if self.astreint_details:
                pdf.add_page()
                pdf.set_global_header("SOURCE: BD SIG DU SIAH - "+datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
                pdf.set_title_top("RAPPORT DE CHEMINEMENT")
                pdf.section_title("Astreinte exploitation")
                tab = {k:_safe_json(v) for k,v in self.astreint_details.items()}

                try:
                    pdf.add_astreint_table(tab, bordered=True)
                except AttributeError:
                    # si méthode non implémentée dans PDFGenerator, fallback simple
                    for k, v in tab.items():
                        pdf.cell(0, 6, f"{k} : {v}", ln=True)

            # ——— Page Carte + légende ———
            pdf.add_map_page(
                map_img_path=screenshot,
                title="CARTE DE LA SITUATION DU RÉSEAU"
            )

            # ——— Photos ———
            pdf.ln(8)
            self.ph_mgr.render(pdf)

            pdf.output(save_path)
            QMessageBox.information(self.iface.mainWindow(),"Rapport généré", save_path)
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(),"CheminerIndus","Erreur génération PDF : {}".format(e))

    # ---------------------------------------------------------
    # SESSION
    # ---------------------------------------------------------
    def _session_state(self) -> Dict[str,object]:
        # Synchroniser la note texte
        self.polluter_note = (self.note_text.toPlainText() or "").strip()

        # Sauver le contenu actuel de LABEL_CI (si masque actif)
        label_dump: List[Dict[str,object]] = []
        if self.label_layer and self._mask_on:
            for f in self.label_layer.getFeatures():
                g = f.geometry()
                if not g:
                    continue
                try:
                    pt = g.asPoint()
                except Exception:
                    try:
                        pt = g.centroid().asPoint()
                    except Exception:
                        continue
                label_dump.append({
                    "x": pt.x(),
                    "y": pt.y(),
                    "categorie": f["categorie"] if "categorie" in f.fields().names() else "",
                    "label": f["label"] if "label" in f.fields().names() else ""
                })

        # Sélection canalisations
        selected_canal_ids: List[int] = []
        if self.canal_layer:
            selected_canal_ids = list(self.canal_layer.selectedFeatureIds())

        # Sélection fossés
        selected_fosse_ids: List[int] = []
        if self.fosse_layer:
            selected_fosse_ids = list(self.fosse_layer.selectedFeatureIds())

        # ---- NOUVEAU : état du dock des industriels ----
        industrial_state: Optional[Dict[str, Any]] = None
        if self.industrial_dock:
            try:
                industrial_state = self.industrial_dock.get_state()
            except Exception:
                industrial_state = None
        return {
            "start_id": self.id_input.text(),
            "mode": self.direction_combo.currentText() if self.direction_combo else "",
            "category": self.cat_combo.currentData() if self.cat_combo else '',
            "function": self.func_combo.currentData() if self.func_combo else '',
            "visited": self.visited,
            "polluter_id": self.polluter_id,
            "polluter_note": self.polluter_note,
            "astreinte": {k:_safe_json(v) for k,v in self.astreint_details.items()},
            "mask_on": self._mask_on,
            "label_ci": label_dump,
            "selected_canal_ids": selected_canal_ids,
            "selected_fosse_ids": selected_fosse_ids,
            "catchment_on": bool(self.catchment_chk.isChecked()) if self.catchment_chk else False,
            "industrial_dock": industrial_state,
        }

    def _apply_session_state(self, st: Dict[str, Any], show_message: bool = True):
        """
        Applique un état de session déjà chargé (autosave ou chargement manuel).
        """
        try:
            # Champs simples
            self.id_input.setText(st.get("start_id",""))
            if self.cat_combo:
                cat = st.get("category","")
                for i in range(self.cat_combo.count()):
                    if self.cat_combo.itemData(i) == cat:
                        self.cat_combo.setCurrentIndex(i); break
            if self.func_combo:
                fun = st.get("function","")
                for i in range(self.func_combo.count()):
                    if self.func_combo.itemData(i) == fun:
                        self.func_combo.setCurrentIndex(i); break

            self.visited = st.get("visited",[])
            self.polluter_id = st.get("polluter_id","")
            self.polluter_note = st.get("polluter_note","")
            if self.note_text:
                self.note_text.setPlainText(self.polluter_note or "")
            self.astreint_details = st.get("astreinte",{})

            # LABEL_CI
            self._mask_on = bool(st.get("mask_on", False))
            lbl = st.get("label_ci", [])
            if self.label_layer:
                prov = self.label_layer.dataProvider()
                prov.truncate()
                if self._mask_on and lbl:
                    feats=[]
                    for rec in lbl:
                        try:
                            x = float(rec.get("x",0.0)); y=float(rec.get("y",0.0))
                        except Exception:
                            continue
                        ff = QgsFeature(self.label_layer.fields())
                        ff.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x,y)))
                        ff.setAttribute("categorie", rec.get("categorie",""))
                        ff.setAttribute("label",     rec.get("label",""))
                        feats.append(ff)
                    if feats:
                        prov.addFeatures(feats)
                    self.label_layer.triggerRepaint()

            # Restauration sélection canalisations
            if self.canal_combo and self.canal_combo.currentData():
                self.canal_layer = self.canal_combo.currentData()
                try:
                    ids = list(map(int, st.get("selected_canal_ids", [])))
                    self.canal_layer.removeSelection()
                    if ids:
                        self.canal_layer.selectByIds(ids)
                except Exception:
                    pass

            # Restauration sélection fossés
            if self.fosse_combo and self.fosse_combo.currentData():
                self.fosse_layer = self.fosse_combo.currentData()
                try:
                    fids = list(map(int, st.get("selected_fosse_ids", [])))
                    self.fosse_layer.removeSelection()
                    if fids:
                        self.fosse_layer.selectByIds(fids)
                except Exception:
                    pass

            # Restauration bassin de collecte
            catch_on = bool(st.get("catchment_on", False))
            if self.catchment_chk:
                # éviter double appel : setChecked déclenchera _toggle_catchment
                self.catchment_chk.setChecked(catch_on)

            # ---- NOUVEAU : restauration du dock industriels ----
            ind_state = st.get("industrial_dock")
            if ind_state:
                # Initialiser le service industriels si nécessaire
                if not self.indus_svc:
                    self.indus_layer   = self.indus_combo.currentData()
                    self.liaison_layer = self.liaison_combo.currentData()
                    self.indus_svc = IndustrialsService(self.indus_layer, self.liaison_layer)

                # Créer le dock si absent
                if not self.industrial_dock:
                    from ..gui.industrial_dock import IndustrialDock
                    self.industrial_dock = IndustrialDock(self.iface.mainWindow())
                    self.industrial_dock.on_zoom_request(self._zoom_to_industrial)
                    self.industrial_dock.on_designate_request(self._designate_industrial)
                    self.industrial_dock.on_refresh_request(self._refresh_industrial_dock_data)
                    self.iface.addDockWidget(Qt.RightDockWidgetArea, self.industrial_dock)

                # Appliquer l'état au dock
                try:
                    self.industrial_dock.apply_state(ind_state)
                except Exception:
                    pass

                # Mémoriser les derniers industriels (pour les rafraîchissements / rapport)
                self._last_indus_data = ind_state.get("raw_data") or {}

                # Ouvrir / fermer selon l'état sauvegardé
                if ind_state.get("is_open", False):
                    self.industrial_dock.show()
                    self.industrial_dock.raise_()
                else:
                    self.industrial_dock.hide()

            if show_message:
                QMessageBox.information(self.iface.mainWindow(),"CheminerIndus","Session chargée.")
            self.canvas.refresh()
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(),"CheminerIndus","Erreur restauration session : {}".format(e))

            if show_message:
                QMessageBox.information(self.iface.mainWindow(),"CheminerIndus","Session chargée.")
            self.canvas.refresh()
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(),"CheminerIndus","Erreur restauration session : {}".format(e))

    def _save_session(self):
        path, _ = QFileDialog.getSaveFileName(self.iface.mainWindow(),"Sauvegarder session",".","Texte (*.txt)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._session_state(), f, ensure_ascii=False, indent=2)
            QMessageBox.information(self.iface.mainWindow(),"CheminerIndus","Session sauvegardée.")
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(),"CheminerIndus","Erreur sauvegarde : {}".format(e))

    def _load_session(self):
        path, _ = QFileDialog.getOpenFileName(self.iface.mainWindow(),"Charger session",".","Texte (*.txt)")
        if not path:
            return
        try:
            with open(path,"r",encoding="utf-8") as f:
                st = json.load(f)
            self._apply_session_state(st, show_message=True)
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(),"CheminerIndus","Erreur chargement : {}".format(e))

    # ---------------------------------------------------------
    # TABLES MINIMALES (couches mémoire si absentes)
    # ---------------------------------------------------------
    def _create_minimal_tables(self):
        prj = QgsProject.instance()
        if not any("CANALISATION" == L.name() for L in prj.mapLayers().values()):
            v = QgsVectorLayer("LineString?crs=EPSG:2154&field=id:string&field=idnini:string&field=idnterm:string&field=typreseau:string&field=fonccanass:string&field=diametre:int&field=dimension:int", "CANALISATION", "memory")
            prj.addMapLayer(v)
        if not any("OUVRAGE" == L.name() for L in prj.mapLayers().values()):
            v = QgsVectorLayer("Point?crs=EPSG:2154&field=idouvrage:string&field=typreseau:string&field=acces:string", "OUVRAGE", "memory")
            prj.addMapLayer(v)
        if not any("FOSSE" == L.name() for L in prj.mapLayers().values()):
            v = QgsVectorLayer("LineString?crs=EPSG:2154&field=id:string&field=idnini:string&field=idnterm:string", "FOSSE", "memory")
            prj.addMapLayer(v)
        if not any("INDUSTRIELS" == L.name() for L in prj.mapLayers().values()):
            v = QgsVectorLayer("Point?crs=EPSG:2154&field=id:string&field=Nom:string&field=Adresse:string&field=Activite:string&field=Risques:string&field=Produits:string&field=siret:string", "INDUSTRIELS", "memory")
            prj.addMapLayer(v)
        if not any("LIAISON_INDUS" == L.name() for L in prj.mapLayers().values()):
            v = QgsVectorLayer("LineString?crs=EPSG:2154&field=id:string&field=id_industriel:string&field=id_ouvrage:string", "LIAISON_INDUS", "memory")
            prj.addMapLayer(v)
        if not any("ASTREINTE-EXPLOIT" == L.name() for L in prj.mapLayers().values()):
            v = QgsVectorLayer("Point?crs=EPSG:2154&field=id:string&field=nom:string&field=tel:string&field=date:string&field=heure:string&field=agent:string&field=adresse:string&field=complement:string&field=tampon:string&field=interv_ep:string&field=interv_eu:string&field=interv_voi:string&field=prestatair:string&field=typ_cana:string&field=message:string&field=action_m:string", "ASTREINTE-EXPLOIT", "memory")
            prj.addMapLayer(v)
        if not any("LABEL_CI" == L.name() for L in prj.mapLayers().values()):
            v = QgsVectorLayer("Point?crs=EPSG:2154&field=categorie:string&field=label:string", "LABEL_CI", "memory")
            prj.addMapLayer(v)

        QMessageBox.information(self.iface.mainWindow(),"CheminerIndus","Tables minimales créées (mémoire).")
        self._autosave()

    # ---------------------------------------------------------
    # RESET
    # ---------------------------------------------------------
    def _reset(self):
        if self.flux_btn and self.flux_btn.isChecked():
            self.flux_btn.setChecked(False); self.flow_anim.stop()
        if self.catchment_chk and self.catchment_chk.isChecked():
            self.catchment_chk.setChecked(False)
        self.highlight_mgr.clear()

        if self.label_layer:
            try:
                self.label_layer.dataProvider().truncate()
                self.label_layer.triggerRepaint()
            except Exception:
                pass

        for lyr in (self.canal_layer, self.ouvr_layer, self.fosse_layer,
                    self.liaison_layer, self.indus_layer, self.astreint_layer):
            try:
                if isinstance(lyr, QgsVectorLayer) and lyr.isValid():
                    lyr.removeSelection()
            except RuntimeError:
                # couche supprimée du projet
                pass

        for w in (self.id_input, self.search_input, self.visit_input):
            if hasattr(w,'clear'): w.clear()
        if self.note_text:
            self.note_text.clear()

        self.visited.clear()
        self.polluter_id = ""; self.polluter_note = ""; self.astreint_details.clear()
        self._last_trace_nodes.clear()
        self._mask_on = False
        self._last_indus_data = {}

        if self.industrial_dock:
            self.iface.removeDockWidget(self.industrial_dock); self.industrial_dock = None
        if self.diag_dock:
            self.iface.removeDockWidget(self.diag_dock); self.diag_dock = None

        self.canvas.refresh()
        QMessageBox.information(self.iface.mainWindow(),"CheminerIndus","Plugin réinitialisé.")
        self._autosave()
