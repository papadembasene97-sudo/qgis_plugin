#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de vérification syntaxique du plugin optimisé
"""

import sys
import ast

def check_syntax(file_path):
    """Vérifie la syntaxe Python d'un fichier."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Compiler pour vérifier la syntaxe
        ast.parse(content)
        print(f"✅ {file_path} : Syntaxe valide")
        return True
    except SyntaxError as e:
        print(f"❌ {file_path} : Erreur de syntaxe")
        print(f"   Ligne {e.lineno}: {e.msg}")
        print(f"   {e.text}")
        return False
    except Exception as e:
        print(f"⚠️  {file_path} : Erreur lors de la vérification")
        print(f"   {str(e)}")
        return False

def main():
    files_to_check = [
        "/home/user/webapp/cheminer_indus/gui/main_dock.py",
        "/home/user/webapp/cheminer_indus/gui/main_dock_optimized.py",
    ]
    
    all_valid = True
    for file_path in files_to_check:
        if not check_syntax(file_path):
            all_valid = False
    
    if all_valid:
        print("\n🎉 Tous les fichiers sont syntaxiquement corrects !")
        return 0
    else:
        print("\n⚠️  Certains fichiers contiennent des erreurs.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
