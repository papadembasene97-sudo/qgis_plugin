# -*- coding: utf-8 -*-
"""
Module d'analyse des PV de conformité
Permet de détecter les PV non conformes le long d'un cheminement
et de désigner un PV comme origine de pollution
"""

from qgis.core import (
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsDistanceArea,
    QgsProject,
    QgsWkbTypes
)
from PyQt5.QtCore import QObject, pyqtSignal


class PVAnalyzer(QObject):
    """
    Analyse les PV de conformité le long d'un cheminement
    """
    
    # Signaux
    pv_found = pyqtSignal(int)  # Nombre de PV trouvés
    pv_designated = pyqtSignal(dict)  # PV désigné comme pollueur
    
    def __init__(self, pv_layer=None):
        """
        Initialise l'analyseur de PV
        
        Args:
            pv_layer: Couche QGIS des PV de conformité
        """
        super().__init__()
        self.pv_layer = pv_layer
        self.pv_list = []  # Liste complète des PV trouvés
        self.pv_actifs = []  # PV actifs (après exclusions)
        self.pv_pollueur = None  # PV désigné comme pollueur
        self.distance_calculator = QgsDistanceArea()
        self.distance_calculator.setEllipsoid('WGS84')
        
        # Distance de recherche (15 mètres)
        self.buffer_distance = 15.0
        
        # ✅ NOUVEAU v1.2.3 Phase 2 : Cache PV par canalisation
        self._pv_canal_cache = {}  # {canal_id: [pv_list]}
        self._cache_enabled = True
    
    def set_pv_layer(self, layer):
        """
        Définit la couche des PV de conformité
        
        Args:
            layer: Couche QGIS
        """
        self.pv_layer = layer
        self.pv_list = []
        self.pv_actifs = []
        self.pv_pollueur = None
    
    def find_pv_near_path(self, canalisations_features, network_type='EU'):
        """
        Trouve tous les PV non conformes à proximité du cheminement
        
        Args:
            canalisations_features: Liste des features de canalisations
            network_type: Type de réseau ('EU' ou 'EP')
        
        Returns:
            Liste des PV trouvés
        """
        if not self.pv_layer:
            print("⚠️ Pas de couche PV_CONFORMITE chargée")
            return []
        
        self.pv_list = []
        
        print(f"\n🔍 Recherche de PV non conformes à {self.buffer_distance}m du cheminement...")
        
        # Pour chaque canalisation du cheminement
        for canal_feat in canalisations_features:
            canal_geom = canal_feat.geometry()
            canal_id = canal_feat['idcanal'] if 'idcanal' in canal_feat.fields().names() else canal_feat.id()
            
            # Créer un buffer autour de la canalisation
            buffer_geom = canal_geom.buffer(self.buffer_distance, 8)
            
            # Chercher les PV dans ce buffer
            for pv_feat in self.pv_layer.getFeatures():
                pv_geom = pv_feat.geometry()
                
                # Vérifier si le PV est dans le buffer
                if buffer_geom.intersects(pv_geom):
                    # Vérifier la conformité
                    conforme = pv_feat['conforme'] if 'conforme' in pv_feat.fields().names() else 'Non'
                    
                    # Ne garder que les PV non conformes
                    if conforme == 'Non':
                        # Calculer la distance exacte
                        distance = self.distance_calculator.measureLine(
                            canal_geom.nearestPoint(pv_geom).asPoint(),
                            pv_geom.asPoint()
                        )
                        
                        # Vérifier que ce PV n'est pas déjà dans la liste
                        pv_id = pv_feat['id'] if 'id' in pv_feat.fields().names() else pv_feat.id()
                        
                        if not any(p['id'] == pv_id for p in self.pv_list):
                            pv_data = {
                                'id': pv_id,
                                'num_pv': pv_feat['num_pv'] if 'num_pv' in pv_feat.fields().names() else 'N/A',
                                'adresse': pv_feat['adresse'] if 'adresse' in pv_feat.fields().names() else 'N/A',
                                'code_postal': pv_feat['code_posta'] if 'code_posta' in pv_feat.fields().names() else '',
                                'commune': pv_feat['nom_com'] if 'nom_com' in pv_feat.fields().names() else 'N/A',
                                'conforme': conforme,
                                'eu_vers_ep': pv_feat['eu_vers_ep'] if 'eu_vers_ep' in pv_feat.fields().names() else 'Non',
                                'ep_vers_eu': pv_feat['ep_vers_eu'] if 'ep_vers_eu' in pv_feat.fields().names() else 'Non',
                                'date_pv': pv_feat['date_pv'] if 'date_pv' in pv_feat.fields().names() else 'N/A',
                                'nb_chamb': pv_feat['nb_chamb'] if 'nb_chamb' in pv_feat.fields().names() else 'N/A',
                                'surf_ep': pv_feat['surf_ep'] if 'surf_ep' in pv_feat.fields().names() else 0,
                                'lien_osmose': pv_feat['lien_osmose'] if 'lien_osmose' in pv_feat.fields().names() else '',
                                'lat': pv_feat['lat'] if 'lat' in pv_feat.fields().names() else None,
                                'lon': pv_feat['lon'] if 'lon' in pv_feat.fields().names() else None,
                                'canal_rattache': canal_id,
                                'distance': round(distance, 1),
                                'geometry': pv_geom,
                                'feature': pv_feat
                            }
                            
                            self.pv_list.append(pv_data)
                            print(f"  ✓ PV trouvé : {pv_data['adresse']}, {pv_data['commune']} (distance: {distance:.1f}m)")
        
        # Initialiser la liste active
        self.pv_actifs = self.pv_list.copy()
        
        print(f"\n✅ {len(self.pv_list)} PV non conformes trouvés au total")
        
        self.pv_found.emit(len(self.pv_list))
        return self.pv_list
    
    def find_pv_in_path(self, canal_ids, distance=15.0, use_cache=True):
        """
        Trouve les PV non conformes proches d'une liste de canalisations (par IDs).
        Version optimisée avec cache pour éviter les recherches répétées.
        
        Args:
            canal_ids: Liste d'IDs de canalisations (feature IDs)
            distance: Distance de recherche en mètres (défaut 15m)
            use_cache: Utiliser le cache (défaut True)
        
        Returns:
            Liste des PV trouvés [{id, num_pv, adresse, ...}, ...]
        """
        if not self.pv_layer:
            return []
        
        # Si cache désactivé, recherche directe
        if not use_cache or not self._cache_enabled:
            return self._search_pvs_direct(canal_ids, distance)
        
        # Vérifier le cache
        cached_pvs = []
        uncached_ids = []
        seen_pv_ids = set()  # Pour éviter les doublons
        
        for cid in canal_ids:
            if cid in self._pv_canal_cache:
                # Ajouter les PV cachés sans doublons
                for pv in self._pv_canal_cache[cid]:
                    pv_id = str(pv.get('id', ''))
                    if pv_id and pv_id not in seen_pv_ids:
                        cached_pvs.append(pv)
                        seen_pv_ids.add(pv_id)
            else:
                uncached_ids.append(cid)
        
        # Chercher seulement les canalisations non-cachées
        if uncached_ids:
            new_pvs = self._search_pvs_direct(uncached_ids, distance)
            
            # Mettre à jour le cache
            # Associer chaque PV à sa canalisation rattachée
            for pv in new_pvs:
                canal_id = pv.get('canal_rattache')
                if canal_id:
                    if canal_id not in self._pv_canal_cache:
                        self._pv_canal_cache[canal_id] = []
                    
                    # Vérifier que ce PV n'est pas déjà dans le cache
                    pv_id = str(pv.get('id', ''))
                    if pv_id and pv_id not in seen_pv_ids:
                        self._pv_canal_cache[canal_id].append(pv)
                        cached_pvs.append(pv)
                        seen_pv_ids.add(pv_id)
        
        return cached_pvs
    
    def _search_pvs_direct(self, canal_ids, distance):
        """
        Recherche directe des PV proches d'une liste de canalisations.
        Méthode interne sans cache.
        
        Args:
            canal_ids: Liste d'IDs de canalisations
            distance: Distance de recherche en mètres
        
        Returns:
            Liste des PV trouvés
        """
        if not self.pv_layer:
            return []
        
        # Récupérer la couche des canalisations depuis le projet
        canal_layer = None
        for layer in QgsProject.instance().mapLayers().values():
            if 'canal' in layer.name().lower() and 'raepa' in layer.name().lower():
                canal_layer = layer
                break
        
        if not canal_layer:
            return []
        
        pvs_found = []
        seen_pv_ids = set()
        
        # Pour chaque canalisation
        for cid in canal_ids:
            # Récupérer la feature de canalisation
            canal_feat = canal_layer.getFeature(cid)
            if not canal_feat or not canal_feat.isValid():
                continue
            
            canal_geom = canal_feat.geometry()
            if not canal_geom:
                continue
            
            # Créer un buffer autour de la canalisation
            buffer_geom = canal_geom.buffer(distance, 8)
            
            # Chercher les PV dans ce buffer
            for pv_feat in self.pv_layer.getFeatures():
                pv_geom = pv_feat.geometry()
                
                # Vérifier si le PV est dans le buffer
                if buffer_geom.intersects(pv_geom):
                    # Vérifier la conformité
                    conforme = pv_feat.attribute('conforme') if pv_feat.fields().indexOf('conforme') >= 0 else 'Non'
                    
                    # Ne garder que les PV non conformes
                    if conforme == 'Non':
                        pv_id = pv_feat.attribute('id') if pv_feat.fields().indexOf('id') >= 0 else pv_feat.id()
                        pv_id_str = str(pv_id)
                        
                        # Éviter les doublons
                        if pv_id_str in seen_pv_ids:
                            continue
                        seen_pv_ids.add(pv_id_str)
                        
                        # Construire les données PV
                        # Calculer la distance exacte entre le PV et la canalisation
                        distance_pv_canal = canal_geom.distance(pv_geom)
                        
                        pv_data = {
                            'id': pv_id,
                            'fid': pv_feat.id(),  # Feature ID pour sélection QGIS
                            'num_pv': pv_feat.attribute('num_pv') if pv_feat.fields().indexOf('num_pv') >= 0 else 'N/A',
                            'adresse': pv_feat.attribute('adresse') if pv_feat.fields().indexOf('adresse') >= 0 else 'N/A',
                            'code_postal': pv_feat.attribute('code_posta') if pv_feat.fields().indexOf('code_posta') >= 0 else '',
                            'commune': pv_feat.attribute('nom_com') if pv_feat.fields().indexOf('nom_com') >= 0 else 'N/A',
                            'conforme': conforme,
                            'eu_vers_ep': pv_feat.attribute('eu_vers_ep') if pv_feat.fields().indexOf('eu_vers_ep') >= 0 else 'Non',
                            'ep_vers_eu': pv_feat.attribute('ep_vers_eu') if pv_feat.fields().indexOf('ep_vers_eu') >= 0 else 'Non',
                            'date_pv': pv_feat.attribute('date_pv') if pv_feat.fields().indexOf('date_pv') >= 0 else 'N/A',
                            'nb_chamb': pv_feat.attribute('nb_chamb') if pv_feat.fields().indexOf('nb_chamb') >= 0 else 'N/A',
                            'surf_ep': pv_feat.attribute('surf_ep') if pv_feat.fields().indexOf('surf_ep') >= 0 else 0,
                            'lien_osmose': pv_feat.attribute('lien_osmose') if pv_feat.fields().indexOf('lien_osmose') >= 0 else '',
                            'lat': pv_feat.attribute('lat') if pv_feat.fields().indexOf('lat') >= 0 else None,
                            'lon': pv_feat.attribute('lon') if pv_feat.fields().indexOf('lon') >= 0 else None,
                            'distance': round(distance_pv_canal, 2),  # Distance en mètres
                            'canal_rattache': cid,
                            'geometry': pv_geom,
                            'feature': pv_feat
                        }
                        
                        pvs_found.append(pv_data)
        
        return pvs_found
    
    def clear_cache(self):
        """Vide le cache PV"""
        self._pv_canal_cache.clear()
    
    def disable_cache(self):
        """Désactive le cache"""
        self._cache_enabled = False
        self._pv_canal_cache.clear()
    
    def enable_cache(self):
        """Active le cache"""
        self._cache_enabled = True
    
    def update_after_exclusion(self, canalisations_exclues):
        """
        Met à jour la liste des PV actifs après exclusion de branches
        
        Args:
            canalisations_exclues: Liste des IDs de canalisations exclues
        
        Returns:
            Liste des PV actifs restants
        """
        if not canalisations_exclues:
            self.pv_actifs = self.pv_list.copy()
            return self.pv_actifs
        
        nb_avant = len(self.pv_actifs)
        
        # Filtrer les PV dont la canalisation rattachée est exclue
        self.pv_actifs = [
            pv for pv in self.pv_list
            if pv['canal_rattache'] not in canalisations_exclues
        ]
        
        nb_apres = len(self.pv_actifs)
        nb_exclus = nb_avant - nb_apres
        
        if nb_exclus > 0:
            print(f"🗑️ {nb_exclus} PV exclus (branche coupée)")
        
        return self.pv_actifs
    
    def designate_as_polluter(self, pv_id):
        """
        Désigne un PV comme origine de pollution
        
        Args:
            pv_id: ID du PV à désigner
        
        Returns:
            True si succès, False sinon
        """
        # Chercher le PV dans la liste active
        pv = next((p for p in self.pv_actifs if p['id'] == pv_id), None)
        
        if pv:
            self.pv_pollueur = pv
            print(f"\n🎯 PV désigné comme pollueur : {pv['adresse']}, {pv['commune']}")
            
            self.pv_designated.emit(pv)
            return True
        else:
            print(f"⚠️ PV {pv_id} introuvable dans la liste active")
            return False
    
    def get_polluter_info(self):
        """
        Retourne les informations complètes du PV pollueur
        
        Returns:
            Dictionnaire avec toutes les infos du PV, ou None
        """
        if not self.pv_pollueur:
            return None
        
        # Détecter les problèmes d'inversion
        problemes = []
        if self.pv_pollueur['eu_vers_ep'] == 'Oui':
            problemes.append("EU → EP (inversion)")
        if self.pv_pollueur['ep_vers_eu'] == 'Oui':
            problemes.append("EP → EU (inversion)")
        if not problemes:
            problemes.append("Non-conformité générale")
        
        return {
            'type': 'PV non conforme',
            'id': self.pv_pollueur['id'],
            'num_pv': self.pv_pollueur['num_pv'],
            'adresse': self.pv_pollueur['adresse'],
            'code_postal': self.pv_pollueur['code_postal'],
            'commune': self.pv_pollueur['commune'],
            'conforme': self.pv_pollueur['conforme'],
            'eu_vers_ep': self.pv_pollueur['eu_vers_ep'],
            'ep_vers_eu': self.pv_pollueur['ep_vers_eu'],
            'date_controle': self.pv_pollueur['date_pv'],
            'nb_chambres': self.pv_pollueur['nb_chamb'],
            'surf_ep': self.pv_pollueur['surf_ep'],
            'lien_osmose': self.pv_pollueur['lien_osmose'],
            'lat': self.pv_pollueur['lat'],
            'lon': self.pv_pollueur['lon'],
            'geometry': self.pv_pollueur['geometry'],
            'problemes': problemes,
            'problemes_str': ', '.join(problemes)
        }
    
    def get_pv_count(self):
        """
        Retourne le nombre de PV non conformes actifs
        
        Returns:
            Nombre de PV actifs
        """
        return len(self.pv_actifs)
    
    def get_pv_by_id(self, pv_id):
        """
        Récupère un PV par son ID
        
        Args:
            pv_id: ID du PV
        
        Returns:
            Données du PV ou None
        """
        return next((p for p in self.pv_actifs if p['id'] == pv_id), None)
    
    def clear(self):
        """
        Réinitialise l'analyseur
        """
        self.pv_list = []
        self.pv_actifs = []
        self.pv_pollueur = None
    
    def export_to_dict(self):
        """
        Exporte les données pour rapport/export
        
        Returns:
            Dictionnaire avec toutes les données
        """
        return {
            'total': len(self.pv_list),
            'actifs': len(self.pv_actifs),
            'pollueur': self.get_polluter_info(),
            'liste': self.pv_actifs
        }
