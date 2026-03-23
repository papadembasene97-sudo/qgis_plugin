# cheminer_indus/core/tracer.py

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set, Tuple

from qgis.core import (
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
    QgsVectorLayer,
)


def _as_str(v) -> str:
    if v is None:
        return ""
    return str(v)


class NetworkTracer:
    """
    Traçage unifié sur 2 couches linéaires formant UN SEUL graphe topologique.
    Version optimisée: construit un graphe en mémoire pour éviter les requêtes
    provider répétées à chaque nœud parcouru.
    """

    def __init__(
        self,
        canal_layer: QgsVectorLayer,
        fosse_layer: Optional[QgsVectorLayer] = None,
        field_alias: Optional[Dict[str, Iterable[str]]] = None,
        filters: Optional[Dict[str, str]] = None,
    ):
        self.canal_layer = canal_layer
        self.fosse_layer = fosse_layer if (fosse_layer and fosse_layer.isValid()) else None
        self.filters = filters or {"category": "", "function": ""}

        self.alias: Dict[str, List[str]] = {
            "cat": ["contcanass", "categorie", "cat_reseau"],
            "func": ["fonccanass", "fonction", "function"],
            "type": ["typreseau", "type_reseau"],
            "len": ["l_longcana_reelle", "longueur", "length"],
        }
        if field_alias:
            for k, v in field_alias.items():
                if v:
                    self.alias[k] = list(v)

        self._layer_field_name_cache: Dict[str, Dict[str, Optional[str]]] = {}

        # Graph caches: node -> list[(is_canal, fid, next_node, length, flux_type)]
        self._graph_out: Optional[Dict[str, List[Tuple[bool, int, str, float, Optional[str]]]]] = None
        self._graph_in: Optional[Dict[str, List[Tuple[bool, int, str, float, Optional[str]]]]] = None

        self.total_length: float = 0.0
        self.flux_types: Set[str] = set()

        self.canal_ids: List[int] = []
        self.fosse_ids: List[int] = []

    def _layer_id(self, layer: QgsVectorLayer) -> str:
        return layer.id()

    def _resolve_field_name(self, layer: QgsVectorLayer, key: str) -> Optional[str]:
        lid = self._layer_id(layer)
        cache = self._layer_field_name_cache.setdefault(lid, {})
        if key in cache:
            return cache[key]

        wanted = self.alias.get(key, [])
        names = set(layer.fields().names())
        for cand in wanted:
            if cand in names:
                cache[key] = cand
                return cand
        cache[key] = None
        return None

    def _feat_val_by_key(self, layer: QgsVectorLayer, feat: QgsFeature, key: str) -> Optional[str]:
        fname = self._resolve_field_name(layer, key)
        if not fname:
            return None
        try:
            val = feat[fname]
        except Exception:
            return None
        return _as_str(val) if val not in (None, "") else None

    def _len_of(self, layer: QgsVectorLayer, feat: QgsFeature) -> float:
        fname = self._resolve_field_name(layer, "len")
        if fname:
            try:
                v = feat[fname]
                if v not in (None, ""):
                    return float(v)
            except Exception:
                pass
        g: QgsGeometry = feat.geometry()
        return float(g.length() if g else 0.0)

    def _pass_filters(self, layer: QgsVectorLayer, feat: QgsFeature) -> bool:
        fcat = (self.filters.get("category") or "").strip()
        ffun = (self.filters.get("function") or "").strip()

        if fcat:
            cat = self._feat_val_by_key(layer, feat, "cat")
            if cat is not None and cat != fcat:
                return False

        if ffun:
            fun = self._feat_val_by_key(layer, feat, "func")
            if fun is not None and fun != ffun:
                return False

        return True

    def _ensure_graph_cache(self):
        if self._graph_out is not None and self._graph_in is not None:
            return

        out: Dict[str, List[Tuple[bool, int, str, float, Optional[str]]]] = {}
        inn: Dict[str, List[Tuple[bool, int, str, float, Optional[str]]]] = {}

        layers: List[Tuple[bool, QgsVectorLayer]] = []
        if self.canal_layer and self.canal_layer.isValid():
            layers.append((True, self.canal_layer))
        if self.fosse_layer and self.fosse_layer.isValid():
            layers.append((False, self.fosse_layer))

        for is_canal, lyr in layers:
            for feat in lyr.getFeatures():
                try:
                    names = feat.fields().names()
                    idnini = _as_str(feat["idnini"]).strip() if "idnini" in names else ""
                    idnterm = _as_str(feat["idnterm"]).strip() if "idnterm" in names else ""
                    if not idnini or not idnterm:
                        continue
                    if idnini.upper() == "INCONNU" or idnterm.upper() == "INCONNU":
                        continue
                    if not self._pass_filters(lyr, feat):
                        continue

                    edge_out = (is_canal, feat.id(), idnterm, self._len_of(lyr, feat), self._feat_val_by_key(lyr, feat, "type"))
                    out.setdefault(idnini, []).append(edge_out)

                    edge_in = (is_canal, feat.id(), idnini, self._len_of(lyr, feat), self._feat_val_by_key(lyr, feat, "type"))
                    inn.setdefault(idnterm, []).append(edge_in)
                except Exception:
                    continue

        self._graph_out = out
        self._graph_in = inn

    def trace(
        self,
        start_id: str,
        downstream: bool = True,
        max_distance: Optional[float] = None,
    ) -> Tuple[List[int], List[int]]:
        self.total_length = 0.0
        self.flux_types.clear()

        self._ensure_graph_cache()
        graph = self._graph_out if downstream else self._graph_in

        import heapq

        best_dist: Dict[str, float] = {start_id: 0.0}
        queue: List[Tuple[float, str]] = [(0.0, start_id)]

        seen_edge_ids: Set[int] = set()
        canal_ids: List[int] = []
        fosse_ids: List[int] = []

        while queue:
            cur_dist, cur = heapq.heappop(queue)
            if cur_dist > best_dist.get(cur, float("inf")):
                continue

            for is_canal, fid, nxt, length, flux_type in graph.get(cur, []) if graph else []:
                next_dist = cur_dist + float(length or 0.0)
                if max_distance is not None and next_dist > float(max_distance):
                    continue

                if fid not in seen_edge_ids:
                    seen_edge_ids.add(fid)
                    if is_canal:
                        canal_ids.append(fid)
                    else:
                        fosse_ids.append(fid)
                    self.total_length += float(length or 0.0)
                    if flux_type:
                        self.flux_types.add(flux_type)

                if nxt and nxt != "INCONNU":
                    if next_dist < best_dist.get(nxt, float("inf")):
                        best_dist[nxt] = next_dist
                        heapq.heappush(queue, (next_dist, nxt))

        self.canal_ids = canal_ids
        self.fosse_ids = fosse_ids
        return canal_ids, fosse_ids

    def trace_from_pv(
        self,
        pv_geometry: QgsGeometry,
        downstream: bool = True,
        search_distance: float = 50.0
    ) -> Tuple[List[int], List[int], Optional[str]]:
        closest_canal = None
        min_distance = search_distance

        bbox = pv_geometry.buffer(search_distance, 5).boundingBox()
        request = QgsFeatureRequest().setFilterRect(bbox)
        for feat in self.canal_layer.getFeatures(request):
            geom = feat.geometry()
            if not geom or geom.isEmpty():
                continue
            distance = pv_geometry.distance(geom)
            if distance < min_distance:
                min_distance = distance
                closest_canal = feat

        if not closest_canal:
            return [], [], None

        if downstream:
            start_node_id = _as_str(closest_canal.attribute("idnini"))
        else:
            start_node_id = _as_str(closest_canal.attribute("idnterm"))

        if not start_node_id or start_node_id == "INCONNU":
            return [], [], None

        canal_ids, fosse_ids = self.trace(start_node_id, downstream=downstream)
        return canal_ids, fosse_ids, start_node_id
