# -*- coding: utf-8 -*-
# OPTIMISATIONS pour main_dock.py - Module de performance pour la désélection de nœuds
# Ce module contient les fonctions optimisées à intégrer dans MainDock

from typing import Dict, List, Optional, Set, Tuple
from qgis.core import QgsFeature, QgsFeatureRequest, QgsVectorLayer, QgsExpression


class OptimizedNodeOps:
    """
    Classe contenant les opérations optimisées pour la désélection de nœuds.
    Utilise des caches pour minimiser les requêtes répétées.
    """
    
    def __init__(self, canal_layer, fosse_layer, liaison_layer, indus_layer):
        self.canal_layer = canal_layer
        self.fosse_layer = fosse_layer
        self.liaison_layer = liaison_layer
        self.indus_layer = indus_layer
        
        # Caches pour optimisation
        self._incoming_cache: Optional[Dict[str, List[Tuple[str, QgsVectorLayer, QgsFeature]]]] = None
        self._outgoing_cache: Optional[Dict[str, List[Tuple[str, QgsVectorLayer, QgsFeature]]]] = None
        self._liaison_by_node: Optional[Dict[str, List[QgsFeature]]] = None
        self._indus_feat_cache: Optional[Dict[str, QgsFeature]] = None
    
    def invalidate_caches(self):
        """Invalide tous les caches."""
        self._incoming_cache = None
        self._outgoing_cache = None
        self._liaison_by_node = None
        self._indus_feat_cache = None
    
    def build_incoming_cache(self) -> Dict[str, List[Tuple[str, QgsVectorLayer, QgsFeature]]]:
        """Construit un cache des arêtes entrantes pour tous les nœuds (amont)."""
        if self._incoming_cache is not None:
            return self._incoming_cache
        
        cache: Dict[str, List[Tuple[str, QgsVectorLayer, QgsFeature]]] = {}
        
        # Canal layer - éditer pour éviter requêtes répétées
        if self.canal_layer and self.canal_layer.isValid():
            for f in self.canal_layer.getFeatures():
                try:
                    idnini = (f['idnini'] or "").strip()
                    idnterm = (f['idnterm'] or "").strip()
                    if idnini != 'INCONNU' and idnterm != 'INCONNU' and idnterm:
                        if idnterm not in cache:
                            cache[idnterm] = []
                        # Dupliquer le feature pour éviter problèmes de référence
                        cache[idnterm].append(("canal", self.canal_layer, QgsFeature(f)))
                except Exception:
                    continue
        
        # Fosse layer
        if self.fosse_layer and self.fosse_layer.isValid():
            for f in self.fosse_layer.getFeatures():
                try:
                    idnini = (f['idnini'] or "").strip()
                    idnterm = (f['idnterm'] or "").strip()
                    if idnini != 'INCONNU' and idnterm != 'INCONNU' and idnterm:
                        if idnterm not in cache:
                            cache[idnterm] = []
                        cache[idnterm].append(("fosse", self.fosse_layer, QgsFeature(f)))
                except Exception:
                    continue
        
        self._incoming_cache = cache
        return cache
    
    def build_outgoing_cache(self) -> Dict[str, List[Tuple[str, QgsVectorLayer, QgsFeature]]]:
        """Construit un cache des arêtes sortantes pour tous les nœuds (aval)."""
        if self._outgoing_cache is not None:
            return self._outgoing_cache
        
        cache: Dict[str, List[Tuple[str, QgsVectorLayer, QgsFeature]]] = {}
        
        # Canal layer
        if self.canal_layer and self.canal_layer.isValid():
            for f in self.canal_layer.getFeatures():
                try:
                    idnini = (f['idnini'] or "").strip()
                    idnterm = (f['idnterm'] or "").strip()
                    if idnini != 'INCONNU' and idnterm != 'INCONNU' and idnini:
                        if idnini not in cache:
                            cache[idnini] = []
                        cache[idnini].append(("canal", self.canal_layer, QgsFeature(f)))
                except Exception:
                    continue
        
        # Fosse layer
        if self.fosse_layer and self.fosse_layer.isValid():
            for f in self.fosse_layer.getFeatures():
                try:
                    idnini = (f['idnini'] or "").strip()
                    idnterm = (f['idnterm'] or "").strip()
                    if idnini != 'INCONNU' and idnterm != 'INCONNU' and idnini:
                        if idnini not in cache:
                            cache[idnini] = []
                        cache[idnini].append(("fosse", self.fosse_layer, QgsFeature(f)))
                except Exception:
                    continue
        
        self._outgoing_cache = cache
        return cache
    
    def build_liaison_cache(self) -> Dict[str, List[QgsFeature]]:
        """Construit un cache des liaisons par ouvrage."""
        if self._liaison_by_node is not None:
            return self._liaison_by_node
        
        cache: Dict[str, List[QgsFeature]] = {}
        
        if self.liaison_layer and self.liaison_layer.isValid():
            for f in self.liaison_layer.getFeatures():
                try:
                    id_ouvr = (f['id_ouvrage'] or "").strip()
                    if id_ouvr and id_ouvr.upper() != 'INCONNU':
                        if id_ouvr not in cache:
                            cache[id_ouvr] = []
                        cache[id_ouvr].append(QgsFeature(f))
                except Exception:
                    continue
        
        self._liaison_by_node = cache
        return cache
    
    def walk_upstream_mixed_optimized(self, start_node: Optional[str]) -> Tuple[Set[int], Set[int], Set[str]]:
        """Version optimisée du parcours amont avec cache."""
        if not start_node:
            return set(), set(), set()
        
        # Construire le cache une seule fois
        incoming_cache = self.build_incoming_cache()
        
        seen_nodes: Set[str] = set()
        cids: Set[int] = set()
        fids: Set[int] = set()
        stack = [str(start_node)]
        
        while stack:
            cur = stack.pop()
            if cur in seen_nodes:
                continue
            seen_nodes.add(cur)
            
            # Utiliser le cache au lieu de requêtes
            edges = incoming_cache.get(cur, [])
            for typ, layer, feat in edges:
                fid = feat.id()
                if typ == "canal":
                    if fid in cids:
                        continue
                    cids.add(fid)
                else:
                    if fid in fids:
                        continue
                    fids.add(fid)
                
                try:
                    nxt = (feat['idnini'] or "").strip()
                    if nxt and nxt.upper() != "INCONNU":
                        stack.append(str(nxt))
                except Exception:
                    pass
        
        return cids, fids, seen_nodes
    
    def walk_downstream_mixed_optimized(self, start_node: Optional[str]) -> Tuple[Set[int], Set[int], Set[str]]:
        """Version optimisée du parcours aval avec cache."""
        if not start_node:
            return set(), set(), set()
        
        # Construire le cache une seule fois
        outgoing_cache = self.build_outgoing_cache()
        
        seen_nodes: Set[str] = set()
        cids: Set[int] = set()
        fids: Set[int] = set()
        stack = [str(start_node).strip()]
        
        while stack:
            cur = stack.pop()
            if cur in seen_nodes:
                continue
            seen_nodes.add(cur)
            
            # Utiliser le cache
            edges = outgoing_cache.get(cur, [])
            for typ, layer, feat in edges:
                fid = feat.id()
                if typ == "canal":
                    if fid in cids:
                        continue
                    cids.add(fid)
                else:
                    if fid in fids:
                        continue
                    fids.add(fid)
                
                try:
                    nxt = (feat['idnterm'] or "").strip()
                    if nxt and nxt.upper() != "INCONNU":
                        stack.append(str(nxt))
                except Exception:
                    pass
        
        return cids, fids, seen_nodes
    
    def walk_upstream_on_selected_optimized(self, start_node: Optional[str], 
                                           sel_c: Set[int], sel_f: Set[int]) -> Tuple[Set[int], Set[int], Set[str]]:
        """Parcours amont limité à la sélection (optimisé)."""
        if not start_node:
            return set(), set(), set()
        
        incoming_cache = self.build_incoming_cache()
        
        seen_nodes: Set[str] = set()
        cids: Set[int] = set()
        fids: Set[int] = set()
        stack = [str(start_node).strip()]
        
        while stack:
            cur = stack.pop()
            if cur in seen_nodes:
                continue
            seen_nodes.add(cur)
            
            edges = incoming_cache.get(cur, [])
            for typ, layer, feat in edges:
                fid = feat.id()
                if typ == "canal":
                    if fid not in sel_c or fid in cids:
                        continue
                    cids.add(fid)
                else:
                    if fid not in sel_f or fid in fids:
                        continue
                    fids.add(fid)
                
                try:
                    nxt = (feat['idnini'] or "").strip()
                    if nxt and nxt.upper() != "INCONNU":
                        stack.append(str(nxt))
                except Exception:
                    pass
        
        return cids, fids, seen_nodes
    
    def walk_downstream_on_selected_optimized(self, start_node: Optional[str],
                                              sel_c: Set[int], sel_f: Set[int]) -> Tuple[Set[int], Set[int], Set[str]]:
        """Parcours aval limité à la sélection (optimisé)."""
        if not start_node:
            return set(), set(), set()
        
        outgoing_cache = self.build_outgoing_cache()
        
        seen_nodes: Set[str] = set()
        cids: Set[int] = set()
        fids: Set[int] = set()
        stack = [str(start_node).strip()]
        
        while stack:
            cur = stack.pop()
            if cur in seen_nodes:
                continue
            seen_nodes.add(cur)
            
            edges = outgoing_cache.get(cur, [])
            for typ, layer, feat in edges:
                fid = feat.id()
                if typ == "canal":
                    if fid not in sel_c or fid in cids:
                        continue
                    cids.add(fid)
                else:
                    if fid not in sel_f or fid in fids:
                        continue
                    fids.add(fid)
                
                try:
                    nxt = (feat['idnterm'] or "").strip()
                    if nxt and nxt.upper() != "INCONNU":
                        stack.append(str(nxt))
                except Exception:
                    pass
        
        return cids, fids, seen_nodes
    
    def deselect_liaisons_and_indus_from_nodes_optimized(self, nodes: Set[str]) -> Set[str]:
        """
        Désélectionne liaisons et industriels depuis un ensemble de nœuds (OPTIMISÉ).
        Utilise un cache pour éviter les multiples getFeature().
        """
        removed_indus: Set[str] = set()
        if not nodes or not self.liaison_layer:
            return removed_indus
        
        # Construire le cache des liaisons si pas déjà fait
        liaison_cache = self.build_liaison_cache()
        
        lids_to_deselect: List[int] = []
        
        # Parcourir les nœuds et collecter les liaisons + indus
        for node in nodes:
            node = (node or "").strip()
            if not node:
                continue
            
            liaisons = liaison_cache.get(node, [])
            for lf in liaisons:
                lids_to_deselect.append(lf.id())
                try:
                    iid = lf['id_industriel']
                    if iid and str(iid).upper() != 'INCONNU':
                        removed_indus.add(str(iid))
                except Exception:
                    pass
        
        # Désélectionner les liaisons en une seule fois
        if lids_to_deselect:
            self.liaison_layer.deselect(lids_to_deselect)
        
        # Désélectionner les industriels en batch
        if self.indus_layer and removed_indus:
            esc = lambda s: (s or "").replace("'", "''")
            values = ",".join("'{}'".format(esc(i)) for i in removed_indus if i)
            if values:
                exprI = QgsExpression("trim(\"id\") IN ({})".format(values))
                reqI = QgsFeatureRequest(exprI)
                rem_ids = [f.id() for f in self.indus_layer.getFeatures(reqI)]
                if rem_ids:
                    self.indus_layer.deselect(rem_ids)
        
        return removed_indus
    
    def bulk_deselect_unselected_branches_optimized(
        self, 
        start_node: str,
        branches: List[Tuple[str, int, Optional[str], Optional[str]]],
        chosen_ids: Set[int]
    ) -> Set[str]:
        """
        Désélectionne tout l'amont pour les branches NON cochées (VERSION OPTIMISÉE).
        Utilise les caches pour accélérer les parcours.
        """
        removed_cids: Set[int] = set()
        removed_fids: Set[int] = set()
        removed_lids: Set[int] = set()
        removed_nodes: Set[str] = set()
        removed_indus: Set[str] = set()
        
        # Construire les caches une seule fois
        liaison_cache = self.build_liaison_cache()
        
        for typ, fid, amont, indus in branches:
            if fid in chosen_ids:
                continue
            
            if typ == "canal":
                removed_cids.add(fid)
                cids, fids, nodes = self.walk_upstream_mixed_optimized(amont)
                removed_cids.update(cids)
                removed_fids.update(fids)
                removed_nodes.update(nodes)
            elif typ == "fosse":
                removed_fids.add(fid)
                cids, fids, nodes = self.walk_upstream_mixed_optimized(amont)
                removed_cids.update(cids)
                removed_fids.update(fids)
                removed_nodes.update(nodes)
            else:  # liaison
                removed_lids.add(fid)
                if indus:
                    removed_indus.add(str(indus))
        
        # Désélectionner en batch
        if self.canal_layer and removed_cids:
            self.canal_layer.deselect(list(removed_cids))
        if self.fosse_layer and removed_fids:
            self.fosse_layer.deselect(list(removed_fids))
        
        # Liaisons amont + indus (depuis tous les nœuds collectés) - VERSION OPTIMISÉE
        ids_to_unselect = list(removed_lids)
        
        # Utiliser le cache pour les liaisons
        for node in removed_nodes:
            node = (node or "").strip()
            if not node:
                continue
            liaisons = liaison_cache.get(node, [])
            for lf in liaisons:
                lid = lf.id()
                if lid not in ids_to_unselect:
                    ids_to_unselect.append(lid)
                try:
                    iid = lf['id_industriel']
                    if iid and str(iid).upper() != 'INCONNU':
                        removed_indus.add(str(iid))
                except Exception:
                    pass
        
        # Désélectionner toutes les liaisons en une fois
        if self.liaison_layer and ids_to_unselect:
            self.liaison_layer.deselect(ids_to_unselect)
        
        # Désélectionner les industriels en batch
        if self.indus_layer and removed_indus:
            esc = lambda s: (s or "").replace("'", "''")
            values = ",".join("'{}'".format(esc(i)) for i in removed_indus if i)
            if values:
                exprI = QgsExpression("trim(\"id\") IN ({})".format(values))
                reqI = QgsFeatureRequest(exprI)
                rem_ids = [f.id() for f in self.indus_layer.getFeatures(reqI)]
                if rem_ids:
                    self.indus_layer.deselect(rem_ids)
        
        return removed_indus
