"""
Script d'entraînement du modèle IA de prédiction de pollution
TRACK-EAU-POLL - Version 1.2.1
"""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import os
from datetime import datetime

# ============================================
# CONFIGURATION
# ============================================

# ⚠️ MODIFIER CE CHEMIN SELON VOTRE INSTALLATION
DOSSIER_DONNEES = 'P:/BASES_SIG/ProjetQGIS/model_ia'

# Fichiers
FICHIER_CSV = f'{DOSSIER_DONNEES}/donnees_ia.csv'
FICHIER_MODELE = f'{DOSSIER_DONNEES}/modele_pollution_2026.pkl'
FICHIER_METADATA = f'{DOSSIER_DONNEES}/modele_metadata.pkl'
FICHIER_RAPPORT = f'{DOSSIER_DONNEES}/rapport_entrainement.txt'

# Paramètres du modèle
PARAMETRES_MODELE = {
    'n_estimators': 100,           # Nombre d'arbres
    'max_depth': 15,               # Profondeur maximale
    'min_samples_split': 10,       # Min échantillons pour split
    'min_samples_leaf': 5,         # Min échantillons par feuille
    'random_state': 42,
    'class_weight': 'balanced',    # Équilibrage automatique
    'n_jobs': -1                   # Utiliser tous les CPU
}

# ============================================
# FONCTIONS
# ============================================

def charger_donnees(fichier_csv):
    """Charge les données depuis le CSV"""
    print(f"📂 Chargement des données depuis : {fichier_csv}")
    
    if not os.path.exists(fichier_csv):
        raise FileNotFoundError(f"❌ Fichier introuvable : {fichier_csv}")
    
    df = pd.read_csv(fichier_csv)
    print(f"✓ {len(df)} exemples chargés")
    return df

def analyser_donnees(df):
    """Analyse et affiche les statistiques des données"""
    print("\n" + "="*60)
    print("📊 ANALYSE DES DONNÉES")
    print("="*60)
    
    print(f"\n📋 Colonnes disponibles ({len(df.columns)}) :")
    for i, col in enumerate(df.columns, 1):
        print(f"   {i:2d}. {col}")
    
    print(f"\n📈 Répartition des classes :")
    repartition = df['pollution_detectee_label'].value_counts()
    total = len(df)
    for label, count in repartition.items():
        nom = "Pollution détectée" if label == 1 else "Pas de pollution"
        pct = (count / total) * 100
        print(f"   {nom:20s} : {count:4d} ({pct:5.1f}%)")
    
    # Vérifier l'équilibre des classes
    if len(repartition) < 2:
        print("\n⚠️  ATTENTION : Une seule classe présente dans les données !")
        print("   Le modèle ne pourra pas apprendre correctement.")
        return False
    
    min_pct = (repartition.min() / total) * 100
    if min_pct < 10:
        print(f"\n⚠️  ATTENTION : Classe minoritaire < 10% ({min_pct:.1f}%)")
        print("   Le modèle risque d'être biaisé.")
    
    return True

def preparer_donnees(df):
    """Prépare les features et le label"""
    print("\n🔧 Préparation des données...")
    
    # Séparer X et y
    y = df['pollution_detectee_label']
    X = df.drop(['pollution_detectee_label'], axis=1)
    
    # ⚠️ CORRECTION : Exclure les colonnes non numériques
    colonnes_non_numeriques = X.select_dtypes(include=['object', 'string']).columns.tolist()
    if colonnes_non_numeriques:
        print(f"   ⚠️  Colonnes non-numériques exclues : {colonnes_non_numeriques}")
        X = X.drop(columns=colonnes_non_numeriques)
    
    # Remplacer NaN par 0
    nb_nan = X.isna().sum().sum()
    if nb_nan > 0:
        print(f"   ⚠️  {nb_nan} valeurs manquantes remplacées par 0")
        X = X.fillna(0)
    
    print(f"✓ {X.shape[1]} features numériques préparées")
    print(f"   Features utilisées : {X.columns.tolist()}")
    
    return X, y

def entrainer_modele(X_train, y_train, parametres):
    """Entraîne le modèle Random Forest"""
    print("\n🎓 Entraînement du modèle Random Forest...")
    print(f"   - Paramètres : {parametres}")
    
    modele = RandomForestClassifier(**parametres)
    modele.fit(X_train, y_train)
    
    print("✓ Entraînement terminé")
    return modele

def evaluer_modele(modele, X_test, y_test, feature_names):
    """Évalue et affiche les performances du modèle"""
    print("\n" + "="*60)
    print("🎯 ÉVALUATION DU MODÈLE")
    print("="*60)
    
    # Prédictions
    y_pred = modele.predict(X_test)
    y_proba = modele.predict_proba(X_test)
    
    # Précision globale
    precision = accuracy_score(y_test, y_pred)
    print(f"\n🎯 Précision globale : {precision*100:.1f}%")
    
    # Rapport détaillé
    print("\n📊 Rapport de classification :")
    print(classification_report(
        y_test, 
        y_pred, 
        target_names=['Pas de pollution (0)', 'Pollution détectée (1)'],
        digits=3
    ))
    
    # Matrice de confusion
    cm = confusion_matrix(y_test, y_pred)
    print("\n🔢 Matrice de confusion :")
    print(f"   ┌─────────────────────────────┐")
    print(f"   │ Vrais Négatifs    : {cm[0,0]:5d} │  (Correct: pas de pollution)")
    print(f"   │ Faux Positifs     : {cm[0,1]:5d} │  (Fausse alerte)")
    print(f"   │ Faux Négatifs     : {cm[1,0]:5d} │  (Pollution ratée ⚠️)")
    print(f"   │ Vrais Positifs    : {cm[1,1]:5d} │  (Correct: pollution détectée)")
    print(f"   └─────────────────────────────┘")
    
    # Importance des features
    importances = modele.feature_importances_
    indices_top = importances.argsort()[-10:][::-1]
    
    print("\n⭐ Top 10 des features les plus importantes :")
    for i, idx in enumerate(indices_top, 1):
        print(f"   {i:2d}. {feature_names[idx]:35s} : {importances[idx]*100:5.1f}%")
    
    return {
        'precision': precision,
        'confusion_matrix': cm,
        'feature_importances': dict(zip(feature_names, importances)),
        'y_pred': y_pred,
        'y_proba': y_proba
    }

def sauvegarder_modele(modele, feature_names, resultats, fichier_modele, fichier_metadata):
    """Sauvegarde le modèle et ses métadonnées"""
    print("\n💾 Sauvegarde du modèle...")
    
    # Sauvegarder le modèle
    joblib.dump(modele, fichier_modele)
    print(f"✓ Modèle sauvegardé : {fichier_modele}")
    
    # Sauvegarder les métadonnées
    metadata = {
        'feature_names': feature_names,
        'nb_features': len(feature_names),
        'precision': resultats['precision'],
        'confusion_matrix': resultats['confusion_matrix'].tolist(),
        'date_entrainement': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'parametres_modele': PARAMETRES_MODELE
    }
    joblib.dump(metadata, fichier_metadata)
    print(f"✓ Métadonnées sauvegardées : {fichier_metadata}")

def generer_rapport(resultats, fichier_rapport):
    """Génère un rapport texte d'entraînement"""
    print(f"\n📄 Génération du rapport : {fichier_rapport}")
    
    with open(fichier_rapport, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("RAPPORT D'ENTRAÎNEMENT - MODÈLE IA CHEMINER INDUS\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Fichier modèle : {FICHIER_MODELE}\n\n")
        
        f.write("PERFORMANCES\n")
        f.write("-"*70 + "\n")
        f.write(f"Précision globale : {resultats['precision']*100:.1f}%\n\n")
        
        cm = resultats['confusion_matrix']
        f.write("Matrice de confusion :\n")
        f.write(f"  Vrais Négatifs  : {cm[0,0]:5d}\n")
        f.write(f"  Faux Positifs   : {cm[0,1]:5d}\n")
        f.write(f"  Faux Négatifs   : {cm[1,0]:5d}\n")
        f.write(f"  Vrais Positifs  : {cm[1,1]:5d}\n\n")
        
        f.write("TOP 10 FEATURES IMPORTANTES\n")
        f.write("-"*70 + "\n")
        importances = resultats['feature_importances']
        top_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:10]
        for i, (feature, importance) in enumerate(top_features, 1):
            f.write(f"{i:2d}. {feature:40s} : {importance*100:5.1f}%\n")
    
    print("✓ Rapport généré")

# ============================================
# PROGRAMME PRINCIPAL
# ============================================

def main():
    """Fonction principale"""
    print("\n" + "="*60)
    print("🚀 ENTRAÎNEMENT MODÈLE IA - CHEMINER INDUS v1.2.1")
    print("="*60)
    
    try:
        # 1. Charger les données
        df = charger_donnees(FICHIER_CSV)
        
        # 2. Analyser les données
        if not analyser_donnees(df):
            print("\n❌ Entraînement annulé : données insuffisantes")
            return
        
        # 3. Préparer les données
        X, y = preparer_donnees(df)
        
        # 4. Split train/test
        print("\n🔀 Séparation train/test (80/20)...")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        print(f"✓ Train: {len(X_train)} | Test: {len(X_test)}")
        
        # 5. Entraîner le modèle
        modele = entrainer_modele(X_train, y_train, PARAMETRES_MODELE)
        
        # 6. Évaluer le modèle
        resultats = evaluer_modele(modele, X_test, y_test, X.columns.tolist())
        
        # 7. Sauvegarder
        sauvegarder_modele(
            modele, 
            X.columns.tolist(), 
            resultats,
            FICHIER_MODELE, 
            FICHIER_METADATA
        )
        
        # 8. Générer le rapport
        generer_rapport(resultats, FICHIER_RAPPORT)
        
        # Résumé final
        print("\n" + "="*60)
        print("🎉 ENTRAÎNEMENT TERMINÉ AVEC SUCCÈS !")
        print("="*60)
        print(f"\n📊 Résumé :")
        print(f"   • Précision : {resultats['precision']*100:.1f}%")
        print(f"   • Exemples utilisés : {len(df)}")
        print(f"   • Features : {len(X.columns)}")
        print(f"   • Modèle : {FICHIER_MODELE}")
        print(f"\n🎯 Prochaines étapes :")
        print(f"   1. Charger le modèle dans QGIS (TRACK-EAU-POLL → IA)")
        print(f"   2. Prédire les pollutions sur vos réseaux")
        print(f"   3. Optimiser vos parcours de visite")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
