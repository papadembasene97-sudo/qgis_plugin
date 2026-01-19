#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour vérifier la détection de la couche PV_CONFORMITE
À exécuter dans la console Python de QGIS
"""

from qgis.core import QgsProject

print("=" * 60)
print("TEST DE DÉTECTION PV_CONFORMITE")
print("=" * 60)

# Liste toutes les couches du projet
layers = QgsProject.instance().mapLayers().values()
print(f"\n📊 Nombre total de couches dans QGIS: {len(layers)}")
print("-" * 60)

# Vérifier chaque couche
pv_layers_found = []

for lyr in layers:
    name_original = lyr.name()
    name_lower = name_original.lower()
    
    # Afficher toutes les couches
    print(f"\n🗂️  Couche: {name_original}")
    print(f"   Type: {lyr.type()}")
    print(f"   Valide: {lyr.isValid()}")
    
    # Tests de détection
    has_pv = "pv" in name_lower
    has_conform = "conform" in name_lower
    has_confomit = "confomit" in name_lower
    
    if has_pv:
        print(f"   ✅ Contient 'pv': OUI")
        print(f"   {'✅' if has_conform else '❌'} Contient 'conform': {has_conform}")
        print(f"   {'✅' if has_confomit else '❌'} Contient 'confomit': {has_confomit}")
        
        # Test de la condition complète
        detected = has_pv and (has_conform or has_confomit)
        print(f"   {'🎯 DÉTECTÉE' if detected else '❌ NON DÉTECTÉE'}: {detected}")
        
        if detected:
            pv_layers_found.append(name_original)
    
print("\n" + "=" * 60)
print("RÉSUMÉ")
print("=" * 60)

if pv_layers_found:
    print(f"✅ {len(pv_layers_found)} couche(s) PV détectée(s):")
    for name in pv_layers_found:
        print(f"   - {name}")
else:
    print("❌ Aucune couche PV détectée!")
    print("\nVérifiez que votre couche:")
    print("   1. Est chargée dans QGIS (visible dans le panneau des couches)")
    print("   2. Contient 'pv' dans son nom")
    print("   3. Contient 'conform' OU 'confomit' dans son nom")
    print("\nExemples de noms valides:")
    print("   ✅ PV_CONFORMITE")
    print("   ✅ PV_CONFOMITE")
    print("   ✅ osmose.PV_CONFORMITE")
    print("   ✅ pv_conform")

print("\n" + "=" * 60)
print("RECOMMANDATIONS")
print("=" * 60)

# Chercher des couches qui pourraient être des PV
potential_pv = []
for lyr in layers:
    name_lower = lyr.name().lower()
    if "pv" in name_lower and "conform" not in name_lower and "confomit" not in name_lower:
        potential_pv.append(lyr.name())

if potential_pv:
    print("\n⚠️  Couches contenant 'pv' mais sans 'conform':")
    for name in potential_pv:
        print(f"   - {name}")
        print(f"     → Renommer en: {name}_CONFORMITE")

print("\n" + "=" * 60)
print("FIN DU TEST")
print("=" * 60)
