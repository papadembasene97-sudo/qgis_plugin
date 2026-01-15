# -*- coding: utf-8 -*-
# cheminer_indus/report/pdf_generator.py
"""
Générateur de PDF pour CheminerIndus.

Ajouts :
- Numéros de page en bas à droite (footer).
"""

from __future__ import annotations
import os
from typing import Dict, Any
from fpdf import FPDF


class PDFGenerator(FPDF):
    # =========================
    # Réglages modifiables
    # =========================
    LEFT_MARGIN  = 15
    RIGHT_MARGIN = 15
    TOP_MARGIN   = 20
    AUTO_BREAK   = 18

    TITLE_Y      = 17
    LOGO_X       = 15
    LOGO_Y       = 8
    LOGO_W       = 25

    FONT_BASE    = 10
    FONT_SMALL   = 9
    FONT_SECTION = 12
    FONT_TITLE   = 16

    TABLE_KEY_RATIO   = 1.75
    TABLE_VALUE_RATIO = 1.65
    TABLE_LINE_H      = 6

    MAP_TOP_Y         = 35
    LEG_GAP           = 8
    LEG_SCALE         = 0.90

    def __init__(self, logo_path: str = "", legend_path: str = ""):
        super().__init__(orientation='P', unit='mm', format='A4')

        self.logo_path   = logo_path or ""
        self.legend_path = legend_path or ""

        base_dir  = os.path.dirname(os.path.dirname(__file__))
        fonts_dir = os.path.join(base_dir, "fonts")
        try:
            self.add_font("DejaVu",  "", os.path.join(fonts_dir, "DejaVuSans.ttf"),          uni=True)
            self.add_font("DejaVu",  "B", os.path.join(fonts_dir, "DejaVuSans-Bold.ttf"),    uni=True)
            self.add_font("DejaVu",  "I", os.path.join(fonts_dir, "DejaVuSans-Oblique.ttf"), uni=True)
        except Exception:
            pass

        self.set_auto_page_break(auto=True, margin=self.AUTO_BREAK)
        self.set_margins(self.LEFT_MARGIN, self.TOP_MARGIN, self.RIGHT_MARGIN)

        try:
            self.set_font("DejaVu", "", self.FONT_BASE)
        except Exception:
            self.set_font("Helvetica", "", self.FONT_BASE)

    # ------------------------------------------------------------------
    # Footer avec numéro de page
    # ------------------------------------------------------------------
    def footer(self):
        """Numéro de page en bas à droite."""
        self.set_y(-15)  # 15 mm depuis le bas
        try:
            self.set_font("DejaVu", "I", 8)
        except Exception:
            self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="R")

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------
    def _ensure_page(self):
        if self.page_no() == 0:
            self.add_page()

    def _set_font_base(self):
        try:
            self.set_font("DejaVu", "", self.FONT_BASE)
        except Exception:
            self.set_font("Helvetica", "", self.FONT_BASE)

    def _set_font_bold(self, size: int | None = None):
        s = size if size is not None else self.FONT_BASE
        try:
            self.set_font("DejaVu", "B", s)
        except Exception:
            self.set_font("Helvetica", "B", s)

    def _set_font_small(self):
        try:
            self.set_font("DejaVu", "", self.FONT_SMALL)
        except Exception:
            self.set_font("Helvetica", "", self.FONT_SMALL)

    def _col_widths(self) -> tuple[float, float]:
        usable_w = self.w - self.l_margin - self.r_margin
        k = usable_w * (self.TABLE_KEY_RATIO / (self.TABLE_KEY_RATIO + self.TABLE_VALUE_RATIO))
        v = usable_w - k
        return k, v

    # ------------------------------------------------------------------
    # En-têtes et titres
    # ------------------------------------------------------------------
    def set_global_header(self, text: str):
        self._ensure_page()
        self.set_xy(0, 8)
        self._set_font_small()
        self.cell(0, 5, text, align='R', ln=1)

    def set_title_top(self, title: str):
        self._ensure_page()
        if self.logo_path and os.path.exists(self.logo_path):
            self.image(self.logo_path, x=self.LOGO_X, y=self.LOGO_Y, w=self.LOGO_W)
        self.set_xy(0, self.TITLE_Y + 5)
        self._set_font_bold(self.FONT_TITLE)
        self.cell(0, 8, title, align='C', ln=1)
        self.ln(3)
        self._set_font_base()

    def section_title(self, title: str):
        self._ensure_page()
        self._set_font_bold(self.FONT_SECTION)
        self.cell(0, 7, title, ln=True)
        self._set_font_base()

    def sub_section(self, title: str):
        self._ensure_page()
        self._set_font_bold(self.FONT_BASE + 1)
        self.cell(0, 6, title, ln=True)
        self._set_font_base()

    # ------------------------------------------------------------------
    # Tableaux
    # ------------------------------------------------------------------
    def _kv_table(self, rows: list[tuple[str, Any]], bordered: bool = True):
        key_w, val_w = self._col_widths()
        th = self.TABLE_LINE_H
        for k, v in rows:
            self._set_font_bold()
            self.cell(key_w, th, str(k), border=1 if bordered else 0)
            self._set_font_base()
            self.multi_cell(val_w, th, "" if v is None else str(v), border=1 if bordered else 0)
        self.ln(1)

    def table_industrial_info(self, data: Dict[str, Any], bordered: bool = True):
        self._ensure_page()
        rows = [
            ("ID",        data.get("id", "")),
            ("Nom",       data.get("Nom", "") or data.get("nom", "")),
            ("Adresse",   data.get("Adresse", "") or data.get("adresse", "")),
            ("Activité",  data.get("Activite", "") or data.get("activite", "")),
            ("SIRET",     data.get("siret", "") or data.get("SIRET", "")),
            ("Produits",  data.get("Produits", "")),
            ("Risques",   data.get("Risques", "")),
        ]
        self._kv_table(rows, bordered=bordered)

    def add_astreint_table(self, data: Dict[str, Any], bordered: bool = True):
        self._ensure_page()
        rows = [
            ("ID",                  data.get("id", "")),
            ("Nom",                 data.get("nom", "")),
            ("Téléphone",           data.get("tel", "")),
            ("Date",                data.get("date", "")),
            ("Heure",               data.get("heure", "")),
            ("Agent",               data.get("agent", "")),
            ("Adresse",             data.get("adresse", "")),
            ("Commune",             data.get("commune", "")),
            ("Complément",          data.get("complement", "")),
            ("Type canalisation",   data.get("typ_cana", "")),
            ("Prestataire",         data.get("prestatair", "")),
            ("Appel astreinte",     data.get("appel_astr", "") or data.get("appel_astreinte", "")),
            ("Intervention EP",     data.get("interv_ep", "")),
            ("Intervention EU",     data.get("interv_eu", "")),
            ("Intervention voirie", data.get("interv_voi", "")),
        ]
        self._kv_table(rows, bordered=bordered)

        msg = str(data.get("message", "") or data.get("Message", "") or "").strip()
        act = str(data.get("action_m", "") or data.get("Action", "") or "").strip()

        self.ln(2)
        self._set_font_bold(10); self.cell(0, self.TABLE_LINE_H, "Message :", ln=True)
        self._set_font_base(); self.multi_cell(0, self.TABLE_LINE_H, msg or "—")

        self.ln(1)
        self._set_font_bold(10); self.cell(0, self.TABLE_LINE_H, "Action :", ln=True)
        self._set_font_base(); self.multi_cell(0, self.TABLE_LINE_H, act or "—")

    # ------------------------------------------------------------------
    # Carte + Légende
    # ------------------------------------------------------------------
    def add_map_page(self, map_img_path: str, title: str = "CARTE DE LA SITUATION RÉSEAUX"):
        self.add_page()
        self.set_title_top(title)
        usable_w = self.w - self.l_margin - self.r_margin
        x = self.l_margin; y = self.MAP_TOP_Y
        if map_img_path and os.path.exists(map_img_path):
            self.image(map_img_path, x=x, y=y, w=usable_w)
            self.set_y(y + self.get_image_height(usable_w, map_img_path) + self.LEG_GAP)
        else:
            self.ln(10)
        if self.legend_path and os.path.exists(self.legend_path):
            leg_w = usable_w * self.LEG_SCALE
            leg_x = self.l_margin + (usable_w - leg_w) / 2.0
            self.image(self.legend_path, x=leg_x, y=self.get_y(), w=leg_w)
            self.ln(2)

    def get_image_height(self, target_w: float, path: str) -> float:
        try:
            from PIL import Image
            with Image.open(path) as im:
                w, h = im.size
            ratio = h / float(w) if w else 0.75
            return target_w * ratio
        except Exception:
            return target_w * 0.66
