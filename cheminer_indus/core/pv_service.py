# -*- coding: utf-8 -*-
# cheminer_indus/core/pv_service.py

from __future__ import annotations
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


    def invalidate_caches(self):
        """Invalide les caches (à appeler si les couches changent)."""
        self._canal_ids_by_node = None
        self._pv_index_all = None
        self._pv_geom_cache_all = None
        self._pv_index_nonconf = None
        self._pv_geom_cache_nonconf = None

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

    def _build_pv_spatial_cache(self, include_conformes: bool, transform: Optional[QgsCoordinateTransform]):
        if include_conformes and self._pv_index_all is not None and self._pv_geom_cache_all is not None:
            return self._pv_index_all, self._pv_geom_cache_all
        if (not include_conformes) and self._pv_index_nonconf is not None and self._pv_geom_cache_nonconf is not None:
            return self._pv_index_nonconf, self._pv_geom_cache_nonconf

        pv_index = QgsSpatialIndex()
        pv_geom_cache: Dict[int, QgsGeometry] = {}

        if self.pv_layer and self.pv_layer.isValid():
            for pv_feat in self.pv_layer.getFeatures():
                if not include_conformes and not self._is_non_conforme(pv_feat):
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
        include_conformes: bool = False
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
        pv_fids = self._find_pv_near_canals(canal_ids, distance, include_conformes)
        
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
        include_conformes: bool
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

        # Construire/relire un index spatial PV cache pour accélérer les recherches
        pv_index, pv_geom_cache = self._build_pv_spatial_cache(include_conformes, transform)

        # Pour chaque canalisation, chercher les PV proches
        req_canals = QgsFeatureRequest().setFilterFids(list(canal_ids))
        
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
                    if fid not in pv_fids:
                        pv_fids.append(fid)

        return pv_fids

    def connected_ids_from_nodes(
        self,
        nodes: Set[str],
        distance: float = 15.0,
        include_conformes: bool = False
    ) -> List[str]:
        """
        Raccourci : à partir des nœuds → sélectionner PV → renvoyer IDs texte.
        
        Args:
            nodes: Ensemble de nœuds du réseau
            distance: Distance de recherche en mètres
        
        Returns:
            Liste des IDs texte des PV (colonne 'id' ou 'num_pv')
        """
        fids = self.select_pv_from_nodes(nodes, distance, include_conformes)
        
        if not fids or not self.pv_layer:
            return []

        # Récupérer les IDs texte depuis les features
        ids = []
        req = QgsFeatureRequest().setFilterFids(fids)
        
        for feat in self.pv_layer.getFeatures(req):
            if not include_conformes and not self._is_non_conforme(feat):
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
                        out[name] = "" if f[name] is None else str(f[name])

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

        # Trouver la canalisation la plus proche
        min_distance = float('inf')
        
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
