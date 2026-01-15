"""
Script de test des prédictions du modèle IA
CheminerIndus - Version 1.2.1
"""

import pandas as pd
import joblib
import os

# ============================================
# CONFIGURATION
# ============================================

# ⚠️ MODIFIER CE CHEMIN SELON VOTRE INSTALLATION
DOSSIER_DONNEES = 'P:/BASES_SIG/ProjetQGIS/model_ia'

FICHIER_MODELE = f'{DOSSIER_DONNEES}/modele_pollution_2026.pkl'
FICHIER_METADATA = f'{DOSSIER_DONNEES}/modele_metadata.pkl'
FICHIER_DONNEES = f'{DOSSIER_DONNEES}/donnees_ia.csv'

# ============================================
# FONCTIONS
# ============================================

def charger_modele(fichier_modele, fichier_metadata):
    """Charge le modèle et ses métadonnées"""
    print(f"📂 Chargement du modèle : {fichier_modele}")
    
    if not os.path.exists(fichier_modele):
        raise FileNotFoundError(f"❌ Modèle introuvable : {fichier_modele}")
    
    modele = joblib.load(fichier_modele)
    metadata = joblib.load(fichier_metadata)
    
    print(f"✓ Modèle chargé")
    print(f"   - Date d'entraînement : {metadata['date_entrainement']}")
    print(f"   - Précision : {metadata['precision']*100:.1f}%")
    print(f"   - Features : {metadata['nb_features']}")
    
    return modele, metadata

def predire_pollution(modele, metadata, X):
    """Prédit la probabilité de pollution pour chaque nœud"""
    print(f"\n🔮 Prédiction en cours sur {len(X)} nœuds...")
    
    # Vérifier que toutes les features sont présentes
    feature_names = metadata['feature_names']
    missing_features = set(feature_names) - set(X.columns)
    if missing_features:
        print(f"⚠️  Features manquantes : {missing_features}")
        # Ajouter les features manquantes avec valeur 0
        for feature in missing_features:
            X[feature] = 0
    
    # Réorganiser les colonnes dans le bon ordre
    X = X[feature_names]
    
    # Remplacer NaN par 0
    X = X.fillna(0)
    
    # Prédire
    predictions = modele.predict(X)
    probabilites = modele.predict_proba(X)
    
    print("✓ Prédictions terminées")
    
    return predictions, probabilites

def analyser_predictions(predictions, probabilites):
    """Analyse et affiche les statistiques des prédictions"""
    print("\n" + "="*60)
    print("📊 ANALYSE DES PRÉDICTIONS")
    print("="*60)
    
    # Répartition des prédictions
    nb_pollution = (predictions == 1).sum()
    nb_pas_pollution = (predictions == 0).sum()
    total = len(predictions)
    
    print(f"\n📈 Répartition des prédictions :")
    print(f"   Pollution détectée    : {nb_pollution:4d} ({nb_pollution/total*100:5.1f}%)")
    print(f"   Pas de pollution      : {nb_pas_pollution:4d} ({nb_pas_pollution/total*100:5.1f}%)")
    
    # Niveaux de risque
    proba_pollution = probabilites[:, 1] * 100  # Probabilité classe 1 (pollution)
    
    critique = (proba_pollution >= 80).sum()
    eleve = ((proba_pollution >= 60) & (proba_pollution < 80)).sum()
    moyen = ((proba_pollution >= 40) & (proba_pollution < 60)).sum()
    faible = (proba_pollution < 40).sum()
    
    print(f"\n🎯 Niveaux de risque :")
    print(f"   CRITIQUE (≥80%)       : {critique:4d} nœuds 🔴")
    print(f"   ÉLEVÉ (60-79%)        : {eleve:4d} nœuds 🟠")
    print(f"   MOYEN (40-59%)        : {moyen:4d} nœuds 🟡")
    print(f"   FAIBLE (<40%)         : {faible:4d} nœuds 🟢")
    
    return proba_pollution

def afficher_top_risques(df, predictions, probabilites, top_n=20):
    """Affiche les nœuds à plus haut risque"""
    print(f"\n⚠️  TOP {top_n} NŒUDS À RISQUE CRITIQUE")
    print("="*60)
    
    # Ajouter les prédictions au DataFrame
    df_resultat = df.copy()
    df_resultat['prediction'] = predictions
    df_resultat['proba_pollution'] = probabilites[:, 1] * 100
    
    # Définir le niveau de risque
    def niveau_risque(proba):
        if proba >= 80:
            return 'CRITIQUE 🔴'
        elif proba >= 60:
            return 'ÉLEVÉ 🟠'
        elif proba >= 40:
            return 'MOYEN 🟡'
        else:
            return 'FAIBLE 🟢'
    
    df_resultat['niveau_risque'] = df_resultat['proba_pollution'].apply(niveau_risque)
    
    # Trier par probabilité décroissante
    df_top = df_resultat.nlargest(top_n, 'proba_pollution')
    
    # Afficher
    print(f"\n{'Rang':<5} {'ID Nœud':<15} {'Proba':<8} {'Niveau':<15} {'Inversions':<12} {'Industriels':<12} {'Historique'}")
    print("-" * 100)
    
    for i, (idx, row) in enumerate(df_top.iterrows(), 1):
        id_noeud = row.get('id_noeud', f'Nœud_{idx}')
        proba = row['proba_pollution']
        niveau = row['niveau_risque']
        inversions = row.get('nb_inversions_total', 0)
        industriels = row.get('nb_industriels', 0)
        pollutions = row.get('nb_pollutions', 0)
        
        print(f"{i:<5} {str(id_noeud):<15} {proba:6.1f}%  {niveau:<15} {inversions:<12} {industriels:<12} {pollutions}")
    
    return df_resultat

def sauvegarder_predictions(df_resultat, fichier_sortie):
    """Sauvegarde les prédictions dans un CSV"""
    print(f"\n💾 Sauvegarde des prédictions : {fichier_sortie}")
    
    # Sélectionner les colonnes importantes
    colonnes_sortie = [
        'id_noeud', 'commune', 
        'prediction', 'proba_pollution', 'niveau_risque',
        'nb_inversions_total', 'nb_industriels', 'nb_pollutions',
        'score_risque_calcule'
    ]
    
    # Filtrer les colonnes existantes
    colonnes_existantes = [col for col in colonnes_sortie if col in df_resultat.columns]
    
    df_sortie = df_resultat[colonnes_existantes]
    df_sortie.to_csv(fichier_sortie, index=False, encoding='utf-8-sig')
    
    print(f"✓ {len(df_sortie)} prédictions sauvegardées")

# ============================================
# PROGRAMME PRINCIPAL
# ============================================

def main():
    """Fonction principale"""
    print("\n" + "="*60)
    print("🔮 TEST DES PRÉDICTIONS - CHEMINER INDUS v1.2.1")
    print("="*60)
    
    try:
        # 1. Charger le modèle
        modele, metadata = charger_modele(FICHIER_MODELE, FICHIER_METADATA)
        
        # 2. Charger les données de test
        print(f"\n📂 Chargement des données : {FICHIER_DONNEES}")
        df = pd.read_csv(FICHIER_DONNEES)
        print(f"✓ {len(df)} nœuds chargés")
        
        # 3. Préparer les features (sans le label)
        if 'pollution_detectee_label' in df.columns:
            label_reel = df['pollution_detectee_label']
            X = df.drop(['pollution_detectee_label'], axis=1)
        else:
            label_reel = None
            X = df.copy()
        
        # 4. Prédire
        predictions, probabilites = predire_pollution(modele, metadata, X)
        
        # 5. Analyser les prédictions
        proba_pollution = analyser_predictions(predictions, probabilites)
        
        # 6. Afficher les nœuds à risque
        df_resultat = afficher_top_risques(df, predictions, probabilites, top_n=20)
        
        # 7. Comparer avec la réalité (si disponible)
        if label_reel is not None:
            print("\n" + "="*60)
            print("✅ COMPARAISON AVEC LA RÉALITÉ")
            print("="*60)
            
            from sklearn.metrics import accuracy_score, confusion_matrix
            
            precision = accuracy_score(label_reel, predictions)
            cm = confusion_matrix(label_reel, predictions)
            
            print(f"\n🎯 Précision : {precision*100:.1f}%")
            print(f"\nMatrice de confusion :")
            print(f"   Vrais Négatifs  : {cm[0,0]:5d}")
            print(f"   Faux Positifs   : {cm[0,1]:5d}")
            print(f"   Faux Négatifs   : {cm[1,0]:5d}")
            print(f"   Vrais Positifs  : {cm[1,1]:5d}")
        
        # 8. Sauvegarder les résultats
        fichier_sortie = f'{DOSSIER_DONNEES}/predictions_resultats.csv'
        sauvegarder_predictions(df_resultat, fichier_sortie)
        
        # Résumé final
        print("\n" + "="*60)
        print("🎉 TEST TERMINÉ AVEC SUCCÈS !")
        print("="*60)
        print(f"\n📊 Résumé :")
        print(f"   • Nœuds analysés : {len(df)}")
        print(f"   • Nœuds à risque CRITIQUE : {(proba_pollution >= 80).sum()}")
        print(f"   • Fichier résultats : {fichier_sortie}")
        print(f"\n🎯 Prochaines étapes :")
        print(f"   1. Importer predictions_resultats.csv dans QGIS")
        print(f"   2. Visualiser les nœuds à risque sur la carte")
        print(f"   3. Planifier les visites prioritaires")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
