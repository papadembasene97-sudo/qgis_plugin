# 🔌 Connexion automatique PostgreSQL - CheminerIndus

## 📋 Comment le plugin accède aux données

### **Méthode actuelle (manuelle)**

1. **L'utilisateur charge manuellement** les couches dans QGIS
2. **Le plugin scanne** les couches QGIS disponibles
3. **L'utilisateur sélectionne** les couches dans les combos

❌ **Problème** : L'utilisateur doit charger 6-8 couches manuellement à chaque ouverture

---

### **🆕 Nouvelle méthode (automatique)**

Le plugin peut **charger automatiquement** toutes les couches nécessaires depuis PostgreSQL.

**Fichier créé** : `cheminer_indus/core/postgres_connector.py`

---

## 🚀 Utilisation

### **Option recommandée : Bouton dans l'onglet COUCHES**

Ajouter un bouton "Charger automatiquement depuis PostgreSQL" qui :
1. Détecte les connexions PostgreSQL QGIS
2. Charge toutes les couches nécessaires
3. Remplit automatiquement les combos

---

## 📊 Couches chargées automatiquement

1. ✅ **Canalisations** (`raepa.raepa_canalass_l`)
2. ✅ **Ouvrages** (`raepa.raepa_ouvrass_p`)
3. ✅ **Industriels** (`sig.Indus`)
4. ✅ **Liaisons** (`sig.liaison_indus`)
5. ✅ **🆕 Données IA** (`cheminer_indus.donnees_entrainement_ia`)
6. ⚙️ Points noirs EGIS (optionnel)
7. ⚙️ PV Conformité (optionnel)

---

## ⚙️ Configuration utilisateur

**Prérequis** : Connexion PostgreSQL dans QGIS

```
QGIS → Couche → PostGIS → Nouvelle connexion
→ Configurer une fois, utilisé automatiquement après
```

---

## 🎯 Avantages

- ✅ **1 clic** au lieu de 8 chargements manuels
- ✅ **30 secondes** au lieu de 5-10 minutes
- ✅ **Noms standardisés** automatiquement
- ✅ **Pas d'oubli** de couche

---

**Fichier** : `cheminer_indus/core/postgres_connector.py` (créé)
**Documentation** : Ce fichier
**Statut** : ✅ Prêt à intégrer dans le plugin
