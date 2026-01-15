# cheminer_indus/core/tracer.py

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set, Tuple

from qgis.core import (
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
    QgsVectorLayer,
    QgsExpression,
)


def _as_str(v) -> str:
    if v is None:
        return ""
    return str(v)


class NetworkTracer:
    """
    Traçage unifié sur 2 couches linéaires formant UN SEUL graphe topologique :
      - canalisations (obligatoire)
      - cours_d_eau_et_fosse_ (optionnelle)

    La continuité se fait via les nœuds `idnini` / `idnterm`.
    Le parcours peut alterner librement entre canalisation et fossé.

    Paramètres
    ----------
    canal_layer : QgsVectorLayer
        Couche linéaire des canalisations (obligatoire).
    fosse_layer : Optional[QgsVectorLayer]
        Couche linéaire cours d'eau / fossé (optionnelle).
    field_alias : Optional[Dict[str, Iterable[str]]]
        Champs alternatifs à essayer, par clé:
         - 'cat'  : catégorie     (ex. contcanass)
         - 'func' : fonction      (ex. fonccanass)
         - 'type' : type de flux  (ex. typreseau: '01','02','03')
         - 'len'  : longueur      (ex. l_longcana_reelle)
    filters : Optional[Dict[str, str]]
        Filtres applicables : {'category': '01/02/03' ou '', 'function': '01/02' ou ''}

    Attributs résultats (après trace)
    ---------------------------------
    total_length : float         Longueur cumulée suivie
    flux_types   : Set[str]      Codes rencontrés (ex. {'01','02'})
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

        # Alias par défaut
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

        # Caches (par couche) pour éviter de tester 15 fois les mêmes noms
        self._layer_field_name_cache: Dict[str, Dict[str, Optional[str]]] = {}

        # Stats
        self.total_length: float = 0.0
        self.flux_types: Set[str] = set()

    # ------------------------------------------------------------------ #
    # Utils champs / valeurs
    # ------------------------------------------------------------------ #

    def _layer_id(self, layer: QgsVectorLayer) -> str:
        return layer.id()

    def _resolve_field_name(self, layer: QgsVectorLayer, key: str) -> Optional[str]:
        """
        Retourne le premier nom de champ existant pour la clé d'alias donnée.
        Résultat mis en cache par couche.
        """
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
        """
        Lit la valeur d'un champ (par clé d'alias) si présent sur la couche.
        """
        fname = self._resolve_field_name(layer, key)
        if not fname:
            return None
        try:
            val = feat[fname]
        except Exception:
            return None
        return _as_str(val) if val not in (None, "") else None

    def _len_of(self, layer: QgsVectorLayer, feat: QgsFeature) -> float:
        """
        Longueur d'un segment : champ 'len' s'il existe, sinon géométrie.
        """
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
        """
        Applique les filtres 'category' et 'function' **si** les champs existent sur la couche.
        S'ils n'existent pas, on laisse passer (ne pas bloquer les fossés par ex.).
        """
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

    # ------------------------------------------------------------------ #
    # Parcours unifié
    # ------------------------------------------------------------------ #

    def _iter_edges_from_node(
        self, node_id: str, downstream: bool
    ) -> Iterable[Tuple[QgsVectorLayer, QgsFeature, str]]:
        """
        Itère sur TOUTES les arêtes sortant du nœud courant, sur canal + fossé.
        Pour downstream=True : on cherche idnini = node_id  -> next = idnterm
        Pour downstream=False : on cherche idnterm = node_id -> next = idnini
        """
        if not self.canal_layer or not self.canal_layer.isValid():
            return []

        # Choix du côté à filtrer
        key_attr = "idnini" if downstream else "idnterm"
        next_attr = "idnterm" if downstream else "idnini"

        layers = [self.canal_layer]
        if self.fosse_layer:
            layers.append(self.fosse_layer)

        results: List[Tuple[QgsVectorLayer, QgsFeature, str]] = []
        for lyr in layers:
            expr = QgsExpression(f'"{key_attr}" = \'{node_id}\'')
            req = QgsFeatureRequest(expr)
            for feat in lyr.getFeatures(req):
                idnini = _as_str(feat["idnini"]) if "idnini" in feat.fields().names() else ""
                idnterm = _as_str(feat["idnterm"]) if "idnterm" in feat.fields().names() else ""
                if idnini == "INCONNU" or idnterm == "INCONNU":
                    continue

                if not self._pass_filters(lyr, feat):
                    continue

                nxt = _as_str(feat[next_attr]) if next_attr in feat.fields().names() else ""
                if nxt and nxt != "INCONNU":
                    results.append((lyr, feat, nxt))
        return results

    def trace(self, start_id: str, downstream: bool = True) -> Tuple[List[int], List[int]]:
        """
        Lance le parcours sur le graphe unifié.

        Retour
        ------
        (canal_ids, fosse_ids) : List[int], List[int]
            Les FIDs sélectionnés par couche.
        """
        self.total_length = 0.0
        self.flux_types.clear()

        visited_nodes: Set[str] = set()
        canal_ids: List[int] = []
        fosse_ids: List[int] = []

        stack: List[str] = [start_id]

        while stack:
            cur = stack.pop()
            if cur in visited_nodes:
                continue
            visited_nodes.add(cur)

            for lyr, feat, nxt in self._iter_edges_from_node(cur, downstream):
                # Accumuler IDs par couche
                if lyr == self.canal_layer:
                    canal_ids.append(feat.id())
                else:
                    fosse_ids.append(feat.id())

                # Longueur cumulée
                self.total_length += self._len_of(lyr, feat)

                # Types de flux (si dispo)
                t = self._feat_val_by_key(lyr, feat, "type")
                if t:
                    self.flux_types.add(t)

                # Continuer
                if nxt and nxt not in visited_nodes and nxt != "INCONNU":
                    stack.append(nxt)

        return canal_ids, fosse_ids
