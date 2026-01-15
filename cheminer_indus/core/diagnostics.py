# -*- coding: utf-8 -*-
# cheminer_indus/core/diagnostics.py

from __future__ import annotations
from typing import Dict, List, Tuple

from qgis.core import QgsVectorLayer, QgsFeatureRequest, QgsExpression


class Diagnostics:
    """
    Deux rubriques :
    - INVERSIONS EU/EP
    - RÉDUCTION DE DIAMÈTRE
    Analyse uniquement les canalisations sélectionnées.
    """

    def __init__(self, canal_layer: QgsVectorLayer, ouvr_layer: QgsVectorLayer):
        self.canal = canal_layer
        self.ouvr = ouvr_layer

    def run_selected_only(self) -> Dict[str, List[Tuple[int, str, int]]]:
        inversions = []
        reductions = []

        if not self.canal or not self.ouvr:
            return {"INVERSIONS": inversions, "REDUCTIONS": reductions}

        sel_ids = self.canal.selectedFeatureIds()
        if not sel_ids:
            return {"INVERSIONS": inversions, "REDUCTIONS": reductions}

        has_inversion_field = "inversion" in self.canal.fields().names()

        inversion_mapping = {
            "1": "Inversion EP dans EU avérée",
            "2": "Inversion EU dans EP avérée",
            "3": "Trop-plein EP dans EU",
            "4": "Trop-plein EU dans EP",
        }

        req = QgsFeatureRequest().setFilterFids(sel_ids)

        for f in self.canal.getFeatures(req):
            typ_c = (f["typreseau"] or "").strip()
            idnini = f["idnini"]
            idnterm = f["idnterm"]

            # ------------------------------------------------------
            # 1) INVERSIONS
            # ------------------------------------------------------
            for oid, pos in ((idnini, "amont"), (idnterm, "aval")):
                if not oid or oid == "INCONNU":
                    continue

                safe_oid = str(oid).replace("'", "''")
                expr = QgsExpression("\"idouvrage\" = '{}'".format(safe_oid))

                of = next(self.ouvr.getFeatures(QgsFeatureRequest(expr)), None)
                if not of:
                    continue

                typ_o = (of["typreseau"] or "").strip()

                # EP/EU inversés
                if typ_c in ("01", "02") and typ_o in ("01", "02") and typ_c != typ_o:

                    direction = ""
                    if typ_c == "02" and typ_o == "01":
                        direction = "EU → EP"
                    elif typ_c == "01" and typ_o == "02":
                        direction = "EP → EU"

                    if direction:
                        # statut d’inversion via champ SQL
                        statut = "Inversion à vérifier"
                        if has_inversion_field:
                            try:
                                code = f["inversion"]
                                code = "" if code is None else str(code).strip()
                                if code:
                                    statut = inversion_mapping.get(code, "Inversion à vérifier")
                            except Exception:
                                pass

                        info_txt = "Inversion {} ({} de l’ouvrage {}) - {}".format(
                            direction, pos, oid, statut
                        )

                        inversions.append((f.id(), info_txt, of.id()))

            # ------------------------------------------------------
            # 2) REDUCTION DE DIAMÈTRE
            # ------------------------------------------------------
            def _to_int(v, default=-1):
                try:
                    return int(str(v).strip())
                except Exception:
                    return default

            diam_aval = _to_int(f["diametre"], -1)
            if diam_aval <= 0:
                continue

            typ_for_threshold = typ_c if typ_c in ("01", "02") else "01"
            seuil = 50 if typ_for_threshold == "02" else 200

            if idnini and idnini != "INCONNU":
                safe_ini = str(idnini).replace("'", "''")

                expr_in = QgsExpression("\"idnterm\" = '{}'".format(safe_ini))
                diam_in_list = []
                in_count = 0

                for fin in self.canal.getFeatures(QgsFeatureRequest(expr_in)):
                    d = _to_int(fin["diametre"], -1)
                    if d > 0:
                        diam_in_list.append(d)
                    in_count += 1

                if in_count >= 1:
                    expr_out = QgsExpression("\"idnini\" = '{}'".format(safe_ini))
                    out_count = sum(1 for _ in self.canal.getFeatures(QgsFeatureRequest(expr_out)))

                    if out_count == 1 and diam_in_list:
                        dmax = max(diam_in_list)
                        if dmax - diam_aval > seuil:
                            info_red = (
                                "Réduction de diamètre : {} → {} (seuil {} mm) sur ouvrage {}".format(
                                    dmax, diam_aval, seuil, idnini
                                )
                            )
                            reductions.append((f.id(), info_red, f.id()))

        return {"INVERSIONS": inversions, "REDUCTIONS": reductions}
