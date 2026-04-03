# -*- coding: utf-8 -*-
# cheminer_indus/core/pv_service.py

from __future__ import annotations
import datetime
import re
from typing import List, Dict, Set, Optional

from qgis.core import (
    QgsVectorLayer, QgsExpression, QgsFeatureRequest, QgsFeature,
    QgsGeometry, QgsCoordinateTransform, QgsProject, QgsSpatialIndex
)


class PVService:
    """
    Service pour les opérations sur la couche PV_CONFORMITE.
    Suit le même pattern que IndustrialsService.
    """

    def __init__(self, pv_layer: Optional[QgsVectorLayer], 
                 canal_layer: Optional[QgsVectorLayer] = None):
        """
        Args:
            pv_layer: Couche PV_CONFORMITE (ou toute couche PV)
            canal_layer: Couche canalisations (pour calculs de distance)
        """
        self.pv_layer = pv_layer
        self.canal_layer = canal_layer

        # Caches performance
        self._canal_ids_by_node: Optional[Dict[str, Set[int]]] = None
        self._pv_index_all: Optional[QgsSpatialIndex] = None
        self._pv_geom_cache_all: Optional[Dict[int, QgsGeometry]] = None
        self._pv_index_nonconf: Optional[QgsSpatialIndex] = None
        self._pv_geom_cache_nonconf: Optional[Dict[int, QgsGeometry]] = None
        self._pv_index_nonconf_visit: Optional[QgsSpatialIndex] = None
        self._pv_geom_cache_nonconf_visit: Optional[Dict[int, QgsGeometry]] = None
        self._pv_cache_target_crs: Optional[str] = None

        self._canal_spatial_index: Optional[QgsSpatialIndex] = None
        self._canal_geom_cache: Optional[Dict[int, QgsGeometry]] = None


    def invalidate_caches(self):
        """Invalide les caches (à appeler si les couches changent)."""
        self._canal_ids_by_node = None
        self._pv_index_all = None
        self._pv_geom_cache_all = None
        self._pv_index_nonconf = None
        self._pv_geom_cache_nonconf = None
        self._pv_index_nonconf_visit = None
        self._pv_geom_cache_nonconf_visit = None
        self._pv_cache_target_crs = None
        self._canal_spatial_index = None
        self._canal_geom_cache = None

    def _build_node_to_canal_cache(self) -> Dict[str, Set[int]]:
        if self._canal_ids_by_node is not None:
            return self._canal_ids_by_node

        cache: Dict[str, Set[int]] = {}
        if not self.canal_layer or not self.canal_layer.isValid():
            self._canal_ids_by_node = cache
            return cache

        for feat in self.canal_layer.getFeatures():
            try:
                idnini = str(feat['idnini'] or '').strip()
                idnterm = str(feat['idnterm'] or '').strip()
                fid = feat.id()
                if idnini and idnini.upper() != 'INCONNU':
                    cache.setdefault(idnini, set()).add(fid)
                if idnterm and idnterm.upper() != 'INCONNU':
                    cache.setdefault(idnterm, set()).add(fid)
            except Exception:
                continue

        self._canal_ids_by_node = cache
        return cache

    def _build_canal_spatial_cache(self):
        if self._canal_spatial_index is not None and self._canal_geom_cache is not None:
            return self._canal_spatial_index, self._canal_geom_cache

        idx = QgsSpatialIndex()
        geom_cache: Dict[int, QgsGeometry] = {}
        if self.canal_layer and self.canal_layer.isValid():
            for feat in self.canal_layer.getFeatures():
                g = feat.geometry()
                if not g:
                    continue
                geom_cache[feat.id()] = g
                idx.addFeature(feat)

        self._canal_spatial_index = idx
        self._canal_geom_cache = geom_cache
        return idx, geom_cache

    def _build_pv_spatial_cache(
        self,
        include_conformes: bool,
        transform: Optional[QgsCoordinateTransform],
        target_crs_authid: str,
        only_visit_or_contre: bool = False
    ):
        if self._pv_cache_target_crs != target_crs_authid:
            self._pv_index_all = None
            self._pv_geom_cache_all = None
            self._pv_index_nonconf = None
            self._pv_geom_cache_nonconf = None
            self._pv_index_nonconf_visit = None
            self._pv_geom_cache_nonconf_visit = None
            self._pv_cache_target_crs = target_crs_authid

        if include_conformes and self._pv_index_all is not None and self._pv_geom_cache_all is not None:
            return self._pv_index_all, self._pv_geom_cache_all
        if (not include_conformes) and only_visit_or_contre and self._pv_index_nonconf_visit is not None and self._pv_geom_cache_nonconf_visit is not None:
            return self._pv_index_nonconf_visit, self._pv_geom_cache_nonconf_visit
        if (not include_conformes) and self._pv_index_nonconf is not None and self._pv_geom_cache_nonconf is not None:
            return self._pv_index_nonconf, self._pv_geom_cache_nonconf

        pv_index = QgsSpatialIndex()
        pv_geom_cache: Dict[int, QgsGeometry] = {}

        if self.pv_layer and self.pv_layer.isValid():
            for pv_feat in self.pv_layer.getFeatures():
                if not include_conformes and not self._is_non_conforme(pv_feat):
                    continue
                if only_visit_or_contre and (not self._is_visit_or_contre(pv_feat)):
                    continue
                pv_geom = pv_feat.geometry()
                if not pv_geom:
                    continue
                if transform:
                    pv_geom = QgsGeometry(pv_geom)
                    pv_geom.transform(transform)
                pv_geom_cache[pv_feat.id()] = pv_geom
                feat_for_index = QgsFeature(pv_feat)
                feat_for_index.setGeometry(pv_geom)
                pv_index.addFeature(feat_for_index)

        if include_conformes:
            self._pv_index_all = pv_index
            self._pv_geom_cache_all = pv_geom_cache
        elif only_visit_or_contre:
            self._pv_index_nonconf_visit = pv_index
            self._pv_geom_cache_nonconf_visit = pv_geom_cache
        else:
            self._pv_index_nonconf = pv_index
            self._pv_geom_cache_nonconf = pv_geom_cache

        return pv_index, pv_geom_cache

    # ------------------------------------------------------------------
    # Sélection via nœuds atteints
    # ------------------------------------------------------------------
    def select_pv_from_nodes(
        self,
        nodes: Set[str],
        distance: float = 15.0,
        include_conformes: bool = False,
        only_visit_or_contre: bool = False
    ) -> List[int]:
        """
        À partir d'un ensemble de nœuds, sélectionne les PV dans un rayon donné
        et renvoie la liste de leurs FIDs.
        
        Args:
            nodes: Ensemble de nœuds du réseau (ex: {"N_12345", "N_67890"})
            distance: Distance de recherche en mètres (défaut: 15m)
        
        Returns:
            Liste des FIDs des PV sélectionnés
        """
        if not self.pv_layer or not self.canal_layer or not nodes:
            if self.pv_layer:
                self.pv_layer.removeSelection()
            return []

        # Récupérer toutes les canalisations liées à ces nœuds
        canal_ids = self._get_canals_from_nodes(nodes)
        
        if not canal_ids:
            self.pv_layer.removeSelection()
            return []

        # Trouver les PV proches de ces canalisations
        pv_fids = self._find_pv_near_canals(canal_ids, distance, include_conformes, only_visit_or_contre)
        
        # Sélectionner les PV dans la couche
        self.pv_layer.removeSelection()
        if pv_fids:
            self.pv_layer.selectByIds(pv_fids)

        return pv_fids

    def _get_canals_from_nodes(self, nodes: Set[str]) -> Set[int]:
        """
        Récupère les FIDs des canalisations connectées aux nœuds donnés.
        """
        canal_ids: Set[int] = set()

        if not self.canal_layer or not self.canal_layer.isValid():
            return canal_ids

        by_node = self._build_node_to_canal_cache()
        for node in nodes:
            nid = str(node or '').strip()
            if not nid:
                continue
            canal_ids.update(by_node.get(nid, set()))

        return canal_ids

    def _find_pv_near_canals(
        self,
        canal_ids: Set[int],
        distance: float,
        include_conformes: bool,
        only_visit_or_contre: bool
    ) -> List[int]:
        """
        Trouve les PV dans un rayon autour des canalisations données.
        Gère automatiquement les différences de CRS (4326 vs 2154).
        
        Args:
            canal_ids: Set des FIDs de canalisations
            distance: Distance de recherche en mètres
        
        Returns:
            Liste des FIDs de PV trouvés
        """
        if not self.pv_layer or not self.canal_layer:
            return []

        pv_fids = []
        
        # Préparer la transformation CRS si nécessaire
        canal_crs = self.canal_layer.crs()
        pv_crs = self.pv_layer.crs()
        transform = None
        
        if canal_crs != pv_crs:
            transform = QgsCoordinateTransform(pv_crs, canal_crs, QgsProject.instance())

        # Cas métier "cheminement pollution": on doit considérer la DERNIÈRE visite/contre-visite
        # (conforme OU non conforme), puis garder uniquement les dernières non conformes.
        effective_include_conformes = include_conformes or only_visit_or_contre

        # Construire/relire un index spatial PV cache pour accélérer les recherches
        pv_index, pv_geom_cache = self._build_pv_spatial_cache(
            effective_include_conformes, transform, canal_crs.authid(), only_visit_or_contre
        )

        # Pour chaque canalisation, chercher les PV proches
        req_canals = QgsFeatureRequest().setFilterFids(list(canal_ids))
        
        candidate_fids: Set[int] = set()
        for canal_feat in self.canal_layer.getFeatures(req_canals):
            canal_geom = canal_feat.geometry()
            if not canal_geom:
                continue

            # Créer un buffer autour de la canalisation (dans le CRS du canal)
            buffer_geom = canal_geom.buffer(distance, 8)

            candidate_ids = pv_index.intersects(buffer_geom.boundingBox())
            for fid in candidate_ids:
                pv_geom = pv_geom_cache.get(fid)
                if pv_geom and buffer_geom.intersects(pv_geom):
                    candidate_fids.add(fid)

        if not candidate_fids:
            return []

        # Règle métier: pour chaque établissement/support, seul le dernier point (visite/contre-visite) compte.
        if only_visit_or_contre:
            return self._latest_non_conforme_fids(candidate_fids)

        # Cas standard: on garde simplement les candidats (avec filtre conformité selon include_conformes)
        pv_fids = sorted(candidate_fids)

        return pv_fids

    def connected_ids_from_nodes(
        self,
        nodes: Set[str],
        distance: float = 15.0,
        include_conformes: bool = False,
        only_visit_or_contre: bool = False
    ) -> List[str]:
        """
        Raccourci : à partir des nœuds → sélectionner PV → renvoyer IDs texte.
        
        Args:
            nodes: Ensemble de nœuds du réseau
            distance: Distance de recherche en mètres
        
        Returns:
            Liste des IDs texte des PV (colonne 'id' ou 'num_pv')
        """
        fids = self.select_pv_from_nodes(nodes, distance, include_conformes, only_visit_or_contre)
        
        if not fids or not self.pv_layer:
            return []

        # Récupérer les IDs texte depuis les features
        ids = []
        req = QgsFeatureRequest().setFilterFids(fids)
        
        for feat in self.pv_layer.getFeatures(req):
            if not include_conformes and not self._is_non_conforme(feat):
                continue
            if only_visit_or_contre and not self._is_visit_or_contre(feat):
                continue
            # Essayer plusieurs noms de colonnes possibles
            pv_id = None
            for field_name in ['id', 'num_pv', 'ID', 'NUM_PV']:
                if feat.fields().indexOf(field_name) >= 0:
                    pv_id = feat.attribute(field_name)
                    if pv_id:
                        break
            
            if pv_id:
                ids.append(str(pv_id))

        return ids

    # ------------------------------------------------------------------
    # Récupération d'infos
    # ------------------------------------------------------------------
    def fetch(self, pv_id: str, include_conformes: bool = False) -> Dict[str, str]:
        """
        Renvoie un dictionnaire {champ: valeur} pour un PV donné.
        
        Args:
            pv_id: ID du PV (colonne 'id' ou 'num_pv')
        
        Returns:
            Dictionnaire avec tous les champs du PV
        """
        if not self.pv_layer:
            return {}

        # Essayer plusieurs noms de colonnes
        for field_name in ['id', 'num_pv', 'ID', 'NUM_PV']:
            if self.pv_layer.fields().indexOf(field_name) >= 0:
                expr = QgsExpression("\"{}\" = '{}'".format(
                    field_name, 
                    str(pv_id).replace("'", "''")
                ))
                req = QgsFeatureRequest(expr)

                for f in self.pv_layer.getFeatures(req):
                    if not include_conformes and not self._is_non_conforme(f):
                        return {}
                    out: Dict[str, str] = {}
                    for name in f.fields().names():
                        out[name] = self._to_text_value(f[name])

                    # Normaliser les noms de champs
                    out.setdefault("id", str(pv_id))
                    out.setdefault("num_pv", out.get("num_pv", pv_id))
                    
                    return out

        return {}

    def fetch_many(
        self,
        ids: List[str],
        include_conformes: bool = False
    ) -> Dict[str, Dict[str, str]]:
        """
        Renvoie {pv_id: {champ: valeur, ...}, ...}
        
        Args:
            ids: Liste des IDs de PV
        
        Returns:
            Dictionnaire {id: données}
        """
        out: Dict[str, Dict[str, str]] = {}
        for pv_id in ids:
            out[pv_id] = self.fetch(pv_id, include_conformes=include_conformes)
        return out

    def get_distance_to_network(self, pv_id: str) -> Optional[float]:
        """
        Calcule la distance entre un PV et le réseau de canalisations le plus proche.
        
        Args:
            pv_id: ID du PV
        
        Returns:
            Distance en mètres, ou None si impossible à calculer
        """
        if not self.pv_layer or not self.canal_layer:
            return None

        # Trouver le PV
        pv_geom = None
        for field_name in ['id', 'num_pv', 'ID', 'NUM_PV']:
            if self.pv_layer.fields().indexOf(field_name) >= 0:
                expr = QgsExpression("\"{}\" = '{}'".format(
                    field_name, 
                    str(pv_id).replace("'", "''")
                ))
                req = QgsFeatureRequest(expr)
                
                for feat in self.pv_layer.getFeatures(req):
                    pv_geom = feat.geometry()
                    break
                
                if pv_geom:
                    break

        if not pv_geom:
            return None

        # Transformer dans le CRS du canal si nécessaire
        canal_crs = self.canal_layer.crs()
        pv_crs = self.pv_layer.crs()
        
        if canal_crs != pv_crs:
            transform = QgsCoordinateTransform(pv_crs, canal_crs, QgsProject.instance())
            pv_geom = QgsGeometry(pv_geom)
            pv_geom.transform(transform)

        # Trouver la canalisation la plus proche (index spatial)
        canal_index, canal_geom_cache = self._build_canal_spatial_cache()

        try:
            pv_point = pv_geom.asPoint()
        except Exception:
            cent = pv_geom.centroid() if pv_geom else None
            pv_point = cent.asPoint() if cent else None
        if not pv_point:
            return None

        nearest = canal_index.nearestNeighbor(pv_point, 8) if canal_index else []
        min_distance = float('inf')
        for fid in nearest:
            canal_geom = canal_geom_cache.get(fid)
            if not canal_geom:
                continue
            dist = pv_geom.distance(canal_geom)
            if dist < min_distance:
                min_distance = dist

        # fallback si index vide
        if min_distance == float('inf'):
            for canal_feat in self.canal_layer.getFeatures():
                canal_geom = canal_feat.geometry()
                if canal_geom:
                    dist = pv_geom.distance(canal_geom)
                    if dist < min_distance:
                        min_distance = dist

        return round(min_distance, 2) if min_distance != float('inf') else None

    def _is_non_conforme(self, feat) -> bool:
        """Retourne True si le PV est non conforme ou si l'info est absente."""
        for field_name in ["conforme", "conformite", "conformité", "conform"]:
            if feat.fields().indexOf(field_name) >= 0:
                val = feat.attribute(field_name)
                sval = str(val or "").strip().lower()
                if sval in ("oui", "yes", "true", "1"):
                    return False
                return True
        return True

    def _is_visit_or_contre(self, feat) -> bool:
        """Retourne True si le type PV est VISITE ou CONTRE VISITE."""
        for field_name in ["type_visite", "type", "nature_visite", "typ_visite"]:
            if feat.fields().indexOf(field_name) >= 0:
                sval = str(feat.attribute(field_name) or "").strip().upper().replace("-", " ")
                sval = " ".join(sval.split())
                return sval in ("VISITE", "CONTRE VISITE")
        # Si champ absent, ne pas exclure par défaut (compat datasets)
        return True

    def _to_text_value(self, val) -> str:
        """Normalise les valeurs pour éviter les formats PyQt (QDate/QDateTime) dans UI/rapports."""
        if val is None:
            return ""
        if hasattr(val, "toString"):
            # QDate / QDateTime / QTime
            try:
                txt = val.toString("yyyy-MM-dd HH:mm:ss")
                if txt and txt != "  ::":
                    return txt.strip()
            except Exception:
                pass
            try:
                txt = val.toString("yyyy-MM-dd")
                if txt:
                    return txt.strip()
            except Exception:
                pass
        sval = str(val).strip()
        # Exemple: PyQt5.QtCore.QDate(2024, 4, 9)
        m = re.match(r".*QDate\((\d{4}),\s*(\d{1,2}),\s*(\d{1,2})\).*", sval)
        if m:
            y, mo, d = m.groups()
            return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
        return sval

    def _date_rank(self, feat) -> tuple:
        """
        Retourne une clé de tri date robuste (dernier point = max).
        Supporte QDate/QDateTime, datetime, et chaînes fréquentes.
        """
        candidates = [
            "date_visite", "date_contre_visite", "date_observation", "date_pv",
            "date", "date_saisie", "created_at", "updated_at"
        ]
        best = datetime.datetime.min
        for field_name in candidates:
            if feat.fields().indexOf(field_name) < 0:
                continue
            raw = feat.attribute(field_name)
            dt = self._parse_date(raw)
            if dt and dt > best:
                best = dt
        return (best, feat.id())

    def _parse_date(self, raw) -> Optional[datetime.datetime]:
        if raw is None:
            return None
        if isinstance(raw, datetime.datetime):
            return raw
        if isinstance(raw, datetime.date):
            return datetime.datetime(raw.year, raw.month, raw.day)
        if hasattr(raw, "toPyDateTime"):
            try:
                return raw.toPyDateTime()
            except Exception:
                pass
        if hasattr(raw, "toPyDate"):
            try:
                d = raw.toPyDate()
                return datetime.datetime(d.year, d.month, d.day)
            except Exception:
                pass
        sval = self._to_text_value(raw)
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M:%S"):
            try:
                return datetime.datetime.strptime(sval, fmt)
            except Exception:
                continue
        return None

    def _establishment_key(self, feat) -> str:
        """Clé regroupement établissement/maison pour règle 'dernier point fait foi'."""
        fields = [
            "id_etablissement", "id_etab", "id_batiment", "id_maison",
            "id_ouvrage", "adresse", "num_pv", "id"
        ]
        for name in fields:
            if feat.fields().indexOf(name) >= 0:
                v = str(feat.attribute(name) or "").strip()
                if v:
                    return f"{name}:{v}"
        g = feat.geometry()
        if g:
            try:
                p = g.asPoint()
                return f"geom:{round(p.x(), 3)}:{round(p.y(), 3)}"
            except Exception:
                pass
        return f"fid:{feat.id()}"

    def _latest_non_conforme_fids(self, candidate_fids: Set[int]) -> List[int]:
        """
        Règle métier:
        - regrouper par établissement/maison,
        - garder la DERNIÈRE visite/contre-visite,
        - sélectionner seulement si cette dernière est non conforme.
        """
        if not self.pv_layer or not candidate_fids:
            return []
        latest_by_key: Dict[str, QgsFeature] = {}
        req = QgsFeatureRequest().setFilterFids(list(candidate_fids))
        for feat in self.pv_layer.getFeatures(req):
            if not self._is_visit_or_contre(feat):
                continue
            k = self._establishment_key(feat)
            cur = latest_by_key.get(k)
            if cur is None or self._date_rank(feat) > self._date_rank(cur):
                latest_by_key[k] = feat
        out: List[int] = []
        for feat in latest_by_key.values():
            if self._is_non_conforme(feat):
                out.append(feat.id())
        return sorted(out)
