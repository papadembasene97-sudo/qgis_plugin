# -*- coding: utf-8 -*-
# cheminer_indus/report/photos.py

import os
from qgis.PyQt.QtWidgets import QFileDialog, QInputDialog, QLineEdit

class PhotoManager:
    def __init__(self):
        # liste de dicts: {"path": str, "comment": str}
        self._photos = []

    def add(self, parent):
        files, _ = QFileDialog.getOpenFileNames(parent, "Ajouter des photos", "", "Images (*.png *.jpg *.jpeg)")
        if files:
            for f in files:
                if os.path.exists(f):
                    # Demander un commentaire facultatif par photo
                    txt, ok = QInputDialog.getText(parent, "Commentaire photo",
                                                   f"Commentaire pour :\n{os.path.basename(f)}",
                                                   QLineEdit.Normal, "")
                    comment = str(txt) if ok else ""
                    self._photos.append({"path": f, "comment": comment})

    def render(self, pdf):
        """
        Chaque photo sur sa propre page, avec le commentaire en bas.
        """
        for item in self._photos:
            p = item.get("path")
            c = item.get("comment","")
            try:
                pdf.add_page()
                pdf.image(p, x=10, w=180)
                if c:
                    pdf.ln(5)
                    pdf.set_font('Arial', '', 9)
                    pdf.multi_cell(0, 5, c)
            except Exception:
                continue
