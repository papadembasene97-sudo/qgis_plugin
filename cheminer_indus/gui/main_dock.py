# -*- coding: utf-8 -*-
# cheminer_indus/gui/main_dock.py

from __future__ import annotations

import os, json, datetime, tempfile, webbrowser
from typing import Optional, List, Tuple, Set, Dict, Any

from qgis.PyQt.QtCore import Qt, QDate, QTime, QDateTime, QSize, QTimer, QElapsedTimer
from qgis.PyQt.QtGui import QIcon, QPixmap, QColor, QMovie
from qgis.PyQt.QtWidgets import (
    QAction, QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QGridLayout, QMessageBox, QTabWidget,
    QFileDialog, QCheckBox, QDialog, QGroupBox, QTextEdit, QColorDialog,
    QSizePolicy, QApplication, QRadioButton, QScrollArea, QFrame, QInputDialog,
    QFormLayout, QDateEdit
)
from qgis.gui import QgsMapToolEmitPoint

from qgis.core import (
    QgsProject, QgsExpression, QgsFeatureRequest, QgsVectorLayer,
    QgsFeature, QgsGeometry, QgsPointXY, Qgis, QgsCoordinateTransform,
    QgsSpatialIndex, QgsDataSourceUri
)

from ..utils.qt_compat import (
    QT_ALIGN_CENTER, QT_LEFT_DOCK_WIDGET_AREA, QT_RIGHT_DOCK_WIDGET_AREA,
    QT_FRAMELESS_WINDOW_HINT, QT_WA_TRANSLUCENT_BACKGROUND,
    QT_SMOOTH_TRANSFORMATION, QT_WAIT_CURSOR, QT_CHECKED, QT_NO_FRAME
)
from ..utils.config             import ICONS_DIR
from ..core.selection           import MapSelectionTool, AstreintSelectionTool
from ..core.tracer              import NetworkTracer
from ..core.industrials         import IndustrialsService
from ..core.pv_service          import PVService
from ..core.diagnostics         import Diagnostics
from ..core.highlight_manager   import HighlightManager
from ..animation.flow_animator  import FlowAnimator
from ..report.pdf_generator     import PDFGenerator
from ..report.photos            import PhotoManager
from ..gui.industrial_dock      import IndustrialDock
from ..gui.diagnostics_dock     import DiagnosticsDock
from ..gui.pv_conformite_tab    import PVConformiteTab
from ..utils.geom_utils         import concave_envelope_from_selected
from ..core.autosave_manager    import AutoSaveManager
from ..gui.main_dock_optimized  import OptimizedNodeOps


# Catégories utilisées dans LABEL_CI
CAT_DEPART       = "Départ_Cheminement"
CAT_VISITE_OUI   = "Pollué"
CAT_VISITE_NON   = "Non_Pollué"
CAT_ASTREINTE    = "Astreinte"
CAT_INDUS_DES    = "Origine_Pollution"
CAT_POLL_DIVERS  = "Pollution_Divers"

PLUGIN_BASE_NAME = "TRACK-EAU-POLL"
PLUGIN_VARIANT = os.environ.get("TRACK_EAU_VARIANT", "LITE").strip().upper()
PLUGIN_DISPLAY_NAME = PLUGIN_BASE_NAME if PLUGIN_VARIANT == "FULL" else f"{PLUGIN_BASE_NAME}-LITE"


def _display_name_for_variant(variant: str) -> str:
    v = str(variant or "LITE").strip().upper()
    return PLUGIN_BASE_NAME if v == "FULL" else f"{PLUGIN_BASE_NAME}-LITE"


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
        self._plugin_menu_name = ""

        # couches
        self.canal_layer   : Optional[QgsVectorLayer] = None
        self.ouvr_layer    : Optional[QgsVectorLayer] = None
        self.fosse_layer   : Optional[QgsVectorLayer] = None
        self.indus_layer   : Optional[QgsVectorLayer] = None
        self.liaison_layer : Optional[QgsVectorLayer] = None
        self.astreint_layer : Optional[QgsVectorLayer] = None
        self.pv_layer      : Optional[QgsVectorLayer] = None  # PV_CONFORMITE
        self.pollution_divers_layer: Optional[QgsVectorLayer] = None
        self.label_layer   : Optional[QgsVectorLayer] = None  # LABEL_CI

        # services / managers
        self.tracer         : Optional[NetworkTracer] = None
        self.indus_svc      : Optional[IndustrialsService] = None
        self.pv_svc         : Optional['PVService'] = None  # Service PV
        self.highlight_mgr   = HighlightManager(self.canvas)
        self.flow_anim       = FlowAnimator(self.canvas)
        self.ph_mgr          = PhotoManager()
        self.auto_mgr        = AutoSaveManager(self.iface, plugin_name=PLUGIN_DISPLAY_NAME)

        # UI state
        self.industrial_dock: Optional[IndustrialDock] = None
        self.diag_dock      : Optional[DiagnosticsDock] = None
        self._last_indus_data: Dict[str, Dict[str, str]] = {}
        self._last_pv_data: Dict[str, Dict[str, str]] = {}  # Données PV détectés
        self._last_process_durations: Dict[str, int] = {}
        self.theme_name: str = "Clair"
        self.language: str = "fr"
        self._tabs: Optional[QTabWidget] = None
        self._tab_order: List[str] = []
        self._main_widget: Optional[QWidget] = None
        self._header_title: Optional[QLabel] = None
        self._header_logo: Optional[QLabel] = None
        self._header_icon: Optional[QLabel] = None
        self.pv_tab: Optional[PVConformiteTab] = None

        # selection tools
        self.tool_select    = None
        self.tool_visit     = None
        self.tool_astreint  = None

        # visites & pollueur & astreinte
        self.visited: List[Dict[str, object]] = []
        self.polluter_id   : str = ""
        self.polluter_note : str = ""
        self.polluter_type : str = ""
        self.polluter_details: Dict[str, Any] = {}
        self.astreint_details: Dict[str, object] = {}

        # masque étiquettes (via LABEL_CI)
        self._mask_on = False

        # Optimisations pour désélection de nœuds
        self._node_ops: Optional[OptimizedNodeOps] = None

        # widgets
        self.canal_combo = self.ouvr_combo = self.fosse_combo = None
        self.indus_combo = self.liaison_combo = self.astreint_combo = None
        self.pv_combo = None  # Combo PV_CONFORMITE
        self.pollution_divers_combo = None  # Combo POINT_POLLUTION_DIVERS
        self.id_input = self.search_input = None
        self.trace_btn = self.flux_btn = None
        self.direction_combo = self.cat_combo = self.func_combo = None
        self.radius_combo = None
        self.visit_input = None
        self.btn_show_indus = None
        self.btn_designate_ouvrage = None
        self.note_text = None
        self.catchment_chk = None
        self.color_btn = None  # bouton Couleurs
        self.variant_combo = None

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
        self._ouvrage_z_cache: Dict[str, float] = {}
        
        # Chemins personnalisés pour logo et icône
        self.custom_logo_path: str = ""  # Chemin vers le logo personnalisé
        self.custom_icon_path: str = ""  # Chemin vers l'icône personnalisée
        self.plugin_variant: str = PLUGIN_VARIANT

        # Autosave instantané (debounce court)
        self._autosave_timer = QTimer()
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_suspended = False
        self._indus_svc_key = None
        self._pv_svc_key = None
        self._node_ops_key = None
        self._tracer_key = None
        self._network_cache_key = None
        self._canal_nodes_by_fid: Dict[int, Tuple[str, str]] = {}
        self._fosse_nodes_by_fid: Dict[int, Tuple[str, str]] = {}
        self._liaison_fids_by_node: Dict[str, Set[int]] = {}

    # ---------------------------------------------------------
    # Integration QGIS
    # ---------------------------------------------------------
    def init_gui(self):
        # Charger les paramètres pour obtenir l'icône personnalisée
        self._load_settings_on_startup()
        self._apply_plugin_variant(self.plugin_variant, persist=False, show_message=False)

        # Utiliser l'icône personnalisée s'il existe
        icon_path = self.get_icon_path() if hasattr(self, 'get_icon_path') else os.path.join(ICONS_DIR, 'icon.png')
        icon = QIcon(icon_path)
        act = QAction(icon, PLUGIN_DISPLAY_NAME, self.iface.mainWindow())
        act.triggered.connect(self._show_with_splash)
        self.iface.addToolBarIcon(act)
        self._plugin_menu_name = f"&{PLUGIN_DISPLAY_NAME}"
        self.iface.addPluginToMenu(self._plugin_menu_name, act)
        self._action = act

    def unload(self):
        try:
            self._autosave()
        except Exception:
            pass
        if self._action:
            try:
                self.iface.removeToolBarIcon(self._action)
                if self._plugin_menu_name:
                    self.iface.removePluginMenu(self._plugin_menu_name, self._action)
            except Exception:
                pass
        if self.dock:
            self.iface.removeDockWidget(self.dock)
        if self.industrial_dock:
            self.iface.removeDockWidget(self.industrial_dock)
        if self.diag_dock:
            self.iface.removeDockWidget(self.diag_dock)


    def _on_variant_changed(self, _index: int):
        variant = self.variant_combo.currentData() if self.variant_combo else "LITE"
        self._apply_plugin_variant(variant, persist=True, show_message=True)
        self._request_autosave()

    def _apply_plugin_variant(self, variant: str, persist: bool = True, show_message: bool = False):
        global PLUGIN_VARIANT, PLUGIN_DISPLAY_NAME
        PLUGIN_VARIANT = str(variant or "LITE").strip().upper()
        PLUGIN_DISPLAY_NAME = _display_name_for_variant(PLUGIN_VARIANT)
        self.plugin_variant = PLUGIN_VARIANT

        if self.auto_mgr:
            self.auto_mgr.plugin_name = PLUGIN_DISPLAY_NAME

        try:
            if self._action:
                self._action.setText(PLUGIN_DISPLAY_NAME)
                try:
                    if self._plugin_menu_name:
                        self.iface.removePluginMenu(self._plugin_menu_name, self._action)
                except Exception:
                    pass
                self._plugin_menu_name = f"&{PLUGIN_DISPLAY_NAME}"
                self.iface.addPluginToMenu(self._plugin_menu_name, self._action)
            if self.dock:
                self.dock.setWindowTitle(PLUGIN_DISPLAY_NAME)
            if self._header_title:
                self._header_title.setText(PLUGIN_DISPLAY_NAME)
        except Exception:
            pass

        if persist:
            self._save_settings_silent()

        if show_message:
            QMessageBox.information(
                self.iface.mainWindow(),
                PLUGIN_DISPLAY_NAME,
                "Variante enregistrée. Redémarrez QGIS pour afficher les onglets correspondants (FULL/LITE)."
            )

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
        splash.setWindowFlag(QT_FRAMELESS_WINDOW_HINT)
        splash.setAttribute(QT_WA_TRANSLUCENT_BACKGROUND, True)

        v = QVBoxLayout(splash)
        v.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel()
        lbl.setAlignment(QT_ALIGN_CENTER)
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

        self.dock = QDockWidget(PLUGIN_DISPLAY_NAME, self.iface.mainWindow())
        self.dock.setAllowedAreas(QT_LEFT_DOCK_WIDGET_AREA | QT_RIGHT_DOCK_WIDGET_AREA)
        
        # Charger les paramètres personnalisés au démarrage
        self._load_settings_on_startup()

        main = QWidget()
        lay  = QVBoxLayout(main)

        # -------------------------------------------------
        # En-tête (icône centrée)
        # -------------------------------------------------
        head = QHBoxLayout()

        header_container = QWidget()
        header_container.setFixedHeight(100)
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)

        header_block = QWidget()
        header_block_layout = QVBoxLayout(header_block)
        header_block_layout.setContentsMargins(0, 0, 0, 0)
        header_block_layout.setSpacing(2)

        icon = QLabel()
        icon_path = self.get_icon_path() if hasattr(self, 'get_icon_path') else os.path.join(ICONS_DIR, 'icon.png')
        icon_pix = QPixmap(icon_path)
        icon_scaled = icon_pix.scaledToHeight(64, QT_SMOOTH_TRANSFORMATION)
        icon.setPixmap(icon_scaled)
        icon.setAlignment(QT_ALIGN_CENTER)

        title = QLabel(PLUGIN_DISPLAY_NAME)
        title.setAlignment(QT_ALIGN_CENTER)
        title.setObjectName("trackHeaderTitle")

        header_block_layout.addWidget(icon)
        header_block_layout.addWidget(title)

        header_layout.addStretch()
        header_layout.addWidget(header_block)
        header_layout.addStretch()

        head.addWidget(header_container)
        lay.addLayout(head)

        self._main_widget = main
        self._header_title = title
        self._header_icon = icon
        self._apply_theme(self.theme_name)

        # -------------------------------------------------
        # Onglets
        # -------------------------------------------------
        tabs = QTabWidget()
        self._tabs = tabs
        lay.addWidget(tabs)

        if self.plugin_variant == "FULL":
            self._tab_order = ["tab_trace", "tab_visit", "tab_actions", "tab_pv", "tab_settings"]
            tabs.addTab(self._tab_trace(),       self._t("tab_trace"))
            tabs.addTab(self._tab_visit_indus(), self._t("tab_visit"))
            tabs.addTab(self._tab_actions(),     self._t("tab_actions"))
            tabs.addTab(self._tab_pv(),          self._t("tab_pv"))
            tabs.addTab(self._tab_settings(),    self._t("tab_settings"))
        else:
            self._tab_order = ["tab_trace", "tab_visit", "tab_settings"]
            tabs.addTab(self._tab_trace(),       self._t("tab_trace"))
            tabs.addTab(self._tab_visit_indus(), self._t("tab_visit"))
            tabs.addTab(self._tab_settings(),    self._t("tab_settings"))

        self.dock.setWidget(main)
        self.iface.addDockWidget(QT_LEFT_DOCK_WIDGET_AREA, self.dock)

        self._populate_layers()
        self._init_autosave()
        self._apply_language(self.language)
        self._setup_autosave_hooks()

    # ---------------------------------------------------------
    # Utilitaires génériques (sablier, autosave, inversion)
    # ---------------------------------------------------------
    def _t(self, key: str) -> str:
        translations = {
            "fr": {
                "tab_trace": "CHEMINEMENT",
                "tab_visit": "VISITE-INDUS",
                "tab_actions": "ACTIONS",
                "tab_pv": "🏠 PV",
                "tab_settings": "⚙️ PARAMÈTRES" if self.plugin_variant == "FULL" else "⚙️ PARAMÉTRAGE",
            },
            "en": {
                "tab_trace": "TRACE",
                "tab_visit": "VISIT-INDUS",
                "tab_actions": "ACTIONS",
                "tab_pv": "🏠 PV",
                "tab_settings": "⚙️ SETTINGS",
            },
        }
        return translations.get(self.language, translations["fr"]).get(key, key)

    def _tr_report(self, key: str) -> str:
        translations = {
            "fr": {
                "save_pdf": "Enregistrer PDF",
                "report_title": "RAPPORT DE CHEMINEMENT",
                "context": "Contexte d'observation",
                "visit": "Visite d'ouvrage",
                "no_visit": "Aucune visite.",
                "pv_origin": "PV à l'origine de la pollution",
                "indus_origin": "Industriel à l'origine de la pollution",
                "note": "Note de pollution",
                "astreinte": "Astreinte exploitation",
                "map_title": "CARTE DE LA SITUATION DU RÉSEAU",
            },
            "en": {
                "save_pdf": "Save PDF",
                "report_title": "TRACE REPORT",
                "context": "Observation context",
                "visit": "Manhole visit",
                "no_visit": "No visits.",
                "pv_origin": "PV identified as pollution source",
                "indus_origin": "Industrial identified as pollution source",
                "note": "Pollution note",
                "astreinte": "On-call operations",
                "map_title": "NETWORK SITUATION MAP",
            },
        }
        return translations.get(self.language, translations["fr"]).get(key, key)

    def _apply_language(self, lang: str):
        if not lang:
            return
        self.language = lang
        if self._tabs and self._tab_order:
            for idx, key in enumerate(self._tab_order):
                self._tabs.setTabText(idx, self._t(key))
        if self.pv_tab and hasattr(self.pv_tab, "set_language"):
            self.pv_tab.set_language(lang)
        self._apply_language_to_controls()

    def _apply_language_to_controls(self):
        translations = {
            "fr": {
                "start_id": "ID ouvrage départ :",
                "select_map": "Sélection carte",
                "search": "Recherche :",
                "search_btn": "Rechercher",
                "type": "Type :",
                "category": "Catégorie :",
                "function": "Fonction :",
                "trace": "Cheminer",
                "flux": "Flux",
                "colors": "Couleurs",
                "visit_nodes": "Visites de nœuds",
                "visit_btn": "Visiter (Pollué O/N)",
                "visit_tooltip": "Sélectionner un nœud sur la carte",
                "industrials": "Industriels",
                "show_indus": "Afficher Indus connectés",
                "note_placeholder": "Note de pollution (si désignation)…",
                "attach": "Rattacher Astreinte",
                "catchment": "Bassin de collecte",
                "catchment_tip": "Affiche/masque un contour concave autour du réseau sélectionné",
                "diagnostic": "Diagnostics",
                "pdf": "Générer PDF",
                "photos": "Ajouter Photos (+ commentaires)",
                "mask": "Masquer/Demasquer étiquettes",
                "save_session": "Sauvegarder session",
                "load_session": "Charger session",
                "schema": "Créer tables minimales",
                "reset": "Réinitialiser",
            },
            "en": {
                "start_id": "Start structure ID:",
                "select_map": "Select on map",
                "search": "Search:",
                "search_btn": "Search",
                "type": "Type:",
                "category": "Category:",
                "function": "Function:",
                "trace": "Trace",
                "flux": "Flow",
                "colors": "Colors",
                "visit_nodes": "Node visits",
                "visit_btn": "Visit (Polluted Y/N)",
                "visit_tooltip": "Select a node on the map",
                "industrials": "Industrials",
                "show_indus": "Show connected Industrials",
                "note_placeholder": "Pollution note (if designated)…",
                "attach": "Attach on-call",
                "catchment": "Catchment area",
                "catchment_tip": "Show/hide a concave outline around the selected network",
                "diagnostic": "Diagnostics",
                "pdf": "Generate PDF",
                "photos": "Add photos (+ comments)",
                "mask": "Show/Hide labels",
                "save_session": "Save session",
                "load_session": "Load session",
                "schema": "Create minimal tables",
                "reset": "Reset",
            },
        }
        tr = translations.get(self.language, translations["fr"])
        if hasattr(self, "lbl_start_id") and self.lbl_start_id:
            self.lbl_start_id.setText(tr["start_id"])
        if hasattr(self, "btn_sel") and self.btn_sel:
            self.btn_sel.setText(tr["select_map"])
        if hasattr(self, "lbl_search") and self.lbl_search:
            self.lbl_search.setText(tr["search"])
        if hasattr(self, "btn_search") and self.btn_search:
            self.btn_search.setText(tr["search_btn"])
        if hasattr(self, "lbl_type") and self.lbl_type:
            self.lbl_type.setText(tr["type"])
        if hasattr(self, "lbl_category") and self.lbl_category:
            self.lbl_category.setText(tr["category"])
        if hasattr(self, "lbl_function") and self.lbl_function:
            self.lbl_function.setText(tr["function"])
        if self.trace_btn:
            self.trace_btn.setText(tr["trace"])
        if self.flux_btn:
            self.flux_btn.setText(tr["flux"])
        if self.color_btn:
            self.color_btn.setText(tr["colors"])
        if hasattr(self, "box_v") and self.box_v:
            self.box_v.setTitle(tr["visit_nodes"])
        if hasattr(self, "btn_visit") and self.btn_visit:
            self.btn_visit.setText(tr["visit_btn"])
        if hasattr(self, "btn_pick") and self.btn_pick:
            self.btn_pick.setToolTip(tr["visit_tooltip"])
        if hasattr(self, "box_i") and self.box_i:
            self.box_i.setTitle(tr["industrials"])
        if self.btn_show_indus:
            self.btn_show_indus.setText(tr["show_indus"])
        if self.note_text:
            self.note_text.setPlaceholderText(tr["note_placeholder"])
        if hasattr(self, "btn_att") and self.btn_att:
            self.btn_att.setText(tr["attach"])
        if self.catchment_chk:
            self.catchment_chk.setText(tr["catchment"])
            self.catchment_chk.setToolTip(tr["catchment_tip"])
        if hasattr(self, "btn_diag") and self.btn_diag:
            self.btn_diag.setText(tr["diagnostic"])
        if hasattr(self, "btn_pdf") and self.btn_pdf:
            self.btn_pdf.setText(tr["pdf"])
        if hasattr(self, "btn_ph") and self.btn_ph:
            self.btn_ph.setText(tr["photos"])
        if hasattr(self, "btn_mask") and self.btn_mask:
            self.btn_mask.setText(tr["mask"])
        if hasattr(self, "btn_save_session") and self.btn_save_session:
            self.btn_save_session.setText(tr["save_session"])
        if hasattr(self, "btn_load_session") and self.btn_load_session:
            self.btn_load_session.setText(tr["load_session"])
        if hasattr(self, "btn_schema") and self.btn_schema:
            self.btn_schema.setText(tr["schema"])
        if hasattr(self, "btn_rst") and self.btn_rst:
            self.btn_rst.setText(tr["reset"])

    def _theme_styles(self) -> Dict[str, str]:
        return {
            "Clair": """
                QWidget { background-color: #f8fafc; color: #0f172a; }
                QTabWidget::pane { border: 1px solid #cbd5f5; border-radius: 8px; padding: 6px; background: #ffffff; }
                QTabBar::tab {
                    background: #e2e8f0; color: #0f172a; padding: 11px 18px; margin-right: 6px;
                    border-top-left-radius: 8px; border-top-right-radius: 8px; font-size: 10px;
                }
                QTabBar::tab:selected { background: #CCEDFC; color: #0f172a; font-weight: bold; }
                QTabBar::tab:hover { background: #dbeafe; }
                QTabBar::tab:pressed { background: #bfdbfe; padding-top: 12px; padding-bottom: 10px; }
                QGroupBox { border: 1px solid #cbd5f5; border-radius: 8px; margin-top: 10px; background: #ffffff; }
                QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 6px; color: #2563eb; font-weight: bold; }
                QPushButton { background: #DAE3F7; color: #1C1A1A; padding: 8px 14px; border-radius: 8px; font-size: 11px; }
                QPushButton:hover { background: #DFE5F5; }
                QPushButton:pressed { background: #c7d2fe; padding-top: 9px; padding-bottom: 7px; }
                QTableWidget { background: #ffffff; alternate-background-color: #f1f5f9; gridline-color: #e2e8f0; }
                QHeaderView::section { background-color: #e2e8f0; color: #0f172a; padding: 4px; border: 1px solid #cbd5f5; }
                QLabel#trackHeaderTitle { font-size: 22px; font-weight: bold; color: #0f172a; }
            """,
            "Sombre": """
                QWidget { background-color: #121D33; color: #e5e7eb; }
                QTabWidget::pane { border: 1px solid #374151; border-radius: 8px; padding: 6px; background: #0f172a; }
                QTabBar::tab {
                    background: #62748C; color: #e5e7eb; padding: 11px 18px; margin-right: 6px;
                    border-top-left-radius: 8px; border-top-right-radius: 8px; font-size: 12px;
                }
                QTabBar::tab:selected { background: #4f46e5; color: #ffffff; font-weight: bold; }
                QTabBar::tab:hover { background: #64748b; }
                QTabBar::tab:pressed { background: #3730a3; padding-top: 12px; padding-bottom: 10px; }
                QGroupBox { border: 1px solid #374151; border-radius: 8px; margin-top: 10px; background: #0f172a; }
                QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 6px; color: #a5b4fc; font-weight: bold; }
                QPushButton { background: #4f46e5; color: #ffffff; padding: 8px 14px; border-radius: 8px; font-size: 11px; }
                QPushButton:hover { background: #6366f1; }
                QPushButton:pressed { background: #312e81; padding-top: 9px; padding-bottom: 7px; }
                QTableWidget { background: #0b1120; alternate-background-color: #111827; gridline-color: #374151; }
                QHeaderView::section { background-color: #1f2937; color: #e5e7eb; padding: 4px; border: 1px solid #374151; }
                QLabel#trackHeaderTitle { font-size: 22px; font-weight: bold; color: #e5e7eb; }
            """,
        }

    def _apply_theme(self, theme_name: str):
        if not theme_name or not self._main_widget:
            return
        self.theme_name = theme_name
        stylesheet = self._theme_styles().get(theme_name)
        if not stylesheet:
            self.theme_name = "Clair"
            stylesheet = self._theme_styles().get("Clair", "")
        if stylesheet:
            self._main_widget.setStyleSheet(stylesheet)

    def _run_with_wait_cursor(self, func, *args, process_key: Optional[str] = None,
                              label: str = "Traitement en cours...", **kwargs):
        """
        Exécute une fonction en affichant uniquement un sablier.
        """
        elapsed = QElapsedTimer()
        elapsed.start()
        try:
            self._autosave_suspended = True
            QApplication.setOverrideCursor(QT_WAIT_CURSOR)
            QApplication.processEvents()
            return func(*args, **kwargs)
        finally:
            self._autosave_suspended = False
            try:
                QApplication.restoreOverrideCursor()
            except Exception:
                pass
            try:
                if process_key and elapsed.isValid():
                    self._last_process_durations[process_key] = elapsed.elapsed()
            except Exception:
                pass
            # flush autosave à la fin des traitements lourds
            self._request_autosave(delay_ms=1200)

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
        if self._autosave_suspended:
            return
        try:
            if self.auto_mgr and self.auto_mgr.path:
                self.auto_mgr.save(self._session_state())
        except Exception:
            pass


    def _request_autosave(self, delay_ms: int = 250):
        """Programme une sauvegarde quasi instantanée après une action utilisateur."""
        if self._autosave_suspended:
            return
        try:
            self._autosave_timer.start(max(150, int(delay_ms)))
        except Exception:
            self._autosave()

    def _setup_autosave_hooks(self):
        """Branche l'autosave sur les interactions principales de l'UI."""
        try:
            if self.id_input:
                self.id_input.textChanged.connect(lambda *_: self._request_autosave())
            if self.search_input:
                self.search_input.textChanged.connect(lambda *_: self._request_autosave())
            if self.visit_input:
                self.visit_input.textChanged.connect(lambda *_: self._request_autosave())
            if self.note_text:
                self.note_text.textChanged.connect(lambda: self._request_autosave())
            if self.direction_combo:
                self.direction_combo.currentIndexChanged.connect(lambda *_: self._request_autosave())
            if self.cat_combo:
                self.cat_combo.currentIndexChanged.connect(lambda *_: self._request_autosave())
            if self.func_combo:
                self.func_combo.currentIndexChanged.connect(lambda *_: self._request_autosave())
            if self.radius_combo:
                self.radius_combo.currentIndexChanged.connect(lambda *_: self._request_autosave())
            for combo in (self.canal_combo, self.ouvr_combo, self.fosse_combo, self.indus_combo, self.liaison_combo, self.astreint_combo, self.pv_combo, self.pollution_divers_combo):
                if combo:
                    combo.currentIndexChanged.connect(lambda *_: self._request_autosave())
            if self.theme_combo:
                self.theme_combo.currentIndexChanged.connect(lambda *_: self._request_autosave())
            if self.lang_combo:
                self.lang_combo.currentIndexChanged.connect(lambda *_: self._request_autosave())
            if hasattr(self, "variant_combo") and self.variant_combo:
                self.variant_combo.currentIndexChanged.connect(lambda *_: self._request_autosave())
            for lyr in (self.canal_layer, self.fosse_layer, self.indus_layer, self.liaison_layer, self.pv_layer):
                if lyr and hasattr(lyr, 'selectionChanged'):
                    lyr.selectionChanged.connect(lambda *_: self._request_autosave())
        except Exception:
            pass

    # Wrappers avec sablier
    def _do_trace_with_wait(self):
        res = self._run_with_wait_cursor(
            self._do_trace,
            process_key="trace",
            label="Cheminement en cours..."
        )
        self._autosave()
        return res

    def _open_diagnostic_with_wait(self):
        res = self._run_with_wait_cursor(
            self._open_diagnostic,
            process_key="diagnostic",
            label="Diagnostic en cours..."
        )
        self._autosave()
        return res

    def _make_report_with_wait(self):
        res = self._run_with_wait_cursor(
            self._make_report,
            process_key="report",
            label="Génération du rapport..."
        )
        # rapport ne modifie pas l'état, autosave non indispensable
        return res

    def _preview_report_with_wait(self):
        return self._run_with_wait_cursor(
            lambda: self._make_report(preview=True),
            process_key="report_preview",
            label="Prévisualisation du rapport..."
        )

    def _visit_with_wait(self):
        return self._run_with_wait_cursor(
            self._visit,
            process_key="visit",
            label="Mise à jour des visites..."
        )

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
        all_vector_layers: List[QgsVectorLayer] = []
        for c in (self.canal_combo, self.ouvr_combo, self.fosse_combo,
                  self.indus_combo, self.liaison_combo, self.astreint_combo, self.pv_combo, self.pollution_divers_combo):
            if c:  # Vérifier que le combo existe
                c.clear()

        # trouver/assurer LABEL_CI si présent
        self.label_layer = None
        self.pollution_divers_layer = None
        
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer):
                all_vector_layers.append(lyr)
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
            if self._is_pv_layer(lyr):
                self.pv_combo.addItem(lyr.name(), lyr)
            if self._is_pollution_divers_layer(lyr):
                if self.pollution_divers_combo:
                    self.pollution_divers_combo.addItem(lyr.name(), lyr)
                self.pollution_divers_layer = lyr
            
            if lyr.name() == "LABEL_CI" and isinstance(lyr, QgsVectorLayer) and lyr.isValid():
                self.label_layer = lyr
        
        # Message de confirmation si appelé manuellement (via bouton Actualiser)
        # On vérifie si on est dans le contexte d'un appel manuel (pas au démarrage)
        if hasattr(self, 'dock') and self.dock and self.dock.isVisible():
            total_layers = len(QgsProject.instance().mapLayers())
            
            msg = f"Couches actualisées !\n\n"
            msg += f"Total QGIS : {total_layers} couches\n"
            msg += f"Canalisations : {self.canal_combo.count()}\n"
            msg += f"Ouvrages : {self.ouvr_combo.count()}\n"
            msg += f"Industriels : {self.indus_combo.count()}\n"
            if self.pollution_divers_combo:
                msg += f"Pollution divers : {self.pollution_divers_combo.count()}\n"
            
            QMessageBox.information(self.iface.mainWindow(), "Actualisation des couches", msg)

        # Si LABEL_CI introuvable : créer une mémoire (sécurité)
        if not self.label_layer:
            vdef = "Point?crs=EPSG:2154&field=categorie:string&field=label:string"
            self.label_layer = QgsVectorLayer(vdef, "LABEL_CI", "memory")
            QgsProject.instance().addMapLayer(self.label_layer)

        # Fallback robuste : si la combo Pollution divers reste vide, proposer
        # les couches candidates "pollution" / "divers", puis toutes les couches point.
        if self.pollution_divers_combo and self.pollution_divers_combo.count() == 0:
            for lyr in all_vector_layers:
                nm = str(lyr.name() or "").lower()
                if ("pollution" in nm) or ("divers" in nm):
                    self.pollution_divers_combo.addItem(lyr.name(), lyr)
            if self.pollution_divers_combo.count() == 0:
                for lyr in all_vector_layers:
                    try:
                        if lyr.geometryType() == 0:  # 0 = Point
                            self.pollution_divers_combo.addItem(lyr.name(), lyr)
                    except Exception:
                        continue
            if self.pollution_divers_combo.count() == 0 and hasattr(self, 'dock') and self.dock and self.dock.isVisible():
                diag = self._diagnose_pollution_divers_layers(all_vector_layers)
                QMessageBox.warning(
                    self.iface.mainWindow(),
                    "Diagnostic couche Pollution divers",
                    "Aucune couche candidate détectée automatiquement pour 'Pollution divers'.\n\n"
                    "Diagnostic (20 premières couches vecteur):\n" + diag
                )

    def _is_pv_layer(self, layer: QgsVectorLayer) -> bool:
        """Détecte une couche PV par son nom ou sa source."""
        if not layer or not isinstance(layer, QgsVectorLayer):
            return False

        name = layer.name().lower()
        if "pv" in name or "conformite" in name or "conformité" in name or "conforme" in name:
            return True

        try:
            source = layer.dataProvider().dataSourceUri().lower()
        except Exception:
            source = ""

        return any(
            token in source
            for token in ("pv_conforme", "pv_conformite", "pv conform", "pv_conform")
        )

    def _is_pollution_divers_layer(self, layer: QgsVectorLayer) -> bool:
        """Détecte POINT_POLLUTION_DIVERS même avec variantes de nommage (espaces/underscores)."""
        if not layer or not isinstance(layer, QgsVectorLayer):
            return False
        raw = str(layer.name() or "").strip().lower()
        norm = " ".join(raw.replace("_", " ").replace("-", " ").split())
        if "point pollution divers" in norm or norm == "pollution divers":
            return True

        # Fallback robuste via source PostGIS (ex: exploit."POINT_POLLUTION_DIVERS")
        try:
            src = str(layer.dataProvider().dataSourceUri() or "").lower()
        except Exception:
            src = ""
        src_norm = src.replace('"', "").replace("'", "").replace("_", " ")
        src_norm = " ".join(src_norm.split())
        if ("point pollution divers" in src_norm) or ("exploit.point pollution divers" in src_norm):
            return True

        # Détection forte PostgreSQL/PostGIS via parsing URI
        try:
            if str(layer.providerType() or "").lower() in ("postgres", "postgis"):
                ds = QgsDataSourceUri(layer.source())
                schema = str(ds.schema() or "").strip().lower().replace('"', '')
                table = str(ds.table() or "").strip().lower().replace('"', '')
                table_norm = table.replace("_", " ").replace("-", " ")
                table_norm = " ".join(table_norm.split())
                if table == "point_pollution_divers" or table_norm == "point pollution divers":
                    return True
                if schema == "exploit" and "point pollution divers" in table_norm:
                    return True
        except Exception:
            pass
        return False

    def _diagnose_pollution_divers_layers(self, layers: List[QgsVectorLayer]) -> str:
        """Retourne une synthèse de diagnostic sur la détection Pollution divers."""
        lines = []
        for lyr in layers:
            try:
                name = lyr.name()
                provider = lyr.providerType()
                detected = self._is_pollution_divers_layer(lyr)
                src = str(lyr.source() or "")
                if len(src) > 120:
                    src = src[:117] + "..."
                lines.append(f"- [{ 'OK' if detected else 'NO' }] {name} | {provider} | {src}")
            except Exception:
                continue
        return "\n".join(lines[:20]) if lines else "Aucune couche vecteur détectée."

    # ---------------------------------------------------------
    # Onglet CHEMINEMENT
    # ---------------------------------------------------------
    def _tab_trace(self) -> QWidget:
        w = QWidget(); g = QGridLayout(w)

        self.id_input = QLineEdit()
        self.lbl_start_id = QLabel("ID ouvrage départ :")
        g.addWidget(self.lbl_start_id, 0, 0)
        g.addWidget(self.id_input, 0, 1)

        # select on map
        self.btn_sel = QPushButton("Sélection carte"); self.btn_sel.setIcon(QIcon(os.path.join(ICONS_DIR,'select.png')))
        self.btn_sel.setCheckable(True); self.btn_sel.clicked.connect(self._toggle_select)
        g.addWidget(self.btn_sel, 1, 0, 1, 2)

        # search
        self.search_input = QLineEdit()
        self.btn_search = QPushButton("Rechercher"); self.btn_search.setIcon(QIcon(os.path.join(ICONS_DIR,'filtre.png')))
        self.btn_search.clicked.connect(self._search)
        hb = QHBoxLayout(); hb.addWidget(self.search_input); hb.addWidget(self.btn_search)
        self.lbl_search = QLabel("Recherche :")
        g.addWidget(self.lbl_search, 2, 0); g.addLayout(hb, 2, 1)

        # mode + filtres
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["Amont vers Aval", "Aval vers Amont", "Cheminement Pollution"])
        self.lbl_type = QLabel("Type :")
        g.addWidget(self.lbl_type, 3, 0); g.addWidget(self.direction_combo, 3, 1)

        self.radius_combo = QComboBox()
        self.radius_combo.addItem("Tout le réseau", None)
        for txt, meters in [("500 m", 500.0), ("1 km", 1000.0), ("2 km", 2000.0),
                            ("3 km", 3000.0), ("4 km", 4000.0), ("5 km", 5000.0)]:
            self.radius_combo.addItem(txt, meters)
        self.lbl_radius = QLabel("Rayon limite :")
        g.addWidget(self.lbl_radius, 4, 0); g.addWidget(self.radius_combo, 4, 1)

        self.cat_combo = QComboBox()
        for txt,val in [("",""),("Eaux Pluviales","01"),("Eaux Usées","02"),("Unitaire","03")]:
            self.cat_combo.addItem(txt,val)
        self.lbl_category = QLabel("Catégorie :")
        g.addWidget(self.lbl_category, 5, 0); g.addWidget(self.cat_combo, 5, 1)

        self.func_combo = QComboBox()
        for txt,val in [("",""),("Transport","01"),("Collecte","02")]:
            self.func_combo.addItem(txt,val)
        self.lbl_function = QLabel("Fonction :")
        g.addWidget(self.lbl_function, 6, 0); g.addWidget(self.func_combo, 6, 1)
        
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
        g.addLayout(hb2, 8, 0, 1, 2)

        return w

    # ---------------------------------------------------------
    # Onglet VISITE-INDUS
    # ---------------------------------------------------------
    def _tab_visit_indus(self) -> QWidget:
        w = QWidget(); l = QVBoxLayout(w)

        # bloc visites
        self.box_v = QGroupBox("Visites de nœuds"); lv = QVBoxLayout(self.box_v)
        hb = QHBoxLayout()
        self.visit_input = QLineEdit(); hb.addWidget(self.visit_input)
        self.btn_pick = QPushButton(); self.btn_pick.setIcon(QIcon(os.path.join(ICONS_DIR,'select.png')))
        self.btn_pick.setCheckable(True); self.btn_pick.setToolTip("Sélectionner un nœud sur la carte")
        self.btn_pick.clicked.connect(self._toggle_visit_select); hb.addWidget(self.btn_pick)
        lv.addLayout(hb)

        self.btn_visit = QPushButton("Visiter (Pollué O/N)"); self.btn_visit.setIcon(QIcon(os.path.join(ICONS_DIR,'pollueur.png')))
        self.btn_visit.clicked.connect(self._visit_with_wait)
        lv.addWidget(self.btn_visit)
        l.addWidget(self.box_v)

        # bloc indus
        self.box_i = QGroupBox("Industriels"); li = QVBoxLayout(self.box_i)
        self.btn_show_indus = QPushButton("Afficher Indus connectés"); self.btn_show_indus.setIcon(QIcon(os.path.join(ICONS_DIR,'table.png')))
        self.btn_show_indus.clicked.connect(self._open_or_update_industrial_dock)
        li.addWidget(self.btn_show_indus)

        # note pollution (grande zone)
        self.note_text = QTextEdit(); self.note_text.setPlaceholderText("Note de pollution (si désignation)…")
        li.addWidget(self.note_text)

        self.btn_designate_ouvrage = QPushButton("Désigner Ouvrage / Pollution Divers")
        self.btn_designate_ouvrage.clicked.connect(self._designate_ouvrage_or_divers)
        li.addWidget(self.btn_designate_ouvrage)

        # rattacher astreinte
        self.btn_att = QPushButton("Rattacher Astreinte"); self.btn_att.setIcon(QIcon(os.path.join(ICONS_DIR,'attach.png')))
        self.btn_att.clicked.connect(self._attach_astreint); li.addWidget(self.btn_att)

        l.addWidget(self.box_i)
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

        self.btn_diag = QPushButton("Diagnostics"); self.btn_diag.setIcon(QIcon(os.path.join(ICONS_DIR,'table.png')))
        self.btn_diag.clicked.connect(self._open_diagnostic_with_wait); l.addWidget(self.btn_diag)

        self.btn_pdf = QPushButton("Générer PDF"); self.btn_pdf.setIcon(QIcon(os.path.join(ICONS_DIR,'report.png')))
        self.btn_pdf.clicked.connect(self._make_report_with_wait); l.addWidget(self.btn_pdf)

        self.btn_pdf_preview = QPushButton("Prévisualiser rapport")
        self.btn_pdf_preview.clicked.connect(self._preview_report_with_wait)
        l.addWidget(self.btn_pdf_preview)

        self.btn_ph = QPushButton("Ajouter Photos (+ commentaires)"); self.btn_ph.setIcon(QIcon(os.path.join(ICONS_DIR,'save.png')))
        self.btn_ph.clicked.connect(lambda: self.ph_mgr.add(self.dock)); l.addWidget(self.btn_ph)

        # masquer étiquettes
        self.btn_mask = QPushButton("Masquer/Demasquer étiquettes")
        self.btn_mask.setIcon(QIcon(os.path.join(ICONS_DIR,'filtre.png')))
        self.btn_mask.setCheckable(True); self.btn_mask.clicked.connect(self._toggle_mask_labels)
        l.addWidget(self.btn_mask)

        # save/load session
        hb = QHBoxLayout()
        self.btn_save_session = QPushButton("Sauvegarder session"); self.btn_save_session.clicked.connect(self._save_session)
        self.btn_load_session = QPushButton("Charger session");     self.btn_load_session.clicked.connect(self._load_session)
        hb.addWidget(self.btn_save_session); hb.addWidget(self.btn_load_session); l.addLayout(hb)

        # créer tables minimales
        self.btn_schema = QPushButton("Créer tables minimales"); self.btn_schema.clicked.connect(self._create_minimal_tables)
        l.addWidget(self.btn_schema)

        # reset (avec confirmation)
        self.btn_rst = QPushButton("Réinitialiser"); self.btn_rst.setIcon(QIcon(os.path.join(ICONS_DIR,'reset.png')))
        self.btn_rst.clicked.connect(self._confirm_reset); l.addWidget(self.btn_rst)
        return w

    # ---------------------------------------------------------
    # Onglet PV Conformité
    # ---------------------------------------------------------
    def _tab_pv(self) -> QWidget:
        """Crée l'onglet PV Conformité pour l'analyse industrielle"""
        self.pv_tab = PVConformiteTab(self)
        return self.pv_tab

    def _tab_settings(self) -> QWidget:
        """Crée l'onglet PARAMÉTRAGE/PARAMÈTRES selon la variante."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QT_NO_FRAME)

        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(5, 5, 5, 5)

        # === SECTION COUCHES SIG ===
        grp_layers = QGroupBox("🗺️ Sélection des couches SIG")
        grp_layers_lay = QGridLayout(grp_layers)

        self.canal_combo    = QComboBox()
        self.ouvr_combo     = QComboBox()
        self.fosse_combo    = QComboBox()
        self.indus_combo    = QComboBox()
        self.liaison_combo  = QComboBox()
        self.astreint_combo = QComboBox()
        self.pv_combo       = QComboBox()
        self.pollution_divers_combo = QComboBox()

        grp_layers_lay.addWidget(QLabel("🔵 Canalisations :"), 0, 0)
        grp_layers_lay.addWidget(self.canal_combo, 0, 1)
        grp_layers_lay.addWidget(QLabel("🔴 Ouvrages :"), 1, 0)
        grp_layers_lay.addWidget(self.ouvr_combo, 1, 1)
        grp_layers_lay.addWidget(QLabel("🌊 Cours d'eau / fossés :"), 2, 0)
        grp_layers_lay.addWidget(self.fosse_combo, 2, 1)
        grp_layers_lay.addWidget(QLabel("🏭 Industriels :"), 3, 0)
        grp_layers_lay.addWidget(self.indus_combo, 3, 1)
        grp_layers_lay.addWidget(QLabel("🔗 Liaisons Indus :"), 4, 0)
        grp_layers_lay.addWidget(self.liaison_combo, 4, 1)
        grp_layers_lay.addWidget(QLabel("⚠️ Astreinte-Exploit :"), 5, 0)
        grp_layers_lay.addWidget(self.astreint_combo, 5, 1)
        grp_layers_lay.addWidget(QLabel("🏠 PV Conformité :"), 6, 0)
        grp_layers_lay.addWidget(self.pv_combo, 6, 1)
        grp_layers_lay.addWidget(QLabel("🧪 Pollution divers :"), 7, 0)
        grp_layers_lay.addWidget(self.pollution_divers_combo, 7, 1)

        btn_refresh_layers = QPushButton("🔄 Actualiser les couches")
        btn_refresh_layers.setToolTip("Recharge la liste des couches disponibles dans QGIS")
        btn_refresh_layers.clicked.connect(self._populate_layers)
        btn_refresh_layers.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 5px; font-weight: bold; }")
        grp_layers_lay.addWidget(btn_refresh_layers, 8, 0, 1, 2)

        lay.addWidget(grp_layers)

        # === SECTION THEME & LANGUE + MODE ===
        grp_ui = QGroupBox("🎨 Thème & Langue")
        grp_ui_lay = QGridLayout(grp_ui)

        grp_ui_lay.addWidget(QLabel("Thème :"), 0, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Clair", "Sombre"])
        if self.theme_name:
            idx_theme = self.theme_combo.findText(self.theme_name)
            if idx_theme >= 0:
                self.theme_combo.setCurrentIndex(idx_theme)
        self.theme_combo.currentTextChanged.connect(self._apply_theme)
        grp_ui_lay.addWidget(self.theme_combo, 0, 1)

        grp_ui_lay.addWidget(QLabel("Langue :"), 1, 0)
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Français", "fr")
        self.lang_combo.addItem("English", "en")
        idx_lang = self.lang_combo.findData(self.language)
        if idx_lang >= 0:
            self.lang_combo.setCurrentIndex(idx_lang)
        self.lang_combo.currentIndexChanged.connect(
            lambda _: self._apply_language(self.lang_combo.currentData())
        )
        grp_ui_lay.addWidget(self.lang_combo, 1, 1)

        grp_ui_lay.addWidget(QLabel("Mode plugin :"), 2, 0)
        self.variant_combo = QComboBox()
        self.variant_combo.addItem("TRACK-EAU-POLL-LITE", "LITE")
        self.variant_combo.addItem("TRACK-EAU-POLL", "FULL")
        idx_variant = self.variant_combo.findData(self.plugin_variant)
        if idx_variant >= 0:
            self.variant_combo.setCurrentIndex(idx_variant)
        self.variant_combo.currentIndexChanged.connect(self._on_variant_changed)
        grp_ui_lay.addWidget(self.variant_combo, 2, 1)

        lay.addWidget(grp_ui)

        if self.plugin_variant == "FULL":
            # === SECTION LOGO ===
            grp_logo = QGroupBox("🖼️ Logo du plugin")
            grp_logo_lay = QVBoxLayout(grp_logo)

            self.logo_preview_label = QLabel()
            self.logo_preview_label.setFixedSize(150, 60)
            self.logo_preview_label.setScaledContents(True)
            self.logo_preview_label.setStyleSheet("border: 1px solid #ccc; background: white;")
            self._update_logo_preview()
            grp_logo_lay.addWidget(self.logo_preview_label, alignment=QT_ALIGN_CENTER)

            logo_path_lay = QHBoxLayout()
            logo_path_lay.addWidget(QLabel("Chemin du logo :"))
            self.logo_path_input = QLineEdit()
            self.logo_path_input.setPlaceholderText("Chemin vers le fichier logo (PNG, JPG)")
            self.logo_path_input.setText(self.custom_logo_path)
            self.logo_path_input.setReadOnly(True)
            logo_path_lay.addWidget(self.logo_path_input, stretch=1)

            btn_browse_logo = QPushButton("📁 Parcourir")
            btn_browse_logo.clicked.connect(self._on_browse_logo)
            logo_path_lay.addWidget(btn_browse_logo)

            btn_reset_logo = QPushButton("🔄 Réinitialiser")
            btn_reset_logo.clicked.connect(self._on_reset_logo)
            logo_path_lay.addWidget(btn_reset_logo)

            grp_logo_lay.addLayout(logo_path_lay)
            lay.addWidget(grp_logo)

            # === SECTION ICÔNE ===
            grp_icon = QGroupBox("⭐ Icône du plugin")
            grp_icon_lay = QVBoxLayout(grp_icon)

            self.icon_preview_label = QLabel()
            self.icon_preview_label.setFixedSize(48, 48)
            self.icon_preview_label.setScaledContents(True)
            self.icon_preview_label.setStyleSheet("border: 1px solid #ccc; background: white;")
            self._update_icon_preview()
            grp_icon_lay.addWidget(self.icon_preview_label, alignment=QT_ALIGN_CENTER)

            icon_path_lay = QHBoxLayout()
            icon_path_lay.addWidget(QLabel("Chemin de l'icône :"))
            self.icon_path_input = QLineEdit()
            self.icon_path_input.setPlaceholderText("Chemin vers le fichier icône (PNG, 64x64 recommandé)")
            self.icon_path_input.setText(self.custom_icon_path)
            self.icon_path_input.setReadOnly(True)
            icon_path_lay.addWidget(self.icon_path_input, stretch=1)

            btn_browse_icon = QPushButton("📁 Parcourir")
            btn_browse_icon.clicked.connect(self._on_browse_icon)
            icon_path_lay.addWidget(btn_browse_icon)

            btn_reset_icon = QPushButton("🔄 Réinitialiser")
            btn_reset_icon.clicked.connect(self._on_reset_icon)
            icon_path_lay.addWidget(btn_reset_icon)

            grp_icon_lay.addLayout(icon_path_lay)
            lay.addWidget(grp_icon)

            # === BOUTONS PARAMÈTRES ===
            btn_lay = QHBoxLayout()
            btn_lay.addStretch()

            btn_save = QPushButton("💾 Sauvegarder les paramètres")
            btn_save.clicked.connect(self._on_save_settings)
            btn_save.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 8px; font-weight: bold; }")
            btn_lay.addWidget(btn_save)

            btn_export = QPushButton("📤 Exporter les paramètres")
            btn_export.clicked.connect(self._on_export_settings)
            btn_lay.addWidget(btn_export)

            btn_import = QPushButton("📥 Importer les paramètres")
            btn_import.clicked.connect(self._on_import_settings)
            btn_lay.addWidget(btn_import)

            lay.addLayout(btn_lay)

        if self.plugin_variant == "FULL":
            grp_info = QGroupBox("ℹ️ Indications")
            info_lay = QVBoxLayout(grp_info)
            info_txt = QLabel(
                "• Les actions opérationnelles sont disponibles dans les onglets dédiés :\n"
                "  - ACTIONS (PDF, masque étiquettes, session, reset)\n"
                "  - PV (analyse conformité)\n"
                "• Cet onglet PARAMÈTRES est réservé au paramétrage (couches, thème/langue, logo, icône, mode)."
            )
            info_txt.setWordWrap(True)
            info_txt.setStyleSheet("padding: 6px;")
            info_lay.addWidget(info_txt)
            lay.addWidget(grp_info)
        else:
            # === SECTION ACTIONS (LITE uniquement) ===
            grp_actions = QGroupBox("🛠️ Actions")
            actions_lay = QVBoxLayout(grp_actions)

            self.btn_pdf = QPushButton("Générer PDF")
            self.btn_pdf.setIcon(QIcon(os.path.join(ICONS_DIR,'report.png')))
            self.btn_pdf.clicked.connect(self._make_report_with_wait)
            actions_lay.addWidget(self.btn_pdf)

            self.btn_mask = QPushButton("Masquer/Demasquer étiquettes")
            self.btn_mask.setIcon(QIcon(os.path.join(ICONS_DIR,'filtre.png')))
            self.btn_mask.setCheckable(True)
            self.btn_mask.clicked.connect(self._toggle_mask_labels)
            actions_lay.addWidget(self.btn_mask)

            hb = QHBoxLayout()
            self.btn_save_session = QPushButton("Sauvegarder session")
            self.btn_save_session.clicked.connect(self._save_session)
            self.btn_load_session = QPushButton("Charger session")
            self.btn_load_session.clicked.connect(self._load_session)
            hb.addWidget(self.btn_save_session)
            hb.addWidget(self.btn_load_session)
            actions_lay.addLayout(hb)

            self.btn_rst = QPushButton("Réinitialiser")
            self.btn_rst.setIcon(QIcon(os.path.join(ICONS_DIR,'reset.png')))
            self.btn_rst.clicked.connect(self._confirm_reset)
            actions_lay.addWidget(self.btn_rst)

            lay.addWidget(grp_actions)

        lay.addStretch()

        scroll.setWidget(w)
        return scroll

    # ---------------------------------------------------------
    # Sélection / Recherche
    # ---------------------------------------------------------
    def _toggle_select(self, checked: bool):
        if checked:
            self.ouvr_layer = self.ouvr_combo.currentData()
            if not self.ouvr_layer or not self.ouvr_layer.isValid():
                QMessageBox.warning(self.iface.mainWindow(),PLUGIN_DISPLAY_NAME,"Couche OUVRAGE invalide.")
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
                QMessageBox.warning(self.iface.mainWindow(),PLUGIN_DISPLAY_NAME,"Couche OUVRAGE invalide.")
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
            QMessageBox.warning(self.iface.mainWindow(),PLUGIN_DISPLAY_NAME,"Couche OUVRAGE invalide.")
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

    def _selected_trace_radius_m(self) -> Optional[float]:
        """Rayon maximal de cheminement en mètres (None = tout le réseau)."""
        if not self.radius_combo:
            return None
        try:
            val = self.radius_combo.currentData()
            return float(val) if val not in (None, "", 0) else None
        except Exception:
            return None

    def _build_network_fast_caches(self):
        """Construit des caches locaux pour limiter les requêtes provider répétées (terrain/réseau lent)."""
        def _sig(layer: Optional[QgsVectorLayer]) -> str:
            if not layer or not layer.isValid():
                return ""
            return layer.id()

        key = (
            _sig(self.canal_layer),
            _sig(self.fosse_layer),
            _sig(self.liaison_layer),
        )
        if self._network_cache_key == key and self._canal_nodes_by_fid is not None:
            return

        self._canal_nodes_by_fid = {}
        self._fosse_nodes_by_fid = {}
        self._liaison_fids_by_node = {}

        def _norm(v: Any) -> str:
            s = str(v or "").strip()
            return "" if not s or s.upper() == "INCONNU" else s

        if self.canal_layer and self.canal_layer.isValid():
            for f in self.canal_layer.getFeatures():
                try:
                    ini = _norm(f["idnini"])
                    term = _norm(f["idnterm"])
                    if ini or term:
                        self._canal_nodes_by_fid[f.id()] = (ini, term)
                except Exception:
                    continue

        if self.fosse_layer and self.fosse_layer.isValid():
            for f in self.fosse_layer.getFeatures():
                try:
                    ini = _norm(f["idnini"])
                    term = _norm(f["idnterm"])
                    if ini or term:
                        self._fosse_nodes_by_fid[f.id()] = (ini, term)
                except Exception:
                    continue

        if self.liaison_layer and self.liaison_layer.isValid():
            for f in self.liaison_layer.getFeatures():
                try:
                    node = _norm(f["id_ouvrage"])
                    if not node:
                        continue
                    self._liaison_fids_by_node.setdefault(node, set()).add(f.id())
                except Exception:
                    continue

        self._network_cache_key = key

    def _get_or_build_tracer(self, filters: Dict[str, str]) -> NetworkTracer:
        """Réutilise le tracer (et son graphe mémoire) tant que couches/filtres ne changent pas."""
        key = (
            self.canal_layer.id() if self.canal_layer and self.canal_layer.isValid() else "",
            self.fosse_layer.id() if self.fosse_layer and self.fosse_layer.isValid() else "",
            str((filters or {}).get("category") or "").strip(),
            str((filters or {}).get("function") or "").strip(),
        )
        if self.tracer is not None and self._tracer_key == key:
            return self.tracer
        self.tracer = NetworkTracer(
            canal_layer=self.canal_layer,
            fosse_layer=self.fosse_layer,
            field_alias=self.field_alias,
            filters=filters
        )
        self._tracer_key = key
        return self.tracer

    def _do_trace(self):
        start_id = (self.id_input.text() or "").strip()
        if not start_id:
            QMessageBox.warning(self.iface.mainWindow(),PLUGIN_DISPLAY_NAME,"Veuillez saisir un ID départ.")
            return

        # couches
        self.canal_layer   = self.canal_combo.currentData()
        self.fosse_layer   = self.fosse_combo.currentData()
        self.indus_layer   = self.indus_combo.currentData()
        self.liaison_layer = self.liaison_combo.currentData()
        self.ouvr_layer    = self.ouvr_combo.currentData()

        if not self.canal_layer or not self.ouvr_layer:
            QMessageBox.warning(self.iface.mainWindow(),PLUGIN_DISPLAY_NAME,"Sélectionnez au minimum CANALISATION et OUVRAGE.")
            return
        self._build_network_fast_caches()

        mode = self.direction_combo.currentText()
        filters = {'category': self.cat_combo.currentData() or '',
                   'function': self.func_combo.currentData() or ''}

        if mode == "Cheminement Pollution":
            self._trace_for_industrials(start_id, filters)
            self._autosave()
            return

        # Tracer réseau
        self.tracer = self._get_or_build_tracer(filters)
        downstream = (mode == "Amont vers Aval")
        canal_ids, fosse_ids = self.tracer.trace(start_id, downstream=downstream, max_distance=self._selected_trace_radius_m())

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

    def _indus_fids_from_ids_compat(self, ind_ids):
        """Retourne des FIDs industriels à partir d'IDs texte avec fallback compatibilité."""
        if not (self.indus_layer and self.indus_layer.isValid() and self.indus_svc and ind_ids):
            return []

        if hasattr(self.indus_svc, "indus_fids_from_ids"):
            return self.indus_svc.indus_fids_from_ids(set(ind_ids))

        # Fallback compatibilité ancienne classe IndustrialsService
        id_field = self.indus_svc._get_indus_id_field() if hasattr(self.indus_svc, "_get_indus_id_field") else None
        if not id_field:
            return []

        esc = lambda s: (s or "").replace("'", "''")
        values = ",".join("'{}'".format(esc(i)) for i in ind_ids if i)
        if not values:
            return []

        expr = QgsExpression("trim(\"{}\") IN ({})".format(id_field, values))
        req = QgsFeatureRequest(expr)
        return [f.id() for f in self.indus_layer.getFeatures(req)]

    def _trace_for_industrials(self, start_id: str, filters: Dict[str,str], pv_distance: float = 15.0):
        """
        Cheminement spécifique pour les industriels :
        - trace en aval→amont,
        - sélectionne les liaisons,
        - sélectionne les industriels dans la couche INDUITS,
        - détecte les PV non conformes,
        - remplit le dock industriels + PV.
        """
        if not self.canal_layer or not self.canal_layer.isValid():
            self.canal_layer = self.canal_combo.currentData() if self.canal_combo else None
        if not self.fosse_layer or not self.fosse_layer.isValid():
            self.fosse_layer = self.fosse_combo.currentData() if self.fosse_combo else None
        if not self.indus_layer or not self.indus_layer.isValid():
            self.indus_layer = self.indus_combo.currentData() if self.indus_combo else None
        if not self.liaison_layer or not self.liaison_layer.isValid():
            self.liaison_layer = self.liaison_combo.currentData() if self.liaison_combo else None
        if not self.pv_layer or not self.pv_layer.isValid():
            self.pv_layer = self.pv_combo.currentData() if self.pv_combo else None
        self._build_network_fast_caches()

        self.tracer = self._get_or_build_tracer(filters)
        # amont
        canal_ids, fosse_ids = self.tracer.trace(start_id, downstream=False, max_distance=self._selected_trace_radius_m())

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
        indus_key = (
            self.indus_layer.id() if self.indus_layer and self.indus_layer.isValid() else None,
            self.liaison_layer.id() if self.liaison_layer and self.liaison_layer.isValid() else None,
        )
        if (not self.indus_svc) or (self._indus_svc_key != indus_key):
            self.indus_svc = IndustrialsService(self.indus_layer, self.liaison_layer)
            self._indus_svc_key = indus_key

        self.indus_svc.select_liaisons_from_nodes(nodes)  # sélectionne liaisons dans la couche
        ind_ids = self.indus_svc.select_industrials_from_selected_liaisons()  # renvoie les IDs texte

        # Sélection explicite des industriels sur la carte (cache IDs->FIDs)
        if self.indus_layer and self.indus_layer.isValid():
            self.indus_layer.removeSelection()
            if ind_ids and self.indus_svc:
                fids = self._indus_fids_from_ids_compat(ind_ids)
                if fids:
                    self.indus_layer.selectByIds(fids)

        details = self.indus_svc.fetch_many(ind_ids)
        self._last_indus_data = details
        
        # PV non conformes (même pattern que les industriels)
        pv_ids = []
        self.pv_layer = self.pv_combo.currentData() if self.pv_combo else self.pv_layer
        pv_key = (
            self.pv_layer.id() if self.pv_layer and self.pv_layer.isValid() else None,
            self.canal_layer.id() if self.canal_layer and self.canal_layer.isValid() else None,
        )
        if (not self.pv_svc) or (self._pv_svc_key != pv_key):
            if self.pv_layer and self.pv_layer.isValid():
                self.pv_svc = PVService(self.pv_layer, self.canal_layer)
                self._pv_svc_key = pv_key
            else:
                self.pv_svc = None
                self._pv_svc_key = None
        
        if self.pv_svc and self.pv_layer:
            pv_ids = self.pv_svc.connected_ids_from_nodes(nodes, distance=pv_distance)
            
            # Sélection explicite des PV sur la carte
            if pv_ids:
                pv_fids = []
                id_field = None
                for field_name in ['id', 'num_pv', 'ID', 'NUM_PV']:
                    if self.pv_layer.fields().indexOf(field_name) >= 0:
                        id_field = field_name
                        break
                if id_field:
                    esc = lambda s: (s or "").replace("'", "''")
                    values = ",".join("'{}'".format(esc(str(pid))) for pid in pv_ids if pid)
                    if values:
                        expr = QgsExpression("\"{}\" IN ({})".format(id_field, values))
                        req = QgsFeatureRequest(expr)
                        pv_fids = [feat.id() for feat in self.pv_layer.getFeatures(req)]
                if pv_fids:
                    self.pv_layer.removeSelection()
                    self.pv_layer.selectByIds(pv_fids)
        
        # Récupérer les données PV
        pv_details = {}
        if self.pv_svc and pv_ids:
            pv_details = self.pv_svc.fetch_many(pv_ids)
            # Ajouter la distance au réseau pour chaque PV
            for pv_id in pv_details:
                distance = self.pv_svc.get_distance_to_network(pv_id)
                if distance is not None:
                    pv_details[pv_id]['distance'] = str(distance)
        
        self._last_pv_data = pv_details
        
        # Ouvrir le dock avec industriels + PV
        self._open_or_update_industrial_dock(data=details, pv_data=pv_details)

        # résumé
        dist = round(self.tracer.total_length, 2)
        codes = [c for c in self.tracer.flux_types if c]
        labels = sorted({ self._flux_labels.get(c, c) for c in codes }) or ["Aucun"]
        QMessageBox.information(
            self.iface.mainWindow(),
            "Cheminement Pollution",
            "Industriels : {}\nPV non conformes : {}\nLongueur : {} m\nFlux : {}".format(
                len(ind_ids), len(pv_ids), dist, " / ".join(labels)
            )
        )

    # ---------------------------------------------------------
    # Collecte de nœuds depuis des IDs sélectionnés
    # ---------------------------------------------------------
    def _collect_nodes_from_ids(self, canal_ids: List[int], fosse_ids: List[int], downstream: bool) -> Set[str]:
        nodes: Set[str] = set()
        if self._canal_nodes_by_fid and canal_ids:
            for fid in canal_ids:
                ini, term = self._canal_nodes_by_fid.get(fid, ("", ""))
                nid = term if downstream else ini
                nid2 = ini if downstream else term
                if nid:
                    nodes.add(str(nid))
                if nid2:
                    nodes.add(str(nid2))
        elif self.canal_layer and canal_ids:
            req = QgsFeatureRequest().setFilterFids(canal_ids)
            for f in self.canal_layer.getFeatures(req):
                nid = f['idnterm'] if downstream else f['idnini']
                if nid and str(nid) != 'INCONNU': nodes.add(str(nid))
                nid2 = f['idnini'] if downstream else f['idnterm']
                if nid2 and str(nid2) != 'INCONNU': nodes.add(str(nid2))

        if self._fosse_nodes_by_fid and fosse_ids:
            for fid in fosse_ids:
                ini, term = self._fosse_nodes_by_fid.get(fid, ("", ""))
                nid = term if downstream else ini
                nid2 = ini if downstream else term
                if nid:
                    nodes.add(str(nid))
                if nid2:
                    nodes.add(str(nid2))
        elif self.fosse_layer and fosse_ids:
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
        if self._liaison_fids_by_node:
            ids: Set[int] = set()
            for n in nodes:
                ids.update(self._liaison_fids_by_node.get((n or "").strip(), set()))
            if ids:
                self.liaison_layer.selectByIds(sorted(ids))
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
        # Prépare les caches locaux de nœuds pour éviter des requêtes provider répétées.
        self._build_network_fast_caches()

        # Initialiser l'optimiseur (et n'invalider que si couches changées)
        node_ops_key = (
            self.canal_layer.id() if self.canal_layer and self.canal_layer.isValid() else None,
            self.fosse_layer.id() if self.fosse_layer and self.fosse_layer.isValid() else None,
            self.liaison_layer.id() if self.liaison_layer and self.liaison_layer.isValid() else None,
            self.indus_layer.id() if self.indus_layer and self.indus_layer.isValid() else None,
        )
        if not self._node_ops:
            self._node_ops = OptimizedNodeOps(
                self.canal_layer, self.fosse_layer,
                self.liaison_layer, self.indus_layer
            )
            self._node_ops_key = node_ops_key
        else:
            self._node_ops.canal_layer = self.canal_layer
            self._node_ops.fosse_layer = self.fosse_layer
            self._node_ops.liaison_layer = self.liaison_layer
            self._node_ops.indus_layer = self.indus_layer
            if self._node_ops_key != node_ops_key:
                self._node_ops.invalidate_caches()
                self._node_ops_key = node_ops_key

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

        # 2) Branches AMONT du nœud (canal/fosse) + liaisons au nœud (caches)
        branches: List[Tuple[str,int,Optional[str],Optional[str]]] = []
        incoming_cache = self._node_ops.build_incoming_cache() if self._node_ops else {}
        for typ, _lyr, feat in incoming_cache.get(node_id, []):
            try:
                amont = feat['idnini']
            except Exception:
                amont = None
            branches.append((typ, feat.id(), amont, None))

        if self._node_ops:
            liaison_cache = self._node_ops.build_liaison_cache()
            for lf in liaison_cache.get(node_id, []):
                try:
                    iid = lf['id_industriel']
                except Exception:
                    iid = None
                branches.append(("liaison", lf.id(), None, iid))

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
                    info = QLabel("Astuce: vous pouvez déplacer/zoomer la carte pendant cette sélection.")
                    info.setWordWrap(True)
                    v.addWidget(info)
                    for typ,fid,amont,indus in branches:
                        label = "Conserver {} id={}".format(typ.upper(), fid)
                        if amont: label += " (amont={})".format(amont)
                        if indus: label += " (indus={})".format(indus)
                        cb = QCheckBox(label); cb.setChecked(False)
                        v.addWidget(cb); checks.append((cb,typ,fid,amont,indus))
                    h = QHBoxLayout(); ok = QPushButton("OK"); cancel = QPushButton("Annuler")
                    ok.clicked.connect(dlg.accept); cancel.clicked.connect(dlg.reject)
                    h.addWidget(ok); h.addWidget(cancel); v.addLayout(h)
                    dlg.setModal(False)
                    dlg.setWindowModality(Qt.NonModal)
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
            sel_c_keep, sel_f_keep = self._selected_id_sets()
            for typ, fid, amont, _ in branches:
                if fid not in chosen_keep:
                    continue
                if typ == "canal":
                    keep_cids.add(fid)
                elif typ == "fosse":
                    keep_fids.add(fid)
                # Remonter sur la sélection à partir de l'amont de la branche cochée - VERSION OPTIMISÉE
                if amont:
                    kc, kf, kn = self._node_ops.walk_upstream_on_selected_optimized(amont, sel_c_keep, sel_f_keep)
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
                if not ids:
                    return out
                # Fast-path: caches locaux (évite un aller provider sur gros graphes)
                if layer is self.canal_layer and self._canal_nodes_by_fid:
                    for fid in ids:
                        ini, term = self._canal_nodes_by_fid.get(fid, ("", ""))
                        if ini:
                            out.add(str(ini))
                        if term:
                            out.add(str(term))
                    return out
                if layer is self.fosse_layer and self._fosse_nodes_by_fid:
                    for fid in ids:
                        ini, term = self._fosse_nodes_by_fid.get(fid, ("", ""))
                        if ini:
                            out.add(str(ini))
                        if term:
                            out.add(str(term))
                    return out
                if not layer:
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

        # 6) Synchroniser les tableaux indus/PV avec les sélections restantes
        current_nodes = self._current_selected_nodes()
        self._last_trace_nodes = current_nodes
        self._refresh_indus_and_pv_from_nodes(current_nodes)

        if self.label_layer:
            self._toggle_mask_labels(True)

        self.canvas.refresh()
        self._autosave()

    # ---------------------------------------------------------
    # Récupération des PV connectés à des nœuds (NOUVEAU v1.2.3)
    # ---------------------------------------------------------
    def _get_pv_from_nodes(self, nodes: Set[str]) -> List[str]:
        """Retourne les IDs des PV non conformes proches des nœuds fournis."""
        if not nodes:
            return []
        self.pv_layer = self.pv_combo.currentData() if self.pv_combo else self.pv_layer
        pv_key = (
            self.pv_layer.id() if self.pv_layer and self.pv_layer.isValid() else None,
            self.canal_layer.id() if self.canal_layer and self.canal_layer.isValid() else None,
        )
        if (not self.pv_svc) or (self._pv_svc_key != pv_key):
            if self.pv_layer and self.pv_layer.isValid():
                self.pv_svc = PVService(self.pv_layer, self.canal_layer)
                self._pv_svc_key = pv_key
            else:
                self.pv_svc = None
                self._pv_svc_key = None
        if not self.pv_svc:
            return []
        return self.pv_svc.connected_ids_from_nodes(set(nodes), distance=15.0)

    def _get_ouvrage_z_by_id(self, node_id: str) -> Optional[float]:
        """Retourne Z (fil d'eau/radier) depuis la couche Ouvrages."""
        if not node_id:
            return None
        if node_id in self._ouvrage_z_cache:
            return self._ouvrage_z_cache[node_id]
        if not self.ouvr_layer or not self.ouvr_layer.isValid():
            self.ouvr_layer = self.ouvr_combo.currentData() if self.ouvr_combo else None
        if not self.ouvr_layer or not self.ouvr_layer.isValid():
            return None
        expr = QgsExpression("trim(\"idouvrage\") = '{}'".format(str(node_id).replace("'", "''")))
        for f in self.ouvr_layer.getFeatures(QgsFeatureRequest(expr)):
            if f.fields().indexOf("z") >= 0:
                try:
                    val = float(f["z"])
                    self._ouvrage_z_cache[node_id] = val
                    return val
                except Exception:
                    return None
        return None
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
        if state == QT_CHECKED:
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
        nodes = self._current_selected_nodes()
        if nodes:
            self._last_trace_nodes = nodes
        elif self._last_trace_nodes:
            nodes = self._last_trace_nodes
        self._refresh_indus_and_pv_from_nodes(nodes)

    def _current_selected_nodes(self) -> Set[str]:
        sel_c, sel_f = self._selected_id_sets()
        if not sel_c and not sel_f:
            return set()
        return self._collect_nodes_from_ids(list(sel_c), list(sel_f), downstream=True)

    def _refresh_indus_and_pv_from_nodes(self, nodes: Set[str], pv_distance: Optional[float] = None):
        if not nodes:
            if self.indus_layer and self.indus_layer.isValid():
                self.indus_layer.removeSelection()
            if not self.pv_layer or not self.pv_layer.isValid():
                self.pv_layer = self.pv_combo.currentData() if self.pv_combo else None
            if self.pv_layer and self.pv_layer.isValid():
                self.pv_layer.removeSelection()
            self._last_indus_data = {}
            self._last_pv_data = {}
            if self.industrial_dock:
                self.industrial_dock.set_data({})
                if hasattr(self.industrial_dock, "set_pv_data"):
                    self.industrial_dock.set_pv_data([])
            if self.pv_tab and hasattr(self.pv_tab, "set_pv_data"):
                self.pv_tab.set_pv_data({})
            return

        self.indus_layer = self.indus_combo.currentData() if self.indus_combo else self.indus_layer
        self.liaison_layer = self.liaison_combo.currentData() if self.liaison_combo else self.liaison_layer
        indus_key = (
            self.indus_layer.id() if self.indus_layer and self.indus_layer.isValid() else None,
            self.liaison_layer.id() if self.liaison_layer and self.liaison_layer.isValid() else None,
        )
        if (not self.indus_svc) or (self._indus_svc_key != indus_key):
            self.indus_svc = IndustrialsService(self.indus_layer, self.liaison_layer)
            self._indus_svc_key = indus_key

        indus_ids = self.indus_svc.connected_ids_from_nodes(nodes) if self.indus_svc else []
        indus_details = self.indus_svc.fetch_many(indus_ids) if self.indus_svc else {}

        if self.indus_layer and self.indus_layer.isValid():
            self.indus_layer.removeSelection()
            if indus_ids and self.indus_svc:
                fids = self._indus_fids_from_ids_compat(indus_ids)
                if fids:
                    self.indus_layer.selectByIds(fids)

        if pv_distance is None:
            pv_distance = float(self.pv_tab.distance_spin.value()) if self.pv_tab and hasattr(self.pv_tab, "distance_spin") else 15.0

        self.pv_layer = self.pv_combo.currentData() if self.pv_combo else self.pv_layer
        pv_key = (
            self.pv_layer.id() if self.pv_layer and self.pv_layer.isValid() else None,
            self.canal_layer.id() if self.canal_layer and self.canal_layer.isValid() else None,
        )
        if (not self.pv_svc) or (self._pv_svc_key != pv_key):
            if self.pv_layer and self.pv_layer.isValid():
                self.pv_svc = PVService(self.pv_layer, self.canal_layer)
                self._pv_svc_key = pv_key
            else:
                self.pv_svc = None
                self._pv_svc_key = None

        pv_ids = []
        if self.pv_svc and self.pv_layer and self.pv_layer.isValid():
            pv_ids = self.pv_svc.connected_ids_from_nodes(nodes, distance=pv_distance)

            self.pv_layer.removeSelection()
            if pv_ids:
                id_field = None
                for field_name in ['id', 'num_pv', 'ID', 'NUM_PV']:
                    if self.pv_layer.fields().indexOf(field_name) >= 0:
                        id_field = field_name
                        break
                if id_field:
                    esc = lambda s: (s or "").replace("'", "''")
                    values = ",".join("'{}'".format(esc(str(pid))) for pid in pv_ids if pid)
                    if values:
                        expr = QgsExpression("\"{}\" IN ({})".format(id_field, values))
                        req = QgsFeatureRequest(expr)
                        pv_fids = [feat.id() for feat in self.pv_layer.getFeatures(req)]
                        if pv_fids:
                            self.pv_layer.selectByIds(pv_fids)

        pv_details = {}
        if self.pv_svc and pv_ids:
            pv_details = self.pv_svc.fetch_many(pv_ids)
            for pv_id in pv_details:
                distance = self.pv_svc.get_distance_to_network(pv_id)
                if distance is not None:
                    pv_details[pv_id]['distance'] = str(distance)

        self._last_indus_data = indus_details
        self._last_pv_data = pv_details

        if self.industrial_dock:
            self.industrial_dock.set_data(indus_details)
            if hasattr(self.industrial_dock, "set_pv_data"):
                self.industrial_dock.set_pv_data(list(pv_details.values()))
        if self.pv_tab and hasattr(self.pv_tab, "set_pv_data"):
            self.pv_tab.set_pv_data(pv_details)

    def _open_or_update_industrial_dock(self, data: Optional[Dict[str,Dict[str,str]]] = None, 
                                         pv_data: Optional[Dict[str,Dict[str,str]]] = None):
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
        
        # Gérer les données PV
        if pv_data is None:
            pv_data = self._last_pv_data if hasattr(self, '_last_pv_data') else {}
        
        if not self.industrial_dock:
            from ..gui.industrial_dock_v2 import IndustrialDockV2
            self.industrial_dock = IndustrialDockV2(self.iface.mainWindow())
            # Callbacks industriels
            self.industrial_dock.on_zoom_indus_request(self._zoom_to_industrial)
            self.industrial_dock.on_designate_indus_request(self._designate_industrial)
            self.industrial_dock.on_zoom_pv_request(self._zoom_to_pv)
            self.industrial_dock.on_designate_pv_request(self._designate_pv)
            # Callback refresh
            self.industrial_dock.on_refresh_request(self._refresh_industrial_dock_data)
            self.iface.addDockWidget(QT_RIGHT_DOCK_WIDGET_AREA, self.industrial_dock)

        self.industrial_dock.set_data(data)
        
        # Définir les données PV si le dock supporte cette méthode
        if pv_data and hasattr(self.industrial_dock, 'set_pv_data'):
            if isinstance(pv_data, dict):
                self.industrial_dock.set_pv_data(list(pv_data.values()))
            else:
                self.industrial_dock.set_pv_data(pv_data)
        
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

    def _zoom_to_pv(self, pv_id: str):
        if not self.pv_layer or not self.pv_layer.isValid():
            return

        for field_name in ['id', 'num_pv', 'ID', 'NUM_PV']:
            if self.pv_layer.fields().indexOf(field_name) >= 0:
                expr = QgsExpression("\"{}\" = '{}'".format(
                    field_name,
                    str(pv_id).replace("'", "''")
                ))
                for feat in self.pv_layer.getFeatures(QgsFeatureRequest(expr)):
                    geom = feat.geometry()
                    if geom:
                        try:
                            layer_crs = self.pv_layer.crs()
                            canvas_crs = self.canvas.mapSettings().destinationCrs()
                            if layer_crs != canvas_crs:
                                transform = QgsCoordinateTransform(
                                    layer_crs, canvas_crs, QgsProject.instance()
                                )
                                geom = QgsGeometry(geom)
                                geom.transform(transform)
                        except Exception:
                            pass
                        self.canvas.setExtent(geom.boundingBox())
                        self.canvas.refresh()
                        return

    def _ensure_pollution_divers_layer(self) -> Optional[QgsVectorLayer]:
        """Retourne une couche point de pollution divers (existante ou mémoire)."""
        if self.pollution_divers_layer and self.pollution_divers_layer.isValid():
            return self.pollution_divers_layer
        if self.pollution_divers_combo and self.pollution_divers_combo.currentData():
            lyr = self.pollution_divers_combo.currentData()
            if isinstance(lyr, QgsVectorLayer) and lyr.isValid():
                self.pollution_divers_layer = lyr
                return lyr

        for lyr in QgsProject.instance().mapLayers().values():
            try:
                if self._is_pollution_divers_layer(lyr):
                    self.pollution_divers_layer = lyr
                    return lyr
            except Exception:
                continue

        QMessageBox.warning(
            self.iface.mainWindow(),
            "POINT_POLLUTION_DIVERS",
            "La couche POINT_POLLUTION_DIVERS doit être chargée depuis votre base SIG avant la désignation."
        )
        return None

    def _record_pollution_history(self, source_type: str, source_id: str, categorie: str, details: str, geom: Optional[QgsGeometry]):
        """Enregistre un historique dans la couche POINT_POLLUTION_DIVERS (base SIG)."""
        layer = self._ensure_pollution_divers_layer()
        if not layer or not layer.isValid() or not geom:
            return None

        ff = QgsFeature(layer.fields())
        ff.setGeometry(geom)
        if layer.fields().indexOf("source_type") >= 0:
            ff.setAttribute("source_type", source_type)
        if layer.fields().indexOf("idouvrage") >= 0:
            ff.setAttribute("idouvrage", source_id)
        if layer.fields().indexOf("categorie") >= 0:
            ff.setAttribute("categorie", categorie)
        if layer.fields().indexOf("details") >= 0:
            ff.setAttribute("details", details)
        if layer.fields().indexOf("date_saisie") >= 0:
            ff.setAttribute("date_saisie", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ok, feats = layer.dataProvider().addFeatures([ff])
        layer.triggerRepaint()
        if ok and feats:
            return feats[0].id()
        return None

    def _record_pollution_divers_entry(self, payload: Dict[str, Any], geom: Optional[QgsGeometry]):
        """Crée une entrée POLLUTION_DIVERS avec mapping souple des champs PostGIS."""
        layer = self._ensure_pollution_divers_layer()
        if not layer or not layer.isValid() or not geom:
            return None

        ff = QgsFeature(layer.fields())
        ff.setGeometry(geom)

        aliases = {
            "type_pollution": ["type_pollution", "type", "categorie"],
            "description": ["description", "details"],
            "date_observation": ["date_observation", "date_obs", "date_saisie"],
            "observateur": ["observateur", "agent", "saisi_par"],
            "gravite": ["gravite", "criticite", "niveau"],
            "commentaire": ["commentaire", "comment", "notes"],
            "photo": ["photo", "photo_path", "image"],
            "source_type": ["source_type"],
            "idouvrage": ["idouvrage", "id_ouvrage"],
        }
        for key, names in aliases.items():
            value = payload.get(key, "")
            for field_name in names:
                if layer.fields().indexOf(field_name) >= 0:
                    ff.setAttribute(field_name, value)
                    break

        ok, feats = layer.dataProvider().addFeatures([ff])
        layer.triggerRepaint()
        if ok and feats:
            return feats[0].id()
        return None

    def _get_pollution_divers_feature_by_fid(self, fid_text: str) -> Optional[QgsFeature]:
        layer = self._ensure_pollution_divers_layer()
        if not layer or not layer.isValid():
            return None
        try:
            fid = int(str(fid_text).strip())
        except Exception:
            return None
        try:
            feat = layer.getFeature(fid)
            return feat if feat and feat.isValid() else None
        except Exception:
            return None

    def _pollution_divers_report_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise les infos pollution divers pour affichage tableau PDF."""
        return {
            "id": data.get("id", data.get("fid", self.polluter_id)),
            "type_pollution": data.get("type_pollution", data.get("categorie", "")),
            "description": data.get("description", data.get("details", "")),
            "date_observation": data.get("date_observation", data.get("date_obs", data.get("date_saisie", ""))),
            "observateur": data.get("observateur", data.get("agent", data.get("saisi_par", ""))),
            "gravite": data.get("gravite", data.get("criticite", data.get("niveau", ""))),
            "commentaire": data.get("commentaire", data.get("comment", data.get("notes", data.get("details", "")))),
            "photo": data.get("photo", data.get("photo_path", data.get("image", ""))),
        }

    def _choose_nearest_ouvrage_from_point(self, pt: QgsPointXY) -> Optional[str]:
        """Laisse l'utilisateur choisir l'ouvrage le plus proche d'un point."""
        if not self.ouvr_layer or not self.ouvr_layer.isValid() or not pt:
            return None

        idx = QgsSpatialIndex(self.ouvr_layer.getFeatures())
        near = idx.nearestNeighbor(pt, 8)
        if not near:
            return None

        candidates = []
        for feat in self.ouvr_layer.getFeatures(QgsFeatureRequest().setFilterFids(near)):
            oid = str(feat["idouvrage"]).strip() if "idouvrage" in feat.fields().names() else ""
            if oid:
                candidates.append(oid)
        if not candidates:
            return None

        choice, ok = QInputDialog.getItem(
            self.iface.mainWindow(),
            "Choix ouvrage proche",
            "Sélectionnez l'ouvrage le plus proche du point créé :",
            candidates,
            0,
            False,
        )
        return str(choice).strip() if ok and choice else None

    def _designate_ouvrage_or_divers(self):
        """Désigne un ouvrage ou crée un point pollution divers puis déclenche le traçage aval."""
        if (self.direction_combo.currentText() or "") != "Cheminement Pollution":
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Mode requis",
                "La désignation d'ouvrage/pollution divers est disponible uniquement en mode 'Cheminement Pollution'."
            )
            return
        if (self.polluter_type or "").upper() in ("INDUS", "PV"):
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Origine déjà définie",
                "Cette action est réservée aux pollutions non liées à un industriel ou à un PV."
            )
            return
        if not self.ouvr_layer or not self.ouvr_layer.isValid():
            self.ouvr_layer = self.ouvr_combo.currentData() if self.ouvr_combo else None

        category_options = ["dépôt sauvage", "hydrocarbures", "pollution accidentelle", "eaux chargées", "déchets solides", "autre"]
        gravite_options = ["faible", "moyenne", "forte"]

        dlg = QDialog(self.iface.mainWindow())
        dlg.setWindowTitle("Désignation pollution divers")
        lv = QVBoxLayout(dlg)

        lv.addWidget(QLabel("Mode de désignation :"))
        mode_combo = QComboBox()
        mode_combo.addItem("Désigner un ouvrage", "OUVRAGE")
        mode_combo.addItem("Créer un point pollution (clic carte)", "POINT")
        lv.addWidget(mode_combo)

        form = QFormLayout()
        cb_cat = QComboBox(); [cb_cat.addItem(c) for c in category_options]
        form.addRow("Type de pollution*", cb_cat)
        edit_desc = QLineEdit()
        form.addRow("Description*", edit_desc)
        date_obs = QDateEdit()
        date_obs.setCalendarPopup(True)
        date_obs.setDate(QDate.currentDate())
        form.addRow("Date observation*", date_obs)
        edit_observateur = QLineEdit()
        form.addRow("Observateur*", edit_observateur)
        cb_gravite = QComboBox(); [cb_gravite.addItem(g) for g in gravite_options]
        form.addRow("Gravité*", cb_gravite)
        edit_photo = QLineEdit()
        edit_photo.setPlaceholderText("Chemin photo (optionnel)")
        form.addRow("Photo", edit_photo)
        txt = QTextEdit(); txt.setPlaceholderText("Commentaire / contexte opérationnel")
        form.addRow("Commentaire", txt)
        lv.addLayout(form)

        hb = QHBoxLayout(); b_ok = QPushButton("Valider"); b_cancel = QPushButton("Annuler")
        hb.addWidget(b_ok); hb.addWidget(b_cancel); lv.addLayout(hb)
        b_ok.clicked.connect(dlg.accept); b_cancel.clicked.connect(dlg.reject)
        if dlg.exec_() != QDialog.Accepted:
            return

        mode = mode_combo.currentData()
        type_pollution = cb_cat.currentText().strip()
        description = (edit_desc.text() or "").strip()
        date_observation = date_obs.date().toString("yyyy-MM-dd")
        observateur = (edit_observateur.text() or "").strip()
        gravite = cb_gravite.currentText().strip()
        commentaire = (txt.toPlainText() or "").strip()
        photo = (edit_photo.text() or "").strip()
        if not (type_pollution and description and observateur and gravite):
            QMessageBox.warning(self.iface.mainWindow(), "Champs obligatoires", "Veuillez renseigner tous les champs marqués *.")
            return

        if mode == "OUVRAGE":
            oid = (self.visit_input.text() if self.visit_input else "") or (self.id_input.text() if self.id_input else "")
            oid = str(oid).strip()
            if not oid:
                QMessageBox.warning(self.iface.mainWindow(), "Ouvrage", "Saisissez ou sélectionnez un ID ouvrage.")
                return
            feat = None
            if self.ouvr_layer and self.ouvr_layer.isValid():
                expr = QgsExpression("trim(\"idouvrage\") = '{}'".format(oid.replace("'", "''")))
                for f in self.ouvr_layer.getFeatures(QgsFeatureRequest(expr)):
                    feat = f
                    break
            if not feat or not feat.geometry():
                QMessageBox.warning(self.iface.mainWindow(), "Ouvrage", "Ouvrage introuvable dans la couche sélectionnée.")
                return

            geom = feat.geometry()
            try:
                pt = geom.asPoint()
            except Exception:
                pt = geom.centroid().asPoint() if geom else None
            if not pt:
                return
            pgeom = QgsGeometry.fromPointXY(QgsPointXY(pt.x(), pt.y()))

            payload = {
                "source_type": "OUVRAGE",
                "idouvrage": oid,
                "type_pollution": type_pollution,
                "description": description,
                "date_observation": date_observation,
                "observateur": observateur,
                "gravite": gravite,
                "commentaire": commentaire,
                "photo": photo,
            }
            self._record_pollution_divers_entry(payload, pgeom)
            self.polluter_id = oid
            self.polluter_type = "OUVRAGE"
            self.polluter_note = commentaire
            self.polluter_details = dict(payload)
            self.polluter_details["id"] = oid
            if self.label_layer:
                self._toggle_mask_labels(True)

            self._trace_downstream_from_nodes([oid], network_choice="BOTH")
            QMessageBox.information(self.iface.mainWindow(), "Pollution divers", "Ouvrage désigné et cheminement Amont→Aval déclenché.")
            return

        # Mode POINT : clic carte
        layer = self._ensure_pollution_divers_layer()
        if not layer or not layer.isValid():
            return

        QMessageBox.information(
            self.iface.mainWindow(),
            "Point pollution",
            "Cliquez sur la carte pour créer le point de pollution, puis choisissez l'ouvrage le plus proche."
        )

        tool = QgsMapToolEmitPoint(self.canvas)
        self._pollution_point_tool = tool

        def _on_canvas_click(pt, button=None):
            try:
                self.canvas.unsetMapTool(tool)
            except Exception:
                pass

            pgeom = QgsGeometry.fromPointXY(QgsPointXY(pt.x(), pt.y()))
            oid = self._choose_nearest_ouvrage_from_point(QgsPointXY(pt.x(), pt.y()))
            if not oid:
                QMessageBox.warning(self.iface.mainWindow(), "Point pollution", "Aucun ouvrage sélectionné.")
                return

            payload = {
                "source_type": "POINT",
                "idouvrage": oid,
                "type_pollution": type_pollution,
                "description": description,
                "date_observation": date_observation,
                "observateur": observateur,
                "gravite": gravite,
                "commentaire": commentaire,
                "photo": photo,
            }
            new_fid = self._record_pollution_divers_entry(payload, pgeom)
            self.polluter_id = str(new_fid) if new_fid is not None else ""
            self.polluter_type = "POLLUTION_DIVERS"
            self.polluter_note = commentaire
            self.polluter_details = dict(payload)
            self.polluter_details["id"] = self.polluter_id
            if self.label_layer:
                self._toggle_mask_labels(True)

            self._trace_downstream_from_nodes([oid], network_choice="BOTH")
            QMessageBox.information(self.iface.mainWindow(), "Point pollution", "Point créé, enregistré et cheminement lancé.")

        tool.canvasClicked.connect(_on_canvas_click)
        self.canvas.setMapTool(tool)

    def _designate_pv(self, pv_id: str):
        """Désigne un PV comme pollueur."""
        self.polluter_id = str(pv_id)
        self.polluter_type = "PV"
        self.polluter_note = (self.note_text.toPlainText() or "").strip() if self.note_text else ""
        self.polluter_details = {}
        if self.pv_layer and self.pv_layer.isValid():
            for field_name in ('id', 'num_pv', 'ID', 'NUM_PV'):
                if self.pv_layer.fields().indexOf(field_name) >= 0:
                    expr_h = QgsExpression("trim(\"{}\") = '{}'".format(field_name, str(pv_id).replace("'", "''")))
                    for pf in self.pv_layer.getFeatures(QgsFeatureRequest(expr_h)):
                        g = pf.geometry()
                        if g:
                            try:
                                hpt = g.asPoint()
                            except Exception:
                                hpt = g.centroid().asPoint() if g else None
                            if hpt:
                                self._record_pollution_history("PV", str(pv_id), "PV", self.polluter_note, QgsGeometry.fromPointXY(QgsPointXY(hpt.x(), hpt.y())))
                        break
                    break
        if self.label_layer:
            self._toggle_mask_labels(True)
        choice = self._ask_pv_trace_network()
        if not choice:
            return

        if choice == "SELECT":
            if not self.ouvr_layer or not self.ouvr_layer.isValid():
                self.ouvr_layer = self.ouvr_combo.currentData() if self.ouvr_combo else None
            if not self.ouvr_layer or not self.ouvr_layer.isValid():
                QMessageBox.warning(
                    self.iface.mainWindow(),
                    "Ouvrages manquants",
                    "Veuillez sélectionner une couche d'ouvrages valide."
                )
                return
            sel = self.ouvr_layer.selectedFeatures()
            if not sel:
                QMessageBox.information(
                    self.iface.mainWindow(),
                    "Sélection nécessaire",
                    "Sélectionnez un ou plusieurs ouvrages sur la carte."
                )
                return
            start_nodes = []
            for f in sel:
                try:
                    start_nodes.append(str(f["idouvrage"]))
                except Exception:
                    continue
            self._trace_downstream_from_nodes(start_nodes, network_choice="BOTH")
            return

        self._trace_from_pv(pv_id, choice)

        QMessageBox.information(
            self.iface.mainWindow(),
            "PV désigné",
            f"Le PV {pv_id} a été désigné comme origine de pollution."
        )

    def _ask_pv_trace_network(self) -> Optional[str]:
        """Demande le réseau à tracer pour un PV désigné."""
        dlg = QDialog(self.iface.mainWindow())
        dlg.setWindowTitle("Cheminement depuis le PV")

        v = QVBoxLayout(dlg)
        lab = QLabel(
            "Quel(s) réseau(x) cheminer en Amont → Aval depuis le PV ?"
        )
        lab.setWordWrap(True)
        v.addWidget(lab)

        rb_ep = QRadioButton("Réseau EP (01) uniquement")
        rb_eu = QRadioButton("Réseau EU (02) uniquement")
        rb_both = QRadioButton("Réseaux EP + EU")
        rb_select = QRadioButton("Sélectionner des ouvrages")
        rb_both.setChecked(True)

        v.addWidget(rb_ep)
        v.addWidget(rb_eu)
        v.addWidget(rb_both)
        v.addWidget(rb_select)

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

        if rb_select.isChecked():
            return "SELECT"
        if rb_ep.isChecked():
            return "EP"
        if rb_eu.isChecked():
            return "EU"
        return "BOTH"

    def _trace_from_pv(self, pv_id: str, network_choice: str):
        """Trace le réseau aval à partir du PV."""
        if not self.pv_layer or not self.pv_layer.isValid():
            self.pv_layer = self.pv_combo.currentData() if self.pv_combo else None
        if not self.canal_layer or not self.canal_layer.isValid():
            self.canal_layer = self.canal_combo.currentData() if self.canal_combo else None

        if not self.pv_layer or not self.canal_layer:
            return

        pv_geom = None
        for field_name in ['id', 'num_pv', 'ID', 'NUM_PV']:
            if self.pv_layer.fields().indexOf(field_name) >= 0:
                expr = QgsExpression("\"{}\" = '{}'".format(
                    field_name,
                    str(pv_id).replace("'", "''")
                ))
                for feat in self.pv_layer.getFeatures(QgsFeatureRequest(expr)):
                    pv_geom = feat.geometry()
                    break
            if pv_geom:
                break

        if not pv_geom:
            return

        try:
            layer_crs = self.pv_layer.crs()
            canal_crs = self.canal_layer.crs()
            if layer_crs != canal_crs:
                transform = QgsCoordinateTransform(layer_crs, canal_crs, QgsProject.instance())
                pv_geom = QgsGeometry(pv_geom)
                pv_geom.transform(transform)
        except Exception:
            pass

        index = QgsSpatialIndex(self.canal_layer.getFeatures())
        try:
            pv_point = pv_geom.asPoint()
        except Exception:
            pv_point = pv_geom.centroid().asPoint() if pv_geom else None
        if not pv_point:
            return
        nearest = index.nearestNeighbor(pv_point, 5)
        start_nodes = []
        for fid in nearest:
            for feat in self.canal_layer.getFeatures(QgsFeatureRequest().setFilterFids([fid])):
                typ = str(feat["typreseau"] or "").strip()
                if network_choice == "EP" and typ not in ("01", "EP"):
                    continue
                if network_choice == "EU" and typ not in ("02", "EU"):
                    continue
                for field_name in ("idnini", "idnterm"):
                    node = str(feat[field_name]) if field_name in feat.fields().names() else ""
                    if node and node != "INCONNU":
                        start_nodes.append(node)
                if start_nodes:
                    break
            if start_nodes:
                break

        self._trace_downstream_from_nodes(start_nodes, network_choice=network_choice)

    def _trace_downstream_from_nodes(self, start_nodes: List[str], network_choice: str):
        """Trace aval à partir d'une liste de nœuds."""
        if not start_nodes:
            return

        filters = {"category": "", "function": ""}
        if network_choice == "EU":
            filters["category"] = "02"
        elif network_choice == "EP":
            filters["category"] = "01"
        elif network_choice == "Unitaire":
            filters["category"] = "03"

        self.tracer = NetworkTracer(
            canal_layer=self.canal_layer,
            fosse_layer=self.fosse_layer,
            field_alias=self.field_alias,
            filters=filters
        )

        try:
            canal_ids, fosse_ids = self.tracer.trace_multi_source(
                start_ids=list(dict.fromkeys(start_nodes)),
                downstream=True,
                max_distance=self._selected_trace_radius_m()
            )
            canal_ids_all = set(canal_ids)
            fosse_ids_all = set(fosse_ids)
        except Exception:
            canal_ids_all = set()
            fosse_ids_all = set()
            for node_id in start_nodes:
                canal_ids, fosse_ids = self.tracer.trace(node_id, downstream=True, max_distance=self._selected_trace_radius_m())
                canal_ids_all.update(canal_ids)
                fosse_ids_all.update(fosse_ids)

        if self.canal_layer:
            self.canal_layer.removeSelection()
            if canal_ids_all:
                self.canal_layer.selectByIds(list(canal_ids_all))
        if self.fosse_layer and self.fosse_layer.isValid():
            self.fosse_layer.removeSelection()
            if fosse_ids_all:
                self.fosse_layer.selectByIds(list(fosse_ids_all))

        self._last_trace_nodes = self._collect_nodes_from_ids(
            list(canal_ids_all), list(fosse_ids_all), downstream=True
        )

        dist = round(self.tracer.total_length, 2)
        codes = [c for c in self.tracer.flux_types if c]
        labels = sorted({self._flux_labels.get(c, c) for c in codes}) or ["Aucun"]
        QMessageBox.information(
            self.iface.mainWindow(),
            "Cheminement depuis PV",
            "Longueur : {} m\nFlux : {}".format(dist, " / ".join(labels))
        )

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
        self.polluter_type = "INDUS"
        self.polluter_details = {}
        if self.indus_layer and self.indus_layer.isValid():
            expr_h = QgsExpression("trim(\"id\") = '{}'".format(ind_id.replace("'", "''")))
            for inf in self.indus_layer.getFeatures(QgsFeatureRequest(expr_h)):
                g = inf.geometry()
                if g:
                    try:
                        hpt = g.asPoint()
                    except Exception:
                        hpt = g.centroid().asPoint() if g else None
                    if hpt:
                        self._record_pollution_history("INDUS", ind_id, "Industriel", self.polluter_note, QgsGeometry.fromPointXY(QgsPointXY(hpt.x(), hpt.y())))
                break
        if self.label_layer:
            self._toggle_mask_labels(True)

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
                PLUGIN_DISPLAY_NAME,
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
                PLUGIN_DISPLAY_NAME,
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
                    PLUGIN_DISPLAY_NAME,
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
            QMessageBox.warning(self.iface.mainWindow(), PLUGIN_DISPLAY_NAME, "Couche ASTREINTE invalide.")
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
            QMessageBox.warning(self.iface.mainWindow(),PLUGIN_DISPLAY_NAME,"Il faut CANALISATION et OUVRAGE.")
            return

        diag = Diagnostics(self.canal_layer, self.ouvr_layer)
        results = diag.run_selected_only()

        if not self.diag_dock:
            self.diag_dock = DiagnosticsDock(self.iface.mainWindow())
            self.diag_dock.on_zoom_request(self._zoom_to_feature_from_diag)
            self.diag_dock.on_refresh_request(self._open_diagnostic_with_wait)
            self.iface.addDockWidget(QT_RIGHT_DOCK_WIDGET_AREA, self.diag_dock)

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
            QMessageBox.warning(self.iface.mainWindow(),PLUGIN_DISPLAY_NAME,"La couche LABEL_CI est introuvable.")
            return

        prov = self.label_layer.dataProvider()
        prov.truncate()  # repart propre

        if checked:
            feats: List[QgsFeature] = []
            label_crs = self.label_layer.crs()

            def _point_to_label_crs(point: QgsPointXY, source_layer: Optional[QgsVectorLayer]) -> QgsPointXY:
                if not source_layer or not point:
                    return QgsPointXY(point.x(), point.y())
                try:
                    source_crs = source_layer.crs()
                    if source_crs and label_crs and source_crs != label_crs:
                        transform = QgsCoordinateTransform(
                            source_crs, label_crs, QgsProject.instance()
                        )
                        return transform.transform(QgsPointXY(point.x(), point.y()))
                except Exception:
                    pass
                return QgsPointXY(point.x(), point.y())

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
                        pt = _point_to_label_crs(pt, self.ouvr_layer)
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
                            pt = _point_to_label_crs(pt, self.ouvr_layer)
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
                            pt = _point_to_label_crs(pt, self.astreint_layer)
                            ff = QgsFeature(self.label_layer.fields())
                            ff.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(pt.x(), pt.y())))
                            ff.setAttribute("categorie", CAT_ASTREINTE)
                            ff.setAttribute("label", aid)
                            feats.append(ff)

            # INDUSTRIEL DÉSIGNÉ
            if self.indus_layer and self.indus_layer.isValid() and self.polluter_id and self.polluter_type.upper() == "INDUS":
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
                        pt = _point_to_label_crs(pt, self.indus_layer)
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

            # OUVRAGE / POINT DIVERS DÉSIGNÉ
            if self.polluter_id and self.polluter_type.upper() in ("OUVRAGE", "POLLUTION_DIVERS"):
                if self.ouvr_layer and self.ouvr_layer.isValid() and self.polluter_id:
                    if self.polluter_type.upper() == "OUVRAGE":
                        expr = QgsExpression("trim(\"idouvrage\") = '{}'".format(self.polluter_id.replace("'", "''")))
                        for f in self.ouvr_layer.getFeatures(QgsFeatureRequest(expr)):
                            g = f.geometry()
                            pt = None
                            if g:
                                try:
                                    pt = g.asPoint()
                                except Exception:
                                    try:
                                        pt = g.centroid().asPoint()
                                    except Exception:
                                        pt = None
                            if pt:
                                pt = _point_to_label_crs(pt, self.ouvr_layer)
                                ff = QgsFeature(self.label_layer.fields())
                                ff.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(pt.x(), pt.y())))
                                ff.setAttribute("categorie", CAT_POLL_DIVERS)
                                ff.setAttribute("label", str(self.polluter_id))
                                feats.append(ff)
                                break

                layer_div = self._ensure_pollution_divers_layer()
                if layer_div and layer_div.isValid():
                    if self.polluter_type.upper() == "POLLUTION_DIVERS":
                        rec = self._get_pollution_divers_feature_by_fid(self.polluter_id)
                        source_feats = [rec] if rec else []
                    else:
                        source_feats = list(layer_div.getFeatures())
                    for f in source_feats:
                        if not f:
                            continue
                        g = f.geometry()
                        pt = None
                        if g:
                            try:
                                pt = g.asPoint()
                            except Exception:
                                try:
                                    pt = g.centroid().asPoint()
                                except Exception:
                                    pt = None
                        if pt:
                            pt = _point_to_label_crs(pt, layer_div)
                            ff = QgsFeature(self.label_layer.fields())
                            ff.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(pt.x(), pt.y())))
                            ff.setAttribute("categorie", CAT_POLL_DIVERS)
                            ff.setAttribute("label", str(f.attribute("type_pollution") or f.attribute("categorie") or "Pollution divers"))
                            feats.append(ff)
                            break

            # PV DÉSIGNÉ
            if not self.pv_layer or not self.pv_layer.isValid():
                self.pv_layer = self.pv_combo.currentData() if self.pv_combo else None
            if self.pv_layer and self.pv_layer.isValid() and self.polluter_id and self.polluter_type.upper() == "PV":
                pv_id_field = None
                for field_name in ("id", "num_pv", "ID", "NUM_PV"):
                    if self.pv_layer.fields().indexOf(field_name) >= 0:
                        pv_id_field = field_name
                        break
                pv_id_field = pv_id_field or "id"
                pv_expr = QgsExpression(
                    "trim(\"{}\") = '{}'".format(pv_id_field, self.polluter_id.replace("'", "''"))
                )
                for f in self.pv_layer.getFeatures(QgsFeatureRequest(pv_expr)):
                    g = f.geometry()
                    pt = None
                    if g:
                        try:
                            pt = g.asPoint()
                        except Exception:
                            try:
                                pt = g.centroid().asPoint()
                            except Exception:
                                pt = None
                    if pt:
                        pt = _point_to_label_crs(pt, self.pv_layer)
                        pv_label = ""
                        for k in ("num_pv", "NUM_PV", "id", "ID"):
                            try:
                                pv_label = f[k]
                                if pv_label:
                                    break
                            except Exception:
                                pass
                        pv_label = str(pv_label or self.polluter_id)
                        ff = QgsFeature(self.label_layer.fields())
                        ff.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(pt.x(), pt.y())))
                        ff.setAttribute("categorie", CAT_INDUS_DES)
                        ff.setAttribute("label", pv_label)
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
    def _make_report(self, preview: bool = False):
        try:
            if preview:
                save_path = os.path.join(tempfile.gettempdir(), "track_eau_poll_preview.pdf")
            else:
                save_path, _ = QFileDialog.getSaveFileName(
                    self.iface.mainWindow(),
                    self._tr_report("save_pdf"),
                    "",
                    "PDF (*.pdf)"
                )
                if not save_path:
                    return

            # Capture carte
            tmp_dir = tempfile.gettempdir()
            screenshot = os.path.join(tmp_dir, "cheminer_carte.png")
            self.canvas.grab().save(screenshot)

            # Construire le PDF avec logo personnalisé
            pdf = PDFGenerator(
                logo_path=self.get_logo_path(),
                legend_path=os.path.join(ICONS_DIR, 'legende.png'),
                icon_path=os.path.join(ICONS_DIR, 'icon.png')
            )
            pdf.alias_nb_pages()
            # ——— Page 1 : Carte + légende (ouverture directe sur la capture) ———
            pdf.add_map_page(
                map_img_path=screenshot,
                title=self._tr_report("map_title")
            )

            # ——— Page 2 : Contexte / Visites / Origine ———
            pdf.add_page()
            pdf.set_global_header("SOURCE: BD SIG DU SIAH - "+datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
            pdf.set_title_top(self._tr_report("report_title"))

            # Contexte
            pdf.section_title(self._tr_report("context"))
            pdf.set_font('Helvetica','',10)
            pdf.cell(0, 8, "Ouvrage de départ : {}".format(self.id_input.text()), ln=True)
            pdf.ln(2)

            # Visites
            pdf.section_title(self._tr_report("visit"))
            if self.visited:
                for v in self.visited:
                    pdf.cell(0, 6, "- {} : Pollué = {}".format(v['id'], "OUI" if v['pollution'] else "NON"), ln=True)
            else:
                pdf.cell(0, 6, self._tr_report("no_visit"), ln=True)
            pdf.ln(3)

            # Pollueur désigné
            polluter_type = (self.polluter_type or "").strip().upper()
            if self.polluter_id and polluter_type == "PV":
                if not self.pv_svc and self.pv_combo:
                    try:
                        self.pv_svc = PVService(
                            pv_layer=self.pv_combo.currentData(),
                            canal_layer=self.canal_combo.currentData() if self.canal_combo else None,
                            distance=float(self.distance_spin.value()) if getattr(self, "distance_spin", None) else 15.0
                        )
                    except Exception:
                        self.pv_svc = None
                pv_info = {}
                if self.pv_svc:
                    pv_info = self.pv_svc.fetch(self.polluter_id) or {}
                pdf.section_title(self._tr_report("pv_origin"))
                pdf.table_pv_info(pv_info, bordered=True)

                self.polluter_note = (self.note_text.toPlainText() or "").strip()
                if self.polluter_note:
                    pdf.sub_section(self._tr_report("note"))
                    pdf.multi_cell(0, 5, self.polluter_note)
                    pdf.ln(2)
            elif self.polluter_id and polluter_type == "OUVRAGE":
                pdf.section_title("Origine ouvrage / point pollution")
                data = dict(self.polluter_details or {})
                data.setdefault("id", self.polluter_id)
                data.setdefault("source_type", "OUVRAGE")
                data.setdefault("description", data.get("description", "Pollution observée à l'ouvrage désigné"))
                pdf.table_pollution_divers_info(self._pollution_divers_report_data(data), bordered=True)
                self.polluter_note = (self.note_text.toPlainText() or "").strip()
                if self.polluter_note:
                    pdf.sub_section(self._tr_report("note"))
                    pdf.multi_cell(0, 5, self.polluter_note)
                    pdf.ln(2)
            elif self.polluter_id and polluter_type == "POLLUTION_DIVERS":
                pdf.section_title("Origine pollution divers")
                feat = self._get_pollution_divers_feature_by_fid(self.polluter_id)
                data = dict(self.polluter_details or {})
                if feat:
                    for k in feat.fields().names():
                        data[k] = feat[k]
                data.setdefault("id", self.polluter_id)
                pdf.table_pollution_divers_info(self._pollution_divers_report_data(data), bordered=True)
            elif self.polluter_id:
                d = {}
                if not self.indus_svc and self.indus_combo:
                    self.indus_svc = IndustrialsService(self.indus_combo.currentData(), self.liaison_combo.currentData())
                if self.indus_svc:
                    info = self.indus_svc.fetch_many([self.polluter_id])
                    d = info.get(self.polluter_id, {})
                pdf.section_title(self._tr_report("indus_origin"))
                pdf.table_industrial_info(d, bordered=True)

                # Note synchronisée
                self.polluter_note = (self.note_text.toPlainText() or "").strip()
                if self.polluter_note:
                    pdf.sub_section(self._tr_report("note"))
                    pdf.multi_cell(0, 5, self.polluter_note)
                    pdf.ln(2)

            # ——— Page Astreinte ———
            if self.astreint_details:
                pdf.add_page()
                pdf.set_global_header("SOURCE: BD SIG DU SIAH - "+datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
                pdf.set_title_top(self._tr_report("report_title"))
                pdf.section_title(self._tr_report("astreinte"))
                tab = {k:_safe_json(v) for k,v in self.astreint_details.items()}

                try:
                    pdf.add_astreint_table(tab, bordered=True)
                except AttributeError:
                    # si méthode non implémentée dans PDFGenerator, fallback simple
                    for k, v in tab.items():
                        pdf.cell(0, 6, f"{k} : {v}", ln=True)

            # ——— Photos ———
            pdf.ln(8)
            self.ph_mgr.render(pdf)

            pdf.output(save_path)
            if preview:
                webbrowser.open("file://" + os.path.abspath(save_path))
            else:
                QMessageBox.information(self.iface.mainWindow(),"Rapport généré", save_path)
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(),PLUGIN_DISPLAY_NAME,"Erreur génération PDF : {}".format(e))

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

        # Sélection industriels
        selected_indus_ids: List[int] = []
        if self.indus_layer:
            selected_indus_ids = list(self.indus_layer.selectedFeatureIds())

        # Sélection PV
        selected_pv_ids: List[int] = []
        if self.pv_layer:
            selected_pv_ids = list(self.pv_layer.selectedFeatureIds())

        # Sauver le contenu des tableaux (dock) au moment précis de la sauvegarde
        industrial_table_data: Dict[str, Dict[str, str]] = dict(self._last_indus_data or {})
        pv_table_data: Dict[str, Dict[str, str]] = dict(self._last_pv_data or {})
        selected_pollution_divers_ids: List[int] = []
        pollution_divers_features: List[Dict[str, Any]] = []
        layer_div = self.pollution_divers_layer if (self.pollution_divers_layer and self.pollution_divers_layer.isValid()) else None
        if not layer_div:
            for lyr in QgsProject.instance().mapLayers().values():
                if self._is_pollution_divers_layer(lyr):
                    layer_div = lyr
                    self.pollution_divers_layer = lyr
                    break
        if layer_div and layer_div.isValid():
            selected_pollution_divers_ids = list(layer_div.selectedFeatureIds())
            for f in layer_div.getFeatures():
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
                rec = {"fid": f.id(), "x": pt.x(), "y": pt.y(), "attrs": {}}
                for nm in f.fields().names():
                    rec["attrs"][nm] = _safe_json(f[nm])
                pollution_divers_features.append(rec)

        # ---- NOUVEAU : état du dock des industriels ----
        industrial_state: Optional[Dict[str, Any]] = None
        if self.industrial_dock:
            try:
                industrial_state = self.industrial_dock.get_state()
                raw_indus = industrial_state.get("visible_indus_data") or industrial_state.get("raw_indus_data") or industrial_state.get("raw_data")
                raw_pv = industrial_state.get("visible_pv_data") or industrial_state.get("raw_pv_data")
                if isinstance(raw_indus, dict):
                    industrial_table_data = dict(raw_indus)
                if isinstance(raw_pv, dict):
                    pv_table_data = dict(raw_pv)
            except Exception:
                industrial_state = None
        return {
            "start_id": self.id_input.text(),
            "mode": self.direction_combo.currentText() if self.direction_combo else "",
            "category": self.cat_combo.currentData() if self.cat_combo else '',
            "function": self.func_combo.currentData() if self.func_combo else '',
            "trace_radius": self.radius_combo.currentData() if self.radius_combo else None,
            "visited": self.visited,
            "polluter_id": self.polluter_id,
            "polluter_note": self.polluter_note,
            "polluter_type": self.polluter_type,
            "polluter_details": {k: _safe_json(v) for k, v in (self.polluter_details or {}).items()},
            "astreinte": {k:_safe_json(v) for k,v in self.astreint_details.items()},
            "mask_on": self._mask_on,
            "label_ci": label_dump,
            "selected_canal_ids": selected_canal_ids,
            "selected_fosse_ids": selected_fosse_ids,
            "selected_indus_ids": selected_indus_ids,
            "selected_pv_ids": selected_pv_ids,
            "selected_pollution_divers_ids": selected_pollution_divers_ids,
            "pollution_divers_features": pollution_divers_features,
            "industrial_table_data": industrial_table_data,
            "pv_table_data": pv_table_data,
            "catchment_on": bool(self.catchment_chk.isChecked()) if self.catchment_chk else False,
            "industrial_dock": industrial_state,
            "theme": self.theme_name,
            "language": self.language,
            "last_trace_nodes": sorted(self._last_trace_nodes),
            "process_durations": dict(self._last_process_durations),
            "layers": {
                "canal": self.canal_combo.currentText() if self.canal_combo else "",
                "ouvr": self.ouvr_combo.currentText() if self.ouvr_combo else "",
                "fosse": self.fosse_combo.currentText() if self.fosse_combo else "",
                "indus": self.indus_combo.currentText() if self.indus_combo else "",
                "liaison": self.liaison_combo.currentText() if self.liaison_combo else "",
                "astreinte": self.astreint_combo.currentText() if self.astreint_combo else "",
                "pv": self.pv_combo.currentText() if self.pv_combo else "",
                "pollution_divers": self.pollution_divers_combo.currentText() if self.pollution_divers_combo else "",
            },
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
            if self.radius_combo:
                rad = st.get("trace_radius", None)
                for i in range(self.radius_combo.count()):
                    if self.radius_combo.itemData(i) == rad:
                        self.radius_combo.setCurrentIndex(i); break

            self.visited = st.get("visited",[])
            self.theme_name = st.get("theme", self.theme_name)
            self.language = st.get("language", self.language)
            self._last_trace_nodes = set(st.get("last_trace_nodes", []) or [])
            self._last_process_durations = dict(st.get("process_durations", {}) or {})

            layers_state = st.get("layers", {}) or {}
            for combo, key in (
                (self.canal_combo, "canal"),
                (self.ouvr_combo, "ouvr"),
                (self.fosse_combo, "fosse"),
                (self.indus_combo, "indus"),
                (self.liaison_combo, "liaison"),
                (self.astreint_combo, "astreinte"),
                (self.pv_combo, "pv"),
                (self.pollution_divers_combo, "pollution_divers"),
            ):
                if combo and layers_state.get(key):
                    idx = combo.findText(str(layers_state.get(key)))
                    if idx >= 0:
                        combo.setCurrentIndex(idx)

            self.polluter_id = st.get("polluter_id","")
            self.polluter_note = st.get("polluter_note","")
            self.polluter_type = st.get("polluter_type","")
            self.polluter_details = st.get("polluter_details", {}) or {}
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

            # Restauration sélection industriels
            if self.indus_combo and self.indus_combo.currentData():
                self.indus_layer = self.indus_combo.currentData()
                try:
                    iids = list(map(int, st.get("selected_indus_ids", [])))
                    self.indus_layer.removeSelection()
                    if iids:
                        self.indus_layer.selectByIds(iids)
                except Exception:
                    pass

            # Restauration sélection PV
            if self.pv_combo and self.pv_combo.currentData():
                self.pv_layer = self.pv_combo.currentData()
                try:
                    pids = list(map(int, st.get("selected_pv_ids", [])))
                    self.pv_layer.removeSelection()
                    if pids:
                        self.pv_layer.selectByIds(pids)
                except Exception:
                    pass

            layer_div = self.pollution_divers_layer if (self.pollution_divers_layer and self.pollution_divers_layer.isValid()) else None
            if not layer_div:
                for lyr in QgsProject.instance().mapLayers().values():
                    if self._is_pollution_divers_layer(lyr):
                        layer_div = lyr
                        self.pollution_divers_layer = lyr
                        break
            if layer_div and layer_div.isValid():
                try:
                    d_ids = list(map(int, st.get("selected_pollution_divers_ids", [])))
                    layer_div.removeSelection()
                    if d_ids:
                        layer_div.selectByIds(d_ids)
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
                    from ..gui.industrial_dock_v2 import IndustrialDockV2
                    self.industrial_dock = IndustrialDockV2(self.iface.mainWindow())
                    # Callbacks industriels / PV
                    self.industrial_dock.on_zoom_indus_request(self._zoom_to_industrial)
                    self.industrial_dock.on_designate_indus_request(self._designate_industrial)
                    self.industrial_dock.on_zoom_pv_request(self._zoom_to_pv)
                    self.industrial_dock.on_designate_pv_request(self._designate_pv)
                    # Callback refresh
                    self.industrial_dock.on_refresh_request(self._refresh_industrial_dock_data)
                    self.iface.addDockWidget(QT_RIGHT_DOCK_WIDGET_AREA, self.industrial_dock)

                # Appliquer l'état au dock
                try:
                    self.industrial_dock.apply_state(ind_state)
                except Exception:
                    pass

                # Mémoriser les derniers industriels/PV (pour les rafraîchissements / rapport)
                self._last_indus_data = (
                    ind_state.get("visible_indus_data")
                    or ind_state.get("raw_indus_data")
                    or ind_state.get("raw_data")
                    or st.get("industrial_table_data")
                    or {}
                )
                self._last_pv_data = (
                    ind_state.get("visible_pv_data")
                    or ind_state.get("raw_pv_data")
                    or st.get("pv_table_data")
                    or {}
                )
                if hasattr(self.industrial_dock, "set_data"):
                    self.industrial_dock.set_data(self._last_indus_data)
                if hasattr(self.industrial_dock, "set_pv_data"):
                    self.industrial_dock.set_pv_data(list(self._last_pv_data.values()))
                if self.pv_tab and hasattr(self.pv_tab, "set_pv_data"):
                    self.pv_tab.set_pv_data(self._last_pv_data)

                # Ouvrir / fermer selon l'état sauvegardé
                if ind_state.get("is_open", False):
                    self.industrial_dock.show()
                    self.industrial_dock.raise_()
                else:
                    self.industrial_dock.hide()
            else:
                self._last_indus_data = st.get("industrial_table_data") or {}
                self._last_pv_data = st.get("pv_table_data") or {}
                if self._last_indus_data or self._last_pv_data:
                    self._open_or_update_industrial_dock(
                        data=self._last_indus_data,
                        pv_data=self._last_pv_data,
                    )

            self._apply_theme(self.theme_name)
            self._apply_language(self.language)

            if show_message:
                QMessageBox.information(self.iface.mainWindow(),PLUGIN_DISPLAY_NAME,"Session chargée.")
            self.canvas.refresh()
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(),PLUGIN_DISPLAY_NAME,"Erreur restauration session : {}".format(e))

    def _save_session(self):
        path, _ = QFileDialog.getSaveFileName(self.iface.mainWindow(),"Sauvegarder session",".","Texte (*.txt)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._session_state(), f, ensure_ascii=False, indent=2)
            QMessageBox.information(self.iface.mainWindow(),PLUGIN_DISPLAY_NAME,"Session sauvegardée.")
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(),PLUGIN_DISPLAY_NAME,"Erreur sauvegarde : {}".format(e))

    def _load_session(self):
        path, _ = QFileDialog.getOpenFileName(self.iface.mainWindow(),"Charger session",".","Texte (*.txt)")
        if not path:
            return
        try:
            with open(path,"r",encoding="utf-8") as f:
                st = json.load(f)
            self._apply_session_state(st, show_message=True)
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(),PLUGIN_DISPLAY_NAME,"Erreur chargement : {}".format(e))

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

        QMessageBox.information(self.iface.mainWindow(),PLUGIN_DISPLAY_NAME,"Tables minimales créées (mémoire).")
        self._autosave()

    # ---------------------------------------------------------
    # RESET
    # ---------------------------------------------------------
    # ---------------------------------------------------------
    # GESTION PV (NOUVEAU v1.2.3 Phase 3)
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
                    self.liaison_layer, self.indus_layer, self.pv_layer, self.astreint_layer):
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
        self.polluter_type = ""
        self.polluter_details = {}
        self._last_trace_nodes.clear()
        self._mask_on = False
        self._last_indus_data = {}
        self._last_pv_data = {}
        self._tracer_key = None
        self._network_cache_key = None
        self._canal_nodes_by_fid = {}
        self._fosse_nodes_by_fid = {}
        self._liaison_fids_by_node = {}

        if self.industrial_dock:
            self.iface.removeDockWidget(self.industrial_dock); self.industrial_dock = None
        if self.diag_dock:
            self.iface.removeDockWidget(self.diag_dock); self.diag_dock = None

        self.canvas.refresh()
        QMessageBox.information(self.iface.mainWindow(),PLUGIN_DISPLAY_NAME,"Plugin réinitialisé.")
        self._autosave()

    # ---------------------------------------------------------
    # Gestion des paramètres (Logo et Icône)
    # ---------------------------------------------------------
    def _update_logo_preview(self):
        """Met à jour l'aperçu du logo"""
        logo_path = self.custom_logo_path or os.path.join(ICONS_DIR, 'logo.png')
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            self.logo_preview_label.setPixmap(pixmap)
        else:
            self.logo_preview_label.setText("❌ Logo non trouvé")
            self.logo_preview_label.setStyleSheet("border: 1px solid #ccc; background: #f5f5f5; color: red;")

    def _update_icon_preview(self):
        """Met à jour l'aperçu de l'icône"""
        icon_path = self.custom_icon_path or os.path.join(ICONS_DIR, 'icon.png')
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            self.icon_preview_label.setPixmap(pixmap)
        else:
            self.icon_preview_label.setText("❌ Icône\nnon trouvée")
            self.icon_preview_label.setStyleSheet("border: 1px solid #ccc; background: #f5f5f5; color: red;")

    def _on_browse_logo(self):
        """Ouvre un dialogue pour sélectionner un fichier logo"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.iface.mainWindow(),
            "Sélectionner un logo",
            os.path.expanduser("~"),
            "Images (*.png *.jpg *.jpeg);;Tous les fichiers (*.*)"
        )
        
        if file_path:
            self.custom_logo_path = file_path
            self.logo_path_input.setText(file_path)
            self._update_logo_preview()
            
            QMessageBox.information(
                self.iface.mainWindow(),
                "Logo modifié",
                f"Le nouveau logo sera utilisé dans les rapports PDF.\n\n"
                f"Chemin : {file_path}\n\n"
                f"💾 N'oubliez pas de sauvegarder les paramètres !"
            )

    def _on_browse_icon(self):
        """Ouvre un dialogue pour sélectionner un fichier icône"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.iface.mainWindow(),
            "Sélectionner une icône",
            os.path.expanduser("~"),
            "Images (*.png *.jpg *.jpeg);;Tous les fichiers (*.*)"
        )
        
        if file_path:
            self.custom_icon_path = file_path
            self.icon_path_input.setText(file_path)
            self._update_icon_preview()
            
            QMessageBox.information(
                self.iface.mainWindow(),
                "Icône modifiée",
                f"La nouvelle icône sera visible après le redémarrage de QGIS.\n\n"
                f"Chemin : {file_path}\n\n"
                f"💾 N'oubliez pas de sauvegarder les paramètres !"
            )

    def _on_reset_logo(self):
        """Réinitialise le logo au logo par défaut"""
        reply = QMessageBox.question(
            self.iface.mainWindow(),
            "Réinitialiser le logo",
            "Voulez-vous réinitialiser le logo au logo par défaut ?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.custom_logo_path = ""
            self.logo_path_input.setText("")
            self._update_logo_preview()
            
            QMessageBox.information(
                self.iface.mainWindow(),
                "Logo réinitialisé",
                "Le logo par défaut sera utilisé.\n\n"
                "💾 N'oubliez pas de sauvegarder les paramètres !"
            )

    def _on_reset_icon(self):
        """Réinitialise l'icône à l'icône par défaut"""
        reply = QMessageBox.question(
            self.iface.mainWindow(),
            "Réinitialiser l'icône",
            "Voulez-vous réinitialiser l'icône à l'icône par défaut ?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.custom_icon_path = ""
            self.icon_path_input.setText("")
            self._update_icon_preview()
            
            QMessageBox.information(
                self.iface.mainWindow(),
                "Icône réinitialisée",
                "L'icône par défaut sera utilisée après le redémarrage de QGIS.\n\n"
                "💾 N'oubliez pas de sauvegarder les paramètres !"
            )

    def _save_settings_silent(self):
        """Sauvegarde silencieuse des paramètres sans popup."""
        try:
            settings = {
                "custom_logo_path": self.custom_logo_path,
                "custom_icon_path": self.custom_icon_path,
                "theme_name": self.theme_name,
                "language": self.language,
                "plugin_variant": self.plugin_variant,
            }
            config_dir = os.path.join(os.path.dirname(__file__), "..")
            config_file = os.path.join(config_dir, "settings.json")
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _on_save_settings(self):
        """Sauvegarde les paramètres dans un fichier de configuration"""
        try:
            import json
            
            settings = {
                'custom_logo_path': self.custom_logo_path,
                'custom_icon_path': self.custom_icon_path,
                'theme_name': self.theme_name,
                'language': self.language,
                'plugin_variant': self.plugin_variant,
            }
            
            # Chemin du fichier de configuration
            config_dir = os.path.join(os.path.dirname(__file__), '..')
            config_file = os.path.join(config_dir, 'settings.json')
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(
                self.iface.mainWindow(),
                "Paramètres sauvegardés",
                f"✅ Les paramètres ont été sauvegardés avec succès !\n\n"
                f"Fichier : {config_file}\n\n"
                f"Les modifications du logo seront visibles dans les prochains rapports PDF.\n"
                f"Les modifications de l'icône nécessitent un redémarrage de QGIS."
            )
        except Exception as e:
            QMessageBox.critical(
                self.iface.mainWindow(),
                "Erreur",
                f"Impossible de sauvegarder les paramètres :\n{str(e)}"
            )

    def _on_export_settings(self):
        """Exporte les paramètres dans un fichier JSON"""
        file_path, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(),
            "Exporter les paramètres",
            os.path.join(os.path.expanduser("~"), "cheminer_indus_settings.json"),
            "Fichiers JSON (*.json)"
        )
        
        if file_path:
            try:
                import json
                
                settings = {
                    'custom_logo_path': self.custom_logo_path,
                    'custom_icon_path': self.custom_icon_path,
                    'theme_name': self.theme_name,
                    'language': self.language,
                'plugin_variant': self.plugin_variant,
                    'exported_date': str(datetime.now())
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=2, ensure_ascii=False)
                
                QMessageBox.information(
                    self.iface.mainWindow(),
                    "Export réussi",
                    f"✅ Paramètres exportés vers :\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    "Erreur d'export",
                    f"Impossible d'exporter les paramètres :\n{str(e)}"
                )

    def _on_import_settings(self):
        """Importe les paramètres depuis un fichier JSON"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.iface.mainWindow(),
            "Importer les paramètres",
            os.path.expanduser("~"),
            "Fichiers JSON (*.json)"
        )
        
        if file_path:
            try:
                import json
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # Appliquer les paramètres
                if 'custom_logo_path' in settings:
                    self.custom_logo_path = settings['custom_logo_path']
                    self.logo_path_input.setText(self.custom_logo_path)
                    self._update_logo_preview()
                
                if 'custom_icon_path' in settings:
                    self.custom_icon_path = settings['custom_icon_path']
                    self.icon_path_input.setText(self.custom_icon_path)
                    self._update_icon_preview()

                if 'theme_name' in settings:
                    self.theme_name = settings['theme_name']
                    if hasattr(self, "theme_combo") and self.theme_combo:
                        idx = self.theme_combo.findText(self.theme_name)
                        if idx >= 0:
                            self.theme_combo.setCurrentIndex(idx)
                    self._apply_theme(self.theme_name)

                if 'language' in settings:
                    self.language = settings['language']
                    if hasattr(self, "lang_combo") and self.lang_combo:
                        idx = self.lang_combo.findData(self.language)
                        if idx >= 0:
                            self.lang_combo.setCurrentIndex(idx)
                    self._apply_language(self.language)

                if 'plugin_variant' in settings:
                    self._apply_plugin_variant(settings.get('plugin_variant', 'LITE'), persist=False, show_message=False)
                    if hasattr(self, "variant_combo") and self.variant_combo:
                        idx = self.variant_combo.findData(self.plugin_variant)
                        if idx >= 0:
                            self.variant_combo.setCurrentIndex(idx)

                QMessageBox.information(
                    self.iface.mainWindow(),
                    "Import réussi",
                    f"✅ Paramètres importés depuis :\n{file_path}\n\n"
                    f"💾 N'oubliez pas de sauvegarder les paramètres !"
                )
            except Exception as e:
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    "Erreur d'import",
                    f"Impossible d'importer les paramètres :\n{str(e)}"
                )

    def _load_settings_on_startup(self):
        """Charge les paramètres au démarrage du plugin"""
        try:
            import json
            
            config_dir = os.path.join(os.path.dirname(__file__), '..')
            config_file = os.path.join(config_dir, 'settings.json')
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                self.custom_logo_path = settings.get('custom_logo_path', '')
                self.custom_icon_path = settings.get('custom_icon_path', '')
                self.theme_name = settings.get('theme_name', self.theme_name)
                self.language = settings.get('language', self.language)
                self.plugin_variant = str(settings.get('plugin_variant', self.plugin_variant)).strip().upper()
        except Exception as e:
            print(f"Impossible de charger les paramètres : {e}")

    def get_logo_path(self) -> str:
        """Retourne le chemin du logo (personnalisé ou par défaut)"""
        if self.custom_logo_path and os.path.exists(self.custom_logo_path):
            return self.custom_logo_path
        return os.path.join(ICONS_DIR, 'logo.png')

    def get_icon_path(self) -> str:
        """Retourne le chemin de l'icône (personnalisée ou par défaut)"""
        if self.custom_icon_path and os.path.exists(self.custom_icon_path):
            return self.custom_icon_path
        return os.path.join(ICONS_DIR, 'icon.png')
