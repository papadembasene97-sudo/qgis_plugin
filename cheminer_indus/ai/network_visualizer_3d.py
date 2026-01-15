"""
Module de visualisation 3D des réseaux d'assainissement
Gestion des zones complexes avec multiples canalisations entremêlées
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime

try:
    import pyvista as pv
    PYVISTA_AVAILABLE = True
except ImportError:
    PYVISTA_AVAILABLE = False
    print("Warning: PyVista not available. Install with: pip install pyvista")

try:
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    from matplotlib.colors import LinearSegmentedColormap
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: Matplotlib not available for 3D plotting")


class NetworkVisualizer3D:
    """
    Visualiseur 3D des réseaux d'assainissement
    
    Affiche les canalisations en 3D avec:
    - Diamètres représentés par l'épaisseur
    - Élévations (Z) représentées verticalement
    - Pentes visualisées
    - Détection automatique des zones complexes
    """
    
    def __init__(self, use_pyvista: bool = True):
        """
        Initialise le visualiseur
        
        Args:
            use_pyvista: Utiliser PyVista (sinon Matplotlib)
        """
        self.use_pyvista = use_pyvista and PYVISTA_AVAILABLE
        
        if self.use_pyvista:
            self.plotter = pv.Plotter()
            self.plotter.set_background('white')
        else:
            if not MATPLOTLIB_AVAILABLE:
                raise ImportError("Neither PyVista nor Matplotlib available")
            
            self.fig = plt.figure(figsize=(14, 10))
            self.ax = self.fig.add_subplot(111, projection='3d')
    
    def detect_complex_zones(self,
                            canal_features: List[Dict],
                            density_threshold: int = 5,
                            radius: float = 50) -> List[Dict]:
        """
        Détecte les zones complexes avec beaucoup de canalisations entremêlées
        
        Args:
            canal_features: Liste des features de canalisations
            density_threshold: Nombre min de canaux pour considérer une zone complexe
            radius: Rayon de recherche (m)
            
        Returns:
            Liste des zones complexes avec statistiques
        """
        print(f"🔍 Recherche de zones complexes (seuil: {density_threshold} canaux dans {radius}m)...")
        
        # Extraction des centroides
        centroids = []
        for feature in canal_features:
            geom = feature.get('geometry', {})
            coords = geom.get('coordinates', [])
            
            if coords and len(coords) >= 2:
                # Centroi de de la ligne
                x_coords = [c[0] for c in coords]
                y_coords = [c[1] for c in coords]
                centroid_x = np.mean(x_coords)
                centroid_y = np.mean(y_coords)
                
                centroids.append({
                    'feature': feature,
                    'x': centroid_x,
                    'y': centroid_y,
                    'z_amont': feature.get('z_amont', 0),
                    'z_aval': feature.get('z_aval', 0)
                })
        
        # Clustering spatial simple
        complex_zones = []
        visited = set()
        
        for i, centroid in enumerate(centroids):
            if i in visited:
                continue
            
            # Compte les voisins dans le rayon
            neighbors = []
            for j, other in enumerate(centroids):
                if i == j:
                    continue
                
                distance = np.sqrt(
                    (other['x'] - centroid['x'])**2 + 
                    (other['y'] - centroid['y'])**2
                )
                
                if distance <= radius:
                    neighbors.append((j, other))
            
            # Si densité suffisante = zone complexe
            if len(neighbors) >= density_threshold - 1:
                zone_features = [centroid['feature']] + [n[1]['feature'] for n in neighbors]
                
                # Marquer comme visités
                visited.add(i)
                for j, _ in neighbors:
                    visited.add(j)
                
                # Analyse de la zone
                zone_analysis = self._analyze_zone(zone_features)
                
                complex_zones.append({
                    'center': (centroid['x'], centroid['y']),
                    'radius': radius,
                    'nb_canals': len(zone_features),
                    'features': zone_features,
                    **zone_analysis
                })
        
        print(f"✅ {len(complex_zones)} zones complexes détectées")
        
        return complex_zones
    
    def _analyze_zone(self, features: List[Dict]) -> Dict:
        """Analyse une zone complexe"""
        diameters = [f.get('diametre', 300) for f in features]
        z_amont_list = [f.get('z_amont', 0) for f in features]
        z_aval_list = [f.get('z_aval', 0) for f in features]
        slopes = [f.get('pente', 0) for f in features]
        
        # Différence d'élévation max (vertical extent)
        all_z = z_amont_list + z_aval_list
        z_range = max(all_z) - min(all_z) if all_z else 0
        
        # Variance des diamètres
        diameter_variance = np.var(diameters) if diameters else 0
        
        # Nombre de niveaux distincts (clustering vertical)
        if z_amont_list:
            z_unique = len(set([round(z, 1) for z in z_amont_list]))
        else:
            z_unique = 0
        
        return {
            'avg_diameter': np.mean(diameters) if diameters else 0,
            'max_diameter': max(diameters) if diameters else 0,
            'min_diameter': min(diameters) if diameters else 0,
            'diameter_variance': diameter_variance,
            'avg_slope': np.mean(slopes) if slopes else 0,
            'z_min': min(all_z) if all_z else 0,
            'z_max': max(all_z) if all_z else 0,
            'z_range': z_range,
            'nb_vertical_levels': z_unique,
            'complexity_score': len(features) * z_range * (1 + diameter_variance/10000)
        }
    
    def visualize_network_3d(self,
                            canal_features: List[Dict],
                            color_by: str = 'diameter',
                            show_labels: bool = True,
                            highlight_complex: bool = True):
        """
        Visualise le réseau en 3D
        
        Args:
            canal_features: Features des canalisations
            color_by: Critère de coloration ('diameter', 'slope', 'type', 'elevation')
            show_labels: Afficher les labels (diamètre, etc.)
            highlight_complex: Mettre en évidence les zones complexes
        """
        print(f"🎨 Génération de la visualisation 3D ({len(canal_features)} canaux)...")
        
        if highlight_complex:
            complex_zones = self.detect_complex_zones(canal_features)
        else:
            complex_zones = []
        
        if self.use_pyvista:
            self._visualize_pyvista(canal_features, complex_zones, color_by, show_labels)
        else:
            self._visualize_matplotlib(canal_features, complex_zones, color_by, show_labels)
    
    def _visualize_pyvista(self,
                          canal_features: List[Dict],
                          complex_zones: List[Dict],
                          color_by: str,
                          show_labels: bool):
        """Visualisation avec PyVista (interactif)"""
        
        # Colormap selon critère
        color_values = self._get_color_values(canal_features, color_by)
        vmin, vmax = min(color_values), max(color_values)
        
        # Ajout des canalisations
        for i, feature in enumerate(canal_features):
            geom = feature.get('geometry', {})
            coords = geom.get('coordinates', [])
            
            if len(coords) < 2:
                continue
            
            # Points de départ et arrivée
            x1, y1 = coords[0][0], coords[0][1]
            x2, y2 = coords[-1][0], coords[-1][1]
            z1 = feature.get('z_amont', 0)
            z2 = feature.get('z_aval', 0)
            
            # Création du tube 3D
            points = np.array([
                [x1, y1, z1],
                [x2, y2, z2]
            ])
            
            diameter = feature.get('diametre', 300) / 1000  # mm -> m
            tube = pv.Tube(points, radius=diameter/2, n_sides=12)
            
            # Couleur selon critère
            color = self._get_color_for_value(color_values[i], vmin, vmax)
            
            self.plotter.add_mesh(tube, color=color, opacity=0.8)
            
            # Label optionnel
            if show_labels and i % 10 == 0:  # Labels tous les 10 canaux
                label_text = f"Ø{int(diameter*1000)}mm"
                self.plotter.add_point_labels(
                    [[(x1+x2)/2, (y1+y2)/2, (z1+z2)/2]],
                    [label_text],
                    font_size=8,
                    point_size=0
                )
        
        # Zones complexes
        if complex_zones:
            for zone in complex_zones:
                center_x, center_y = zone['center']
                z_center = (zone['z_min'] + zone['z_max']) / 2
                
                # Sphère pour marquer la zone
                sphere = pv.Sphere(
                    center=[center_x, center_y, z_center],
                    radius=zone['radius'] * 0.3
                )
                self.plotter.add_mesh(sphere, color='red', opacity=0.3)
                
                # Label de la zone
                zone_label = f"Zone complexe\n{zone['nb_canals']} canaux\nScore: {zone['complexity_score']:.1f}"
                self.plotter.add_point_labels(
                    [[center_x, center_y, z_center + 5]],
                    [zone_label],
                    font_size=10,
                    point_color='red',
                    point_size=10
                )
        
        # Axes et grille
        self.plotter.show_axes()
        self.plotter.add_bounding_box()
        
        # Colorbar
        self.plotter.add_text(
            f"Coloration: {color_by}",
            position='upper_left',
            font_size=12
        )
        
        # Affichage
        print("🖼️  Affichage de la visualisation 3D interactive...")
        self.plotter.show()
    
    def _visualize_matplotlib(self,
                             canal_features: List[Dict],
                             complex_zones: List[Dict],
                             color_by: str,
                             show_labels: bool):
        """Visualisation avec Matplotlib (statique mais plus compatible)"""
        
        color_values = self._get_color_values(canal_features, color_by)
        vmin, vmax = min(color_values), max(color_values)
        
        # Colormap
        cmap = plt.cm.viridis
        
        for i, feature in enumerate(canal_features):
            geom = feature.get('geometry', {})
            coords = geom.get('coordinates', [])
            
            if len(coords) < 2:
                continue
            
            x1, y1 = coords[0][0], coords[0][1]
            x2, y2 = coords[-1][0], coords[-1][1]
            z1 = feature.get('z_amont', 0)
            z2 = feature.get('z_aval', 0)
            
            # Ligne 3D
            diameter = feature.get('diametre', 300)
            linewidth = (diameter / 100) * 2  # Épaisseur proportionnelle
            
            color = cmap((color_values[i] - vmin) / (vmax - vmin) if vmax > vmin else 0.5)
            
            self.ax.plot([x1, x2], [y1, y2], [z1, z2],
                        color=color,
                        linewidth=linewidth,
                        alpha=0.7)
        
        # Zones complexes
        if complex_zones:
            for zone in complex_zones:
                center_x, center_y = zone['center']
                z_center = (zone['z_min'] + zone['z_max']) / 2
                
                # Marker pour la zone
                self.ax.scatter([center_x], [center_y], [z_center],
                              c='red', s=200, alpha=0.5, marker='o')
                
                if show_labels:
                    self.ax.text(center_x, center_y, z_center + 2,
                               f"{zone['nb_canals']} canaux",
                               color='red', fontsize=8)
        
        # Configuration des axes
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.set_zlabel('Altitude Z (m NGF)')
        self.ax.set_title(f'Visualisation 3D du réseau - Coloration: {color_by}')
        
        # Colorbar
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=self.ax, pad=0.1, shrink=0.8)
        cbar.set_label(color_by.capitalize())
        
        plt.tight_layout()
        print("🖼️  Affichage de la visualisation 3D...")
        plt.show()
    
    def _get_color_values(self, canal_features: List[Dict], color_by: str) -> List[float]:
        """Extrait les valeurs pour la coloration"""
        if color_by == 'diameter':
            return [f.get('diametre', 300) for f in canal_features]
        elif color_by == 'slope':
            return [f.get('pente', 0) * 100 for f in canal_features]  # En %
        elif color_by == 'elevation':
            return [f.get('z_amont', 0) for f in canal_features]
        elif color_by == 'type':
            type_map = {'EU': 1, 'EP': 2, 'Mixte': 3, 'UNITAIRE': 3}
            return [type_map.get(f.get('type_reseau', 'EU'), 1) for f in canal_features]
        else:
            return [1.0] * len(canal_features)
    
    def _get_color_for_value(self, value: float, vmin: float, vmax: float) -> str:
        """Convertit une valeur en couleur RGB"""
        if vmax == vmin:
            normalized = 0.5
        else:
            normalized = (value - vmin) / (vmax - vmin)
        
        # Colormap viridis
        cmap = plt.cm.viridis
        rgba = cmap(normalized)
        
        # Conversion en format RGB pour PyVista
        return f'#{int(rgba[0]*255):02x}{int(rgba[1]*255):02x}{int(rgba[2]*255):02x}'
    
    def export_complex_zones_report(self, complex_zones: List[Dict], output_path: str):
        """Exporte un rapport des zones complexes"""
        import json
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'nb_zones': len(complex_zones),
            'zones': []
        }
        
        for i, zone in enumerate(complex_zones, 1):
            zone_report = {
                'zone_id': i,
                'center_x': zone['center'][0],
                'center_y': zone['center'][1],
                'radius': zone['radius'],
                'nb_canals': zone['nb_canals'],
                'avg_diameter': round(zone['avg_diameter'], 2),
                'diameter_range': [zone['min_diameter'], zone['max_diameter']],
                'elevation_range': [round(zone['z_min'], 2), round(zone['z_max'], 2)],
                'z_range': round(zone['z_range'], 2),
                'nb_vertical_levels': zone['nb_vertical_levels'],
                'complexity_score': round(zone['complexity_score'], 2),
                'risk_assessment': self._assess_zone_risk(zone)
            }
            
            report['zones'].append(zone_report)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Rapport exporté : {output_path}")
    
    def _assess_zone_risk(self, zone: Dict) -> str:
        """Évalue le risque d'une zone complexe"""
        score = zone['complexity_score']
        
        if score > 1000:
            return "CRITIQUE - Intervention prioritaire recommandée"
        elif score > 500:
            return "ÉLEVÉ - Surveillance renforcée nécessaire"
        elif score > 200:
            return "MOYEN - Surveillance régulière"
        else:
            return "FAIBLE - Surveillance normale"
    
    def create_profile_view(self, canal_features: List[Dict], output_path: Optional[str] = None):
        """
        Crée une vue en profil du réseau (coupe verticale)
        
        Args:
            canal_features: Features des canalisations
            output_path: Chemin de sauvegarde (optionnel)
        """
        fig, ax = plt.subplots(figsize=(16, 6))
        
        # Calcul des distances cumulées
        cumulative_distance = 0
        distances = []
        elevations_amont = []
        elevations_aval = []
        diameters = []
        
        for feature in canal_features:
            geom = feature.get('geometry', {})
            coords = geom.get('coordinates', [])
            
            if len(coords) >= 2:
                # Longueur du tronçon
                length = feature.get('longueur', 0)
                if length == 0:
                    x1, y1 = coords[0][0], coords[0][1]
                    x2, y2 = coords[-1][0], coords[-1][1]
                    length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
                
                z_amont = feature.get('z_amont', 0)
                z_aval = feature.get('z_aval', 0)
                diameter = feature.get('diametre', 300) / 1000  # m
                
                distances.extend([cumulative_distance, cumulative_distance + length])
                elevations_amont.extend([z_amont, z_aval])
                elevations_aval.extend([z_amont - diameter, z_aval - diameter])
                diameters.extend([diameter, diameter])
                
                cumulative_distance += length
        
        # Tracé du radier (fond)
        ax.plot(distances, elevations_amont, 'b-', linewidth=2, label='Radier (fond)')
        
        # Remplissage pour montrer le diamètre
        ax.fill_between(distances, elevations_aval, elevations_amont, alpha=0.3, label='Canalisation')
        
        # Grille et labels
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Distance cumulée (m)', fontsize=12)
        ax.set_ylabel('Altitude (m NGF)', fontsize=12)
        ax.set_title('Profil en long du réseau', fontsize=14, fontweight='bold')
        ax.legend()
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"💾 Profil sauvegardé : {output_path}")
        else:
            plt.show()
