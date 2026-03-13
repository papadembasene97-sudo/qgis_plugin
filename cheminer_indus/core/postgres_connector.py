"""
Module de connexion automatique PostgreSQL pour TRACK-EAU-POLL
Charge automatiquement les couches nécessaires depuis PostgreSQL
"""

from qgis.core import (
    QgsDataSourceUri,
    QgsVectorLayer,
    QgsProject,
    QgsProviderRegistry
)
from qgis.PyQt.QtCore import QSettings

class PostgreSQLConnector:
    """Gestionnaire de connexion PostgreSQL pour TRACK-EAU-POLL"""
    
    def __init__(self):
        self.settings = QSettings()
        self.project = QgsProject.instance()
        self.connection_name = None
        self.db_params = {}
    
    def get_available_connections(self):
        """Récupère les connexions PostgreSQL configurées dans QGIS"""
        
        self.settings.beginGroup("/PostgreSQL/connections")
        connections = self.settings.childGroups()
        self.settings.endGroup()
        
        return connections
    
    def load_connection_params(self, connection_name):
        """Charge les paramètres d'une connexion PostgreSQL"""
        
        self.connection_name = connection_name
        
        self.settings.beginGroup(f"/PostgreSQL/connections/{connection_name}")
        
        self.db_params = {
            'host': self.settings.value('host', ''),
            'port': self.settings.value('port', '5432'),
            'database': self.settings.value('database', ''),
            'username': self.settings.value('username', ''),
            'password': self.settings.value('password', ''),
            'service': self.settings.value('service', ''),
            'authcfg': self.settings.value('authcfg', ''),
            'sslmode': self.settings.value('sslmode', QgsDataSourceUri.SslPrefer)
        }
        
        self.settings.endGroup()
        
        return self.db_params
    
    def create_uri(self, schema, table, geom_column='geom', key_column='id'):
        """Crée une URI PostgreSQL pour charger une couche"""
        
        uri = QgsDataSourceUri()
        
        # Connexion de base
        if self.db_params.get('service'):
            uri.setConnection(
                self.db_params['service'],
                self.db_params['database'],
                self.db_params['username'],
                self.db_params['password']
            )
        else:
            uri.setConnection(
                self.db_params['host'],
                self.db_params['port'],
                self.db_params['database'],
                self.db_params['username'],
                self.db_params['password']
            )
        
        # Configurer la couche
        uri.setDataSource(schema, table, geom_column, '', key_column)
        
        # SSL
        if self.db_params.get('sslmode'):
            uri.setSslMode(self.db_params['sslmode'])
        
        return uri.uri()
    
    def load_layer(self, schema, table, layer_name=None, geom_column='geom', key_column='id'):
        """Charge une couche PostgreSQL dans QGIS"""
        
        if not self.connection_name:
            raise ValueError("Aucune connexion PostgreSQL configurée")
        
        # Vérifier si la couche existe déjà
        if layer_name:
            existing_layers = self.project.mapLayersByName(layer_name)
            if existing_layers:
                print(f"✓ Couche '{layer_name}' déjà chargée")
                return existing_layers[0]
        
        # Créer l'URI
        uri = self.create_uri(schema, table, geom_column, key_column)
        
        # Nom de la couche
        if not layer_name:
            layer_name = f"{schema}.{table}"
        
        # Charger la couche
        layer = QgsVectorLayer(uri, layer_name, "postgres")
        
        if not layer.isValid():
            raise RuntimeError(f"❌ Impossible de charger {schema}.{table}")
        
        # Ajouter au projet
        self.project.addMapLayer(layer)
        
        print(f"✓ Couche '{layer_name}' chargée : {layer.featureCount()} entités")
        
        return layer
    
    def load_cheminer_indus_layers(self):
        """Charge toutes les couches nécessaires pour TRACK-EAU-POLL"""
        
        layers = {}
        
        try:
            # 1. Canalisations
            layers['canalisations'] = self.load_layer(
                schema='raepa',
                table='raepa_canalass_l',
                layer_name='Canalisations',
                geom_column='geom',
                key_column='idcana'
            )
            
            # 2. Ouvrages
            layers['ouvrages'] = self.load_layer(
                schema='raepa',
                table='raepa_ouvrass_p',
                layer_name='Ouvrages',
                geom_column='geom',
                key_column='idouvrage'
            )
            
            # 3. Industriels
            layers['industriels'] = self.load_layer(
                schema='sig',
                table='Indus',
                layer_name='Industriels',
                geom_column='geom',
                key_column='id'
            )
            
            # 4. Liaisons industriels
            layers['liaison_indus'] = self.load_layer(
                schema='sig',
                table='liaison_indus',
                layer_name='Liaisons Industriels',
                geom_column='geom',
                key_column='idliaison'
            )
            
            # 5. Astreinte-Exploit (sans géométrie)
            # Note: Cette table peut ne pas avoir de géométrie
            try:
                layers['astreinte'] = self.load_layer(
                    schema='expoit',
                    table='ASTREINTE-EXPLOIT',
                    layer_name='Astreinte-Exploit',
                    geom_column=None,
                    key_column='id'
                )
            except:
                print("⚠️  Table ASTREINTE-EXPLOIT sans géométrie, non chargée comme couche")
            
            # 6. 🆕 Vue d'entraînement IA
            layers['donnees_ia'] = self.load_layer(
                schema='cheminer_indus',
                table='donnees_entrainement_ia',
                layer_name='Données Entraînement IA',
                geom_column='geom',
                key_column='id_noeud'
            )
            
            # 7. 🆕 Points noirs EGIS
            try:
                layers['points_noirs_egis'] = self.load_layer(
                    schema='sda',
                    table='POINT_NOIR_EGIS',
                    layer_name='Points Noirs EGIS',
                    geom_column='geom',
                    key_column='gid'
                )
            except:
                print("⚠️  Table POINT_NOIR_EGIS non disponible ou sans géométrie")
            
            # 8. 🆕 PV Conformité (utilise lat/lon pour créer des Points)
            # ⚠️ Schéma corrigé : osmose.PV_CONFORMITE (pas exploit)
            try:
                # Créer une URI spéciale avec lat/lon comme géométrie
                uri_pv = QgsDataSourceUri()
                
                if self.db_params.get('service'):
                    uri_pv.setConnection(
                        self.db_params['service'],
                        self.db_params['database'],
                        self.db_params['username'],
                        self.db_params['password']
                    )
                else:
                    uri_pv.setConnection(
                        self.db_params['host'],
                        self.db_params['port'],
                        self.db_params['database'],
                        self.db_params['username'],
                        self.db_params['password']
                    )
                
                # Utiliser une vue SQL pour créer la géométrie depuis lat/lon
                # ⚠️ CORRECTION : osmose.PV_CONFORMITE (pas exploit)
                sql = f"""
                    SELECT 
                        *,
                        ST_SetSRID(ST_MakePoint(lon, lat), 4326) as geom
                    FROM osmose."PV_CONFORMITE"
                    WHERE lat IS NOT NULL AND lon IS NOT NULL
                """
                
                uri_pv.setDataSource("", f"({sql})", "geom", "", "id")
                
                # Charger la couche
                layer_pv = QgsVectorLayer(uri_pv.uri(), 'PV Conformité', 'postgres')
                
                if layer_pv.isValid():
                    # Vérifier si la couche n'existe pas déjà
                    existing = self.project.mapLayersByName('PV Conformité')
                    if not existing:
                        self.project.addMapLayer(layer_pv)
                        print(f"✓ Couche 'PV Conformité' chargée : {layer_pv.featureCount()} entités")
                        layers['pv_conformite'] = layer_pv
                    else:
                        print(f"✓ Couche 'PV Conformité' déjà chargée")
                        layers['pv_conformite'] = existing[0]
                else:
                    print("⚠️  Table PV_CONFORMITE : géométrie invalide")
            
            except Exception as e:
                print(f"⚠️  Table osmose.PV_CONFORMITE non disponible : {e}")
            
            print(f"\n✅ {len(layers)} couches chargées avec succès !")
            
            return layers
        
        except Exception as e:
            print(f"❌ Erreur lors du chargement des couches : {e}")
            raise
    
    def auto_detect_connection(self):
        """Détecte automatiquement la connexion PostgreSQL à utiliser"""
        
        connections = self.get_available_connections()
        
        if not connections:
            raise ValueError("❌ Aucune connexion PostgreSQL configurée dans QGIS")
        
        # Chercher une connexion qui contient les tables TRACK-EAU-POLL
        for conn_name in connections:
            self.load_connection_params(conn_name)
            
            # Tester si la base contient les tables nécessaires
            try:
                uri = self.create_uri('raepa', 'raepa_canalass_l')
                test_layer = QgsVectorLayer(uri, 'test', 'postgres')
                
                if test_layer.isValid():
                    print(f"✓ Connexion '{conn_name}' détectée et fonctionnelle")
                    return conn_name
            except:
                continue
        
        # Si aucune connexion trouvée, utiliser la première
        print(f"⚠️  Utilisation de la connexion par défaut : {connections[0]}")
        self.load_connection_params(connections[0])
        return connections[0]


# ============================================================================
# EXEMPLE D'UTILISATION
# ============================================================================

def load_cheminer_indus_data():
    """Fonction helper pour charger toutes les données TRACK-EAU-POLL"""
    
    connector = PostgreSQLConnector()
    
    # Option 1 : Auto-détection
    connector.auto_detect_connection()
    
    # Option 2 : Connexion spécifique
    # connections = connector.get_available_connections()
    # connector.load_connection_params(connections[0])
    
    # Charger toutes les couches
    layers = connector.load_cheminer_indus_layers()
    
    return layers, connector
