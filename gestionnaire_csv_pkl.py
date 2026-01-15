"""
Gestionnaire de conversions CSV ↔ PKL
CheminerIndus - Version 1.2.2
Menu interactif pour toutes les conversions
"""

import pandas as pd
import os
import sys

# ============================================
# FONCTIONS DE CONVERSION
# ============================================

def convertir_csv_vers_pkl(fichier_csv, fichier_pkl=None):
    """Convertit CSV → PKL"""
    
    if fichier_pkl is None:
        fichier_pkl = fichier_csv.replace('.csv', '.pkl')
    
    print(f"\n📂 Chargement de {fichier_csv}...")
    df = pd.read_csv(fichier_csv)
    
    print(f"✓ {len(df)} lignes, {len(df.columns)} colonnes chargées")
    
    print(f"💾 Sauvegarde en {fichier_pkl}...")
    df.to_pickle(fichier_pkl)
    
    taille_csv = os.path.getsize(fichier_csv) / (1024*1024)
    taille_pkl = os.path.getsize(fichier_pkl) / (1024*1024)
    gain = (1 - taille_pkl / taille_csv) * 100
    
    print(f"✓ Conversion réussie !")
    print(f"   CSV : {taille_csv:.2f} MB")
    print(f"   PKL : {taille_pkl:.2f} MB")
    print(f"   Gain : {gain:.1f}%")
    
    return fichier_pkl

def convertir_pkl_vers_csv(fichier_pkl, fichier_csv=None):
    """Convertit PKL → CSV"""
    
    if fichier_csv is None:
        fichier_csv = fichier_pkl.replace('.pkl', '.csv')
    
    print(f"\n📂 Chargement de {fichier_pkl}...")
    df = pd.read_pickle(fichier_pkl)
    
    print(f"✓ {len(df)} lignes, {len(df.columns)} colonnes chargées")
    
    print(f"💾 Sauvegarde en {fichier_csv}...")
    df.to_csv(fichier_csv, index=False, encoding='utf-8-sig')
    
    taille_pkl = os.path.getsize(fichier_pkl) / (1024*1024)
    taille_csv = os.path.getsize(fichier_csv) / (1024*1024)
    
    print(f"✓ Conversion réussie !")
    print(f"   PKL : {taille_pkl:.2f} MB")
    print(f"   CSV : {taille_csv:.2f} MB")
    
    return fichier_csv

def afficher_info_fichier(fichier):
    """Affiche les informations d'un fichier"""
    
    if not os.path.exists(fichier):
        print(f"❌ Fichier introuvable : {fichier}")
        return
    
    extension = os.path.splitext(fichier)[1].lower()
    
    print(f"\n📋 Informations sur : {fichier}")
    print(f"   Taille : {os.path.getsize(fichier) / (1024*1024):.2f} MB")
    
    try:
        if extension == '.csv':
            df = pd.read_csv(fichier, nrows=5)
        elif extension == '.pkl':
            df = pd.read_pickle(fichier)
        else:
            print(f"⚠️  Format non supporté : {extension}")
            return
        
        # Compter toutes les lignes
        if extension == '.csv':
            df_full = pd.read_csv(fichier)
        else:
            df_full = df
        
        print(f"   Lignes : {len(df_full)}")
        print(f"   Colonnes : {len(df_full.columns)}")
        print(f"\n📊 Colonnes :")
        for i, col in enumerate(df_full.columns, 1):
            dtype = df_full[col].dtype
            print(f"   {i:2d}. {col:30s} ({dtype})")
        
        print(f"\n📋 Aperçu (5 premières lignes) :")
        print(df.head())
        
    except Exception as e:
        print(f"❌ Erreur lors de la lecture : {e}")

# ============================================
# MENU INTERACTIF
# ============================================

def menu_principal():
    """Affiche le menu principal"""
    
    print("\n" + "="*60)
    print("🔄 GESTIONNAIRE CSV ↔ PKL - CheminerIndus v1.2.2")
    print("="*60)
    print("\n📋 MENU :")
    print("   1. Convertir CSV → PKL")
    print("   2. Convertir PKL → CSV")
    print("   3. Afficher infos d'un fichier")
    print("   4. Conversion par défaut (donnees_ia.csv → .pkl)")
    print("   0. Quitter")
    print()

def demander_fichier(prompt, extension_attendue=None):
    """Demande un chemin de fichier à l'utilisateur"""
    
    fichier = input(f"{prompt}\n> ").strip().strip('"').strip("'")
    
    if not fichier:
        return None
    
    # Remplacer les backslashes par des slashes
    fichier = fichier.replace('\\', '/')
    
    if not os.path.exists(fichier):
        print(f"⚠️  Fichier introuvable : {fichier}")
        return None
    
    if extension_attendue:
        extension = os.path.splitext(fichier)[1].lower()
        if extension != extension_attendue:
            print(f"⚠️  Extension attendue : {extension_attendue}, trouvée : {extension}")
            return None
    
    return fichier

def main():
    """Fonction principale"""
    
    while True:
        try:
            menu_principal()
            choix = input("Votre choix : ").strip()
            
            if choix == '0':
                print("\n👋 Au revoir !")
                break
            
            elif choix == '1':
                # CSV → PKL
                print("\n" + "="*60)
                print("📥 CONVERSION CSV → PKL")
                print("="*60)
                
                fichier_csv = demander_fichier("Entrez le chemin du fichier CSV :", ".csv")
                if fichier_csv:
                    fichier_pkl = convertir_csv_vers_pkl(fichier_csv)
                    print(f"\n✅ Fichier PKL créé : {fichier_pkl}")
            
            elif choix == '2':
                # PKL → CSV
                print("\n" + "="*60)
                print("📤 CONVERSION PKL → CSV")
                print("="*60)
                
                fichier_pkl = demander_fichier("Entrez le chemin du fichier PKL :", ".pkl")
                if fichier_pkl:
                    fichier_csv = convertir_pkl_vers_csv(fichier_pkl)
                    print(f"\n✅ Fichier CSV créé : {fichier_csv}")
            
            elif choix == '3':
                # Afficher infos
                print("\n" + "="*60)
                print("📋 INFORMATIONS FICHIER")
                print("="*60)
                
                fichier = demander_fichier("Entrez le chemin du fichier (CSV ou PKL) :")
                if fichier:
                    afficher_info_fichier(fichier)
            
            elif choix == '4':
                # Conversion par défaut
                print("\n" + "="*60)
                print("⚡ CONVERSION RAPIDE")
                print("="*60)
                
                fichier_csv = 'P:/BASES_SIG/ProjetQGIS/model_ia/donnees_ia.csv'
                fichier_pkl = 'P:/BASES_SIG/ProjetQGIS/model_ia/donnees_ia.pkl'
                
                print(f"Fichier source : {fichier_csv}")
                print(f"Fichier cible  : {fichier_pkl}")
                
                if os.path.exists(fichier_csv):
                    convertir_csv_vers_pkl(fichier_csv, fichier_pkl)
                    print(f"\n✅ Conversion terminée !")
                else:
                    print(f"\n❌ Fichier CSV introuvable : {fichier_csv}")
            
            else:
                print(f"\n⚠️  Choix invalide : {choix}")
            
            input("\nAppuyez sur Entrée pour continuer...")
        
        except KeyboardInterrupt:
            print("\n\n👋 Interruption par l'utilisateur. Au revoir !")
            break
        
        except Exception as e:
            print(f"\n❌ ERREUR : {e}")
            import traceback
            traceback.print_exc()
            input("\nAppuyez sur Entrée pour continuer...")

if __name__ == "__main__":
    main()
