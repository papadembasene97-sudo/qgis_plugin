"""
Script de conversion PKL (Pickle) vers CSV
CheminerIndus - Version 1.2.2
"""

import pandas as pd
import os

# ============================================
# CONFIGURATION
# ============================================

# ⚠️ MODIFIER CES CHEMINS SELON VOTRE INSTALLATION
FICHIER_PKL = 'P:/BASES_SIG/ProjetQGIS/model_ia/donnees_ia.pkl'
FICHIER_CSV = 'P:/BASES_SIG/ProjetQGIS/model_ia/donnees_ia_from_pkl.csv'

# ============================================
# PROGRAMME PRINCIPAL
# ============================================

def convertir_pkl_vers_csv(fichier_pkl, fichier_csv):
    """Convertit un fichier PKL en CSV"""
    
    print("="*60)
    print("🔄 CONVERSION PKL → CSV")
    print("="*60)
    
    # 1. Vérifier que le fichier PKL existe
    if not os.path.exists(fichier_pkl):
        print(f"\n❌ ERREUR : Fichier introuvable")
        print(f"   Chemin : {fichier_pkl}")
        return False
    
    print(f"\n📂 Chargement du PKL...")
    print(f"   Fichier : {fichier_pkl}")
    
    try:
        # 2. Charger le PKL avec pandas
        df = pd.read_pickle(fichier_pkl)
        
        print(f"✓ PKL chargé avec succès")
        print(f"   • {len(df)} lignes")
        print(f"   • {len(df.columns)} colonnes")
        print(f"   • Taille : {os.path.getsize(fichier_pkl) / (1024*1024):.2f} MB")
        
        # 3. Afficher les premières lignes
        print(f"\n📋 Aperçu des données (5 premières lignes) :")
        print(df.head())
        
        # 4. Sauvegarder en CSV
        print(f"\n💾 Sauvegarde en CSV...")
        print(f"   Fichier : {fichier_csv}")
        
        df.to_csv(fichier_csv, index=False, encoding='utf-8-sig')
        
        print(f"✓ CSV sauvegardé avec succès")
        print(f"   • Taille : {os.path.getsize(fichier_csv) / (1024*1024):.2f} MB")
        
        # 5. Résumé
        print("\n" + "="*60)
        print("🎉 CONVERSION TERMINÉE AVEC SUCCÈS !")
        print("="*60)
        
        print(f"\n📊 Résumé :")
        print(f"   • Fichier PKL   : {fichier_pkl}")
        print(f"   • Fichier CSV   : {fichier_csv}")
        print(f"   • Lignes        : {len(df)}")
        print(f"   • Colonnes      : {len(df.columns)}")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR lors de la conversion : {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Lancer la conversion
    succes = convertir_pkl_vers_csv(FICHIER_PKL, FICHIER_CSV)
    
    if succes:
        print("✅ Tout s'est bien passé !")
    else:
        print("❌ La conversion a échoué.")
