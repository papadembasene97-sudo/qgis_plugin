# 🎯 Guide d'intégration rapide - Module PV

## Installation

### 1. Copier le fichier PVAnalyzer

```bash
# Le fichier est déjà créé :
cheminer_indus/core/pv_analyzer.py
```

### 2. Charger la couche PV_CONFORMITE dans QGIS

**Via le connecteur PostgreSQL automatique (recommandé) :**

Le connecteur charge automatiquement :
- ✅ `raepa.raepa_canalass_l`
- ✅ `raepa.raepa_ouvrass_p`
- ✅ `sig.Indus`
- ✅ `sig.liaison_indus`
- ✅ `cheminer_indus.donnees_entrainement_ia`
- ✅ `exploit.PV_CONFORMITE` ← **NOUVEAU**

**Manuellement :**

```
QGIS → Couche → Ajouter une couche → PostgreSQL
→ Connexion → Schema: exploit → Table: PV_CONFORMITE → Ajouter
```

---

## Utilisation dans le code

### Étape 1 : Importer le module

```python
from cheminer_indus.core.pv_analyzer import PVAnalyzer
```

### Étape 2 : Initialiser

```python
# Récupérer la couche PV
pv_layer = QgsProject.instance().mapLayersByName('PV_CONFORMITE')[0]

# Créer l'analyseur
pv_analyzer = PVAnalyzer(pv_layer)
```

### Étape 3 : Détecter les PV lors du cheminement

```python
# Après avoir calculé le cheminement et récupéré les canalisations
canalisations_features = [...]  # Liste des QgsFeature

# Chercher les PV à 15m
pv_list = pv_analyzer.find_pv_near_path(canalisations_features, 'EU')

print(f"✅ {len(pv_list)} PV non conformes trouvés")

# Accès aux données
for pv in pv_list:
    print(f"  - {pv['adresse']}, {pv['commune']}")
    print(f"    Conforme: {pv['conforme']}")
    print(f"    EU→EP: {pv['eu_vers_ep']} | EP→EU: {pv['ep_vers_eu']}")
```

### Étape 4 : Gérer l'exclusion de branches

```python
# Quand une branche est exclue
canalisations_exclues = ['idcanal_12347', 'idcanal_12348', ...]

# Mettre à jour la liste des PV
pv_analyzer.update_after_exclusion(canalisations_exclues)

print(f"PV actifs : {pv_analyzer.get_pv_count()}")
```

### Étape 5 : Désigner un PV comme pollueur

```python
# L'utilisateur clique sur un PV (id = 14)
pv_id = 14

success = pv_analyzer.designate_as_polluter(pv_id)

if success:
    info = pv_analyzer.get_polluter_info()
    
    print(f"🎯 PV pollueur désigné :")
    print(f"  Type : {info['type']}")
    print(f"  Adresse : {info['adresse']}")
    print(f"  Commune : {info['commune']}")
    print(f"  Problèmes : {info['problemes_str']}")
```

### Étape 6 : Générer le rapport

```python
# Dans report_generator.py
polluter_info = pv_analyzer.get_polluter_info()

if polluter_info['type'] == 'PV non conforme':
    # Générer un rapport spécifique PV
    report_generator.generate_pv_pollution_report(
        polluter_info, 
        path_data
    )
```

---

## Intégration avec l'interface

### Dans `gui/main_dock.py` ou `gui/industrial_tab.py`

```python
from cheminer_indus.core.pv_analyzer import PVAnalyzer

class MainDock(QDockWidget):
    def __init__(self):
        # ... init existant ...
        
        # Ajouter l'analyseur PV
        self.pv_analyzer = None
    
    def on_cheminement_calculated(self, canalisations):
        """Appelé après le calcul du cheminement"""
        
        # Si la couche PV existe
        pv_layer = QgsProject.instance().mapLayersByName('PV_CONFORMITE')
        
        if pv_layer:
            pv_layer = pv_layer[0]
            
            # Initialiser l'analyseur
            if not self.pv_analyzer:
                self.pv_analyzer = PVAnalyzer(pv_layer)
            
            # Chercher les PV
            pv_list = self.pv_analyzer.find_pv_near_path(
                canalisations, 
                self.network_type
            )
            
            # Mettre à jour l'interface
            self.update_pv_list_widget(pv_list)
    
    def update_pv_list_widget(self, pv_list):
        """Affiche les PV dans un QListWidget"""
        
        self.pv_list_widget.clear()
        
        for pv in pv_list:
            # Créer l'item
            text = f"⚠️ {pv['adresse']}, {pv['commune']}"
            
            if pv['ep_vers_eu'] == 'Oui':
                text += " [EP→EU]"
            if pv['eu_vers_ep'] == 'Oui':
                text += " [EU→EP]"
            
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, pv['id'])  # Stocker l'ID
            
            self.pv_list_widget.addItem(item)
        
        # Mettre à jour le label
        self.label_pv_count.setText(f"PV non conformes : {len(pv_list)}")
    
    def on_pv_item_double_clicked(self, item):
        """Double-clic sur un PV → le désigner comme pollueur"""
        
        pv_id = item.data(Qt.UserRole)
        
        # Message de confirmation
        reply = QMessageBox.question(
            self,
            "Désigner comme pollueur",
            f"Désigner ce PV comme origine de pollution ?\n\n"
            f"{item.text()}\n\n"
            f"Un cheminement Amont → Aval sera calculé.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Désigner
            success = self.pv_analyzer.designate_as_polluter(pv_id)
            
            if success:
                # Calculer le cheminement
                self.calculate_path_from_pv()
    
    def on_exclude_branch(self, canalisations_exclues):
        """Appelé quand une branche est exclue"""
        
        # Mettre à jour les industriels (déjà fait)
        # ...
        
        # Mettre à jour les PV
        if self.pv_analyzer:
            pv_actifs = self.pv_analyzer.update_after_exclusion(
                canalisations_exclues
            )
            
            # Rafraîchir l'interface
            self.update_pv_list_widget(pv_actifs)
```

---

## Structure des données PV

### Dictionnaire retourné par `find_pv_near_path()`

```python
{
    'id': 14,
    'num_pv': 'GH.15.11.012',
    'adresse': '9 allée des Tournelles',
    'code_postal': '95500',
    'commune': 'LE THILLAY',
    'conforme': 'Non',
    'eu_vers_ep': 'Non',
    'ep_vers_eu': 'Oui',  # ← INVERSION !
    'date_pv': '2015/11/18',
    'nb_chamb': None,
    'surf_ep': 0,
    'lien_osmose': 'https://si.siah-croult.org/gestion-pv/pv/?action=voir&id=14',
    'lat': 49.000369,
    'lon': 2.469815,
    'canal_rattache': 'idcanal_12345',
    'distance': 12.3,  # mètres
    'geometry': QgsGeometry(...),
    'feature': QgsFeature(...)
}
```

### Dictionnaire retourné par `get_polluter_info()`

```python
{
    'type': 'PV non conforme',
    'id': 14,
    'num_pv': 'GH.15.11.012',
    'adresse': '9 allée des Tournelles',
    'code_postal': '95500',
    'commune': 'LE THILLAY',
    'conforme': 'Non',
    'eu_vers_ep': 'Non',
    'ep_vers_eu': 'Oui',
    'date_controle': '2015/11/18',
    'nb_chambres': None,
    'surf_ep': 0,
    'lien_osmose': 'https://...',
    'lat': 49.000369,
    'lon': 2.469815,
    'geometry': QgsGeometry(...),
    'problemes': ['EP → EU (inversion)'],
    'problemes_str': 'EP → EU (inversion)'
}
```

---

## Signaux Qt disponibles

```python
# Signal émis quand des PV sont trouvés
pv_analyzer.pv_found.connect(self.on_pv_found)

def on_pv_found(self, count):
    print(f"{count} PV non conformes détectés")

# Signal émis quand un PV est désigné comme pollueur
pv_analyzer.pv_designated.connect(self.on_pv_designated)

def on_pv_designated(self, pv_data):
    print(f"PV pollueur : {pv_data['adresse']}")
```

---

## Mise à jour du connecteur PostgreSQL

### Ajouter PV_CONFORMITE aux couches chargées

**Fichier : `cheminer_indus/core/postgres_connector.py`**

```python
# Ajouter dans la liste des couches
self.required_layers = {
    'raepa.raepa_canalass_l': 'Canalisations',
    'raepa.raepa_ouvrass_p': 'Ouvrages',
    'sig.Indus': 'Indus',
    'sig.liaison_indus': 'liaison_indus',
    'cheminer_indus.donnees_entrainement_ia': 'donnees_entrainement_ia',
    'exploit.PV_CONFORMITE': 'PV_CONFORMITE',  # ← AJOUTER
}

self.optional_layers = {
    'expoit.ASTREINTE-EXPLOIT': 'ASTREINTE-EXPLOIT',
    'sda.POINT_NOIR_EGIS': 'POINT_NOIR_EGIS',
}
```

---

## Checklist d'intégration

### ✅ Fichiers créés
- [x] `cheminer_indus/core/pv_analyzer.py`
- [ ] `cheminer_indus/gui/industrial_tab.py` (à créer)
- [ ] `cheminer_indus/report/pv_report_generator.py` (à créer)

### ✅ Modifications nécessaires
- [ ] `cheminer_indus/core/postgres_connector.py` → Ajouter PV_CONFORMITE
- [ ] `cheminer_indus/gui/main_dock.py` → Intégrer PVAnalyzer
- [ ] `cheminer_indus/report/report_generator.py` → Ajouter sections PV

### ✅ Tests
- [ ] Chargement de la couche PV_CONFORMITE
- [ ] Détection des PV à 15m du cheminement
- [ ] Exclusion de branches (PV retirés)
- [ ] Désignation d'un PV comme pollueur
- [ ] Génération du rapport PDF
- [ ] Export CSV

---

## Prochaines étapes

1. **Mettre à jour `postgres_connector.py`** pour charger `PV_CONFORMITE`
2. **Créer `industrial_tab.py`** avec l'interface complète
3. **Mettre à jour `report_generator.py`** pour les rapports PV
4. **Tester avec des données réelles**
5. **Documenter dans le README principal**

---

**Contact :** papademba.sene97@gmail.com  
**Version :** 1.2.3  
**Date :** 2026-01-16
