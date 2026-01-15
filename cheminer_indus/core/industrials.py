# -*- coding: utf-8 -*-
# cheminer_indus/core/industrials.py

from __future__ import annotations
from typing import List, Dict, Set, Optional

from qgis.core import QgsVectorLayer, QgsExpression, QgsFeatureRequest


class IndustrialsService:
    """
    Opérations sur Industriels & Liaisons.
    """

    def __init__(self, indus_layer: Optional[QgsVectorLayer],
                 liaison_layer: Optional[QgsVectorLayer]):
        self.indus_layer = indus_layer
        self.liaison_layer = liaison_layer

    # ------------------------------------------------------------------
    # Sélection via nœuds atteints
    # ------------------------------------------------------------------
    def select_liaisons_from_nodes(self, nodes: Set[str]) -> List[int]:
        """
        À partir d'un ensemble de nœuds, sélectionne les liaisons concernées
        dans la couche LIAISON_INDUS et renvoie la liste de leurs FIDs.
        """
        if not self.liaison_layer or not nodes:
            if self.liaison_layer:
                self.liaison_layer.removeSelection()
            return []

        esc = lambda s: (s or "").replace("'", "''")
        values = ",".join("'{}'".format(esc(n)) for n in nodes if n)
        if not values:
            self.liaison_layer.removeSelection()
            return []

        expr = QgsExpression("\"id_ouvrage\" IN ({})".format(values))
        req = QgsFeatureRequest(expr)
        ids = [f.id() for f in self.liaison_layer.getFeatures(req)]

        self.liaison_layer.removeSelection()
        if ids:
            self.liaison_layer.selectByIds(ids)

        return ids

    def select_industrials_from_selected_liaisons(self) -> List[str]:
        """
        Lit la sélection de liaisons, sélectionne les industriels correspondants
        et renvoie leurs IDs (texte).
        """
        if not self.liaison_layer or not self.indus_layer:
            return []

        ind_ids: Set[str] = set()
        for lf in self.liaison_layer.selectedFeatures():
            ind = lf['id_industriel']
            if ind and ind != 'INCONNU':
                ind_ids.add(str(ind))

        self.indus_layer.removeSelection()
        if ind_ids:
            esc = lambda s: (s or "").replace("'", "''")
            values = ",".join("'{}'".format(esc(i)) for i in ind_ids)
            exprI = QgsExpression("\"id\" IN ({})".format(values))
            reqI = QgsFeatureRequest(exprI)
            fids = [f.id() for f in self.indus_layer.getFeatures(reqI)]
            if fids:
                self.indus_layer.selectByIds(fids)

        return sorted(ind_ids)

    def connected_ids_from_nodes(self, nodes: Set[str]) -> List[str]:
        """
        Raccourci : à partir des nœuds → sélectionner liaisons → industriels
        → renvoyer IDs.
        """
        self.select_liaisons_from_nodes(nodes)
        return self.select_industrials_from_selected_liaisons()

    # ------------------------------------------------------------------
    # Récupération d'infos
    # ------------------------------------------------------------------
    def fetch(self, ind_id: str) -> Dict[str, str]:
        """
        Renvoie un dictionnaire {champ: valeur} pour un industriel donné.
        Essaie de normaliser quelques noms usuels (Nom, Adresse, Activite…)
        pour faciliter l'affichage dans le tableau.
        """
        if not self.indus_layer:
            return {}

        expr = QgsExpression("\"id\" = '{}'".format(str(ind_id).replace("'", "''")))
        req = QgsFeatureRequest(expr)

        for f in self.indus_layer.getFeatures(req):
            out: Dict[str, str] = {}
            for name in f.fields().names():
                out[name] = "" if f[name] is None else str(f[name])

            # Renommages usuels (on ajoute ces clés si absentes)
            out.setdefault("Nom", out.get("nom", ""))
            out.setdefault("Adresse", out.get("adresse", ""))
            out.setdefault("Activite", out.get("activite", ""))
            out.setdefault("Risques", out.get("risques", ""))
            out.setdefault("Produits", out.get("produits", ""))
            out.setdefault("siret", out.get("SIRET", out.get("siret", "")))

            # Toujours stocker l'id pour le tableau
            out.setdefault("id", str(ind_id))

            return out

        return {}

    def fetch_many(self, ids: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Renvoie {id_indus: {champ: valeur, ...}, ...}
        """
        out: Dict[str, Dict[str, str]] = {}
        for i in ids:
            out[i] = self.fetch(i)
        return out
