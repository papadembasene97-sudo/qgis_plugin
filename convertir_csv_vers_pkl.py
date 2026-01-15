"""
Script de conversion CSV vers PKL (Pickle)
CheminerIndus - Version 1.2.2
"""

import pandas as pd
import pickle
import os

# ============================================
# CONFIGURATION
# ============================================

# ⚠️ MODIFIER CES CHEMINS SELON VOTRE INSTALLATION
FICHIER_CSV = 'P:/BASES_SIG/ProjetQGIS/model_ia/donnees_ia.csv'
FICHIER_PKL = 'P:/BASES_SIG/ProjetQGIS/model_ia/donnees_ia.pkl'

# ============================================
# PROGRAMME PRINCIPAL
# ============================================

def convertir_csv_vers_pkl(fichier_csv, fichier_pkl):
    """Convertit un fichier CSV en PKL"""
    
    print("="*60)
    print("🔄 CONVERSION CSV → PKL")
    print("="*60)
    
    # 1. Vérifier que le fichier CSV existe
    if not os.path.exists(fichier_csv):
        print(f"\n❌ ERREUR : Fichier introuvable")
        print(f"   Chemin : {fichier_csv}")
        return False
    
    print(f"\n📂 Chargement du CSV...")
    print(f"   Fichier : {fichier_csv}")
    
    try:
        # 2. Charger le CSV avec pandas
        df = pd.read_csv(fichier_csv)
        
        print(f"✓ CSV chargé avec succès")
        print(f"   • {len(df)} lignes")
        print(f"   • {len(df.columns)} colonnes")
        print(f"   • Taille : {os.path.getsize(fichier_csv) / (1024*1024):.2f} MB")
        
        # 3. Afficher les premières lignes
        print(f"\n📋 Aperçu des données (5 premières lignes) :")
        print(df.head())
        
        # 4. Afficher les types de colonnes
        print(f"\n📊 Types de colonnes :")
        types_count = df.dtypes.value_counts()
        for dtype, count in types_count.items():
            print(f"   • {dtype}: {count} colonnes")
        
        # 5. Sauvegarder en PKL
        print(f"\n💾 Sauvegarde en PKL...")
        print(f"   Fichier : {fichier_pkl}")
        
        # Option 1 : Via pandas (recommandé)
        df.to_pickle(fichier_pkl)
        
        # Option 2 : Via pickle standard (alternative)
        # with open(fichier_pkl, 'wb') as f:
        #     pickle.dump(df, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        print(f"✓ PKL sauvegardé avec succès")
        print(f"   • Taille : {os.path.getsize(fichier_pkl) / (1024*1024):.2f} MB")
        
        # 6. Vérifier en rechargeant
        print(f"\n🔍 Vérification...")
        df_test = pd.read_pickle(fichier_pkl)
        
        if len(df_test) == len(df) and len(df_test.columns) == len(df.columns):
            print(f"✓ Vérification réussie : {len(df_test)} lignes, {len(df_test.columns)} colonnes")
        else:
            print(f"⚠️  Attention : différence détectée")
            print(f"   CSV : {len(df)} lignes, {len(df.columns)} colonnes")
            print(f"   PKL : {len(df_test)} lignes, {len(df_test.columns)} colonnes")
        
        # 7. Résumé
        print("\n" + "="*60)
        print("🎉 CONVERSION TERMINÉE AVEC SUCCÈS !")
        print("="*60)
        
        gain_taille = (1 - os.path.getsize(fichier_pkl) / os.path.getsize(fichier_csv)) * 100
        
        print(f"\n📊 Résumé :")
        print(f"   • Fichier CSV   : {fichier_csv}")
        print(f"   • Fichier PKL   : {fichier_pkl}")
        print(f"   • Lignes        : {len(df)}")
        print(f"   • Colonnes      : {len(df.columns)}")
        print(f"   • Gain de taille: {gain_taille:.1f}%")
        
        print(f"\n💡 Utilisation :")
        print(f"   df = pd.read_pickle('{fichier_pkl}')")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR lors de la conversion : {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Lancer la conversion
    succes = convertir_csv_vers_pkl(FICHIER_CSV, FICHIER_PKL)
    
    if succes:
        print("✅ Tout s'est bien passé !")
    else:
        print("❌ La conversion a échoué.")
