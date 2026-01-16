# -*- coding: utf-8 -*-
"""
Script de test du module PVAnalyzer
À exécuter dans la console Python de QGIS
"""

from qgis.core import QgsProject, QgsFeature
from cheminer_indus.core.pv_analyzer import PVAnalyzer

def test_pv_analyzer():
    """Test complet du module PVAnalyzer"""
    
    print("=" * 60)
    print("🧪 TEST MODULE PVANALYZER")
    print("=" * 60)
    
    # 1. Charger les couches
    print("\n1️⃣ Chargement des couches...")
    
    # Couche PV
    pv_layers = QgsProject.instance().mapLayersByName('PV Conformité')
    if not pv_layers:
        pv_layers = QgsProject.instance().mapLayersByName('PV_CONFORMITE')
    
    if not pv_layers:
        print("❌ Couche PV_CONFORMITE introuvable !")
        print("   Charger d'abord la couche depuis PostgreSQL :")
        print("   QGIS → Couche → PostgreSQL → exploit → PV_CONFORMITE")
        return
    
    pv_layer = pv_layers[0]
    print(f"✅ Couche PV chargée : {pv_layer.featureCount()} PV")
    
    # Couche canalisations
    canal_layers = QgsProject.instance().mapLayersByName('Canalisations')
    if not canal_layers:
        canal_layers = QgsProject.instance().mapLayersByName('raepa_canalass_l')
    
    if not canal_layers:
        print("❌ Couche Canalisations introuvable !")
        return
    
    canal_layer = canal_layers[0]
    print(f"✅ Couche Canalisations chargée : {canal_layer.featureCount()} canalisations")
    
    # 2. Initialiser PVAnalyzer
    print("\n2️⃣ Initialisation PVAnalyzer...")
    pv_analyzer = PVAnalyzer(pv_layer)
    print(f"✅ PVAnalyzer initialisé (distance buffer : {pv_analyzer.buffer_distance}m)")
    
    # 3. Simuler un cheminement (prendre les 50 premières canalisations)
    print("\n3️⃣ Simulation d'un cheminement...")
    
    canalisations_features = []
    for i, feat in enumerate(canal_layer.getFeatures()):
        if i >= 50:
            break
        canalisations_features.append(feat)
    
    print(f"✅ {len(canalisations_features)} canalisations dans le cheminement simulé")
    
    # 4. Chercher les PV
    print("\n4️⃣ Recherche des PV non conformes...")
    pv_list = pv_analyzer.find_pv_near_path(canalisations_features, 'EU')
    
    if pv_list:
        print(f"\n✅ {len(pv_list)} PV non conformes trouvés :\n")
        
        for i, pv in enumerate(pv_list[:5], 1):  # Afficher les 5 premiers
            print(f"  {i}. {pv['adresse']}, {pv['commune']}")
            print(f"     Conforme: {pv['conforme']}")
            print(f"     EU→EP: {pv['eu_vers_ep']} | EP→EU: {pv['ep_vers_eu']}")
            print(f"     Distance: {pv['distance']:.1f}m")
            print(f"     Canal rattaché: {pv['canal_rattache']}")
            print()
        
        if len(pv_list) > 5:
            print(f"  ... et {len(pv_list) - 5} autres PV")
        
        # 5. Tester l'exclusion de branches
        print("\n5️⃣ Test de l'exclusion de branches...")
        
        # Exclure les canalisations 10-20
        canalisations_exclues = [
            feat['idcanal'] if 'idcanal' in feat.fields().names() else feat.id()
            for i, feat in enumerate(canalisations_features)
            if 10 <= i < 20
        ]
        
        print(f"   Exclusion de {len(canalisations_exclues)} canalisations...")
        
        nb_avant = pv_analyzer.get_pv_count()
        pv_analyzer.update_after_exclusion(canalisations_exclues)
        nb_apres = pv_analyzer.get_pv_count()
        
        print(f"   PV avant exclusion : {nb_avant}")
        print(f"   PV après exclusion : {nb_apres}")
        print(f"   PV exclus : {nb_avant - nb_apres}")
        
        # 6. Désigner un PV comme pollueur
        print("\n6️⃣ Test de désignation d'un PV comme pollueur...")
        
        if pv_analyzer.pv_actifs:
            premier_pv = pv_analyzer.pv_actifs[0]
            pv_id = premier_pv['id']
            
            success = pv_analyzer.designate_as_polluter(pv_id)
            
            if success:
                print("✅ PV désigné comme pollueur avec succès !")
                
                # Récupérer les infos
                info = pv_analyzer.get_polluter_info()
                
                print(f"\n📍 Informations du PV pollueur :")
                print(f"   Type : {info['type']}")
                print(f"   ID : {info['id']}")
                print(f"   N° PV : {info['num_pv']}")
                print(f"   Adresse : {info['adresse']}")
                print(f"   Commune : {info['commune']}")
                print(f"   Conforme : {info['conforme']}")
                print(f"   EU→EP : {info['eu_vers_ep']}")
                print(f"   EP→EU : {info['ep_vers_eu']}")
                print(f"   Date contrôle : {info['date_controle']}")
                print(f"   Problèmes : {info['problemes_str']}")
                
                if info['lien_osmose']:
                    print(f"   Lien OSMOSE : {info['lien_osmose']}")
            else:
                print("❌ Échec de la désignation")
        
        # 7. Test d'export
        print("\n7️⃣ Test d'export...")
        export_data = pv_analyzer.export_to_dict()
        
        print(f"   Total PV : {export_data['total']}")
        print(f"   PV actifs : {export_data['actifs']}")
        print(f"   PV pollueur : {export_data['pollueur'] is not None}")
    
    else:
        print("⚠️  Aucun PV non conforme trouvé dans ce cheminement")
        print("   (C'est normal si les canalisations simulées sont loin des PV)")
    
    print("\n" + "=" * 60)
    print("✅ TESTS TERMINÉS")
    print("=" * 60)


# Fonction de statistiques sur les PV
def stats_pv_conformite():
    """Affiche des statistiques sur la couche PV_CONFORMITE"""
    
    print("=" * 60)
    print("📊 STATISTIQUES PV_CONFORMITE")
    print("=" * 60)
    
    # Charger la couche
    pv_layers = QgsProject.instance().mapLayersByName('PV Conformité')
    if not pv_layers:
        pv_layers = QgsProject.instance().mapLayersByName('PV_CONFORMITE')
    
    if not pv_layers:
        print("❌ Couche PV_CONFORMITE introuvable !")
        return
    
    pv_layer = pv_layers[0]
    
    total = pv_layer.featureCount()
    print(f"\n📍 Total PV : {total}")
    
    # Compter par conformité
    conformes = 0
    non_conformes = 0
    eu_vers_ep = 0
    ep_vers_eu = 0
    
    communes = {}
    
    for feat in pv_layer.getFeatures():
        # Conformité
        if feat['conforme'] == 'Oui':
            conformes += 1
        else:
            non_conformes += 1
        
        # Inversions
        if feat['eu_vers_ep'] == 'Oui':
            eu_vers_ep += 1
        if feat['ep_vers_eu'] == 'Oui':
            ep_vers_eu += 1
        
        # Communes
        commune = feat['nom_com'] if 'nom_com' in feat.fields().names() else 'Inconnu'
        communes[commune] = communes.get(commune, 0) + 1
    
    print(f"\n✅ Conformes : {conformes} ({conformes/total*100:.1f}%)")
    print(f"❌ Non conformes : {non_conformes} ({non_conformes/total*100:.1f}%)")
    
    print(f"\n⚠️  Inversions EU → EP : {eu_vers_ep} ({eu_vers_ep/total*100:.1f}%)")
    print(f"⚠️  Inversions EP → EU : {ep_vers_eu} ({ep_vers_eu/total*100:.1f}%)")
    
    # Top 10 communes
    print(f"\n🏘️  Top 10 communes (nombre de PV) :")
    sorted_communes = sorted(communes.items(), key=lambda x: x[1], reverse=True)[:10]
    
    for i, (commune, count) in enumerate(sorted_communes, 1):
        print(f"   {i:2}. {commune:30} : {count:4} PV")
    
    print("\n" + "=" * 60)


# Fonction d'aide
def aide():
    """Affiche l'aide pour utiliser le module PV"""
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║           MODULE PV CONFORMITÉ - GUIDE D'UTILISATION         ║
╚═══════════════════════════════════════════════════════════════╝

📋 Commandes disponibles :

1️⃣ Afficher les statistiques PV :
   >>> stats_pv_conformite()

2️⃣ Tester le module PVAnalyzer :
   >>> test_pv_analyzer()

3️⃣ Utilisation manuelle :
   
   # Charger la couche PV
   pv_layer = QgsProject.instance().mapLayersByName('PV Conformité')[0]
   
   # Créer l'analyseur
   from cheminer_indus.core.pv_analyzer import PVAnalyzer
   pv_analyzer = PVAnalyzer(pv_layer)
   
   # Chercher les PV (après avoir calculé un cheminement)
   pv_list = pv_analyzer.find_pv_near_path(canalisations_features, 'EU')
   
   # Désigner un PV comme pollueur
   pv_analyzer.designate_as_polluter(pv_id)
   
   # Récupérer les infos
   info = pv_analyzer.get_polluter_info()

4️⃣ Afficher cette aide :
   >>> aide()

📞 Support : papademba.sene97@gmail.com
    """)


# Exécution automatique si lancé depuis la console
if __name__ == '__console__' or __name__ == '__main__':
    print("\n🚀 Module PVAnalyzer chargé !")
    print("   Tapez aide() pour voir les commandes disponibles")

