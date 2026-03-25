# ⚙️ Guide d'utilisation - Onglet Paramètres

## 🎯 Objectif

Personnaliser le **logo** et l'**icône** du plugin TRACK-EAU-POLL pour adapter l'interface et les rapports à votre identité visuelle.

---

## 📍 Accès à l'onglet

1. Ouvrir le plugin TRACK-EAU-POLL dans QGIS
2. Cliquer sur l'onglet **"⚙️ PARAMÈTRES"** (dernier onglet)

---

## 🖼️ Section Logo

### Aperçu
- Une prévisualisation du logo actuel (200x80 pixels)
- Affichage en temps réel des modifications

### Actions disponibles

#### 📁 Parcourir
1. Cliquer sur le bouton **"📁 Parcourir"**
2. Sélectionner une image (PNG, JPG, JPEG)
3. Le logo est mis à jour immédiatement dans l'aperçu

#### 🔄 Réinitialiser
1. Cliquer sur le bouton **"🔄 Réinitialiser"**
2. Confirmer l'action
3. Le logo par défaut est restauré

### Où apparaît le logo ?
- ✅ **Dans les rapports PDF** générés par le plugin
- ✅ **En haut de l'interface** du dock TRACK-EAU-POLL
- ✅ **Effet immédiat** (pas de redémarrage nécessaire)

### Recommandations
- **Format** : PNG avec transparence recommandé
- **Dimensions** : Largeur adaptative, hauteur max 80px
- **Poids** : Moins de 1 MB pour de meilleures performances

---

## ⭐ Section Icône

### Aperçu
- Une prévisualisation de l'icône actuelle (64x64 pixels)
- Affichage en temps réel des modifications

### Actions disponibles

#### 📁 Parcourir
1. Cliquer sur le bouton **"📁 Parcourir"**
2. Sélectionner une image (PNG, JPG, JPEG)
3. L'icône est mise à jour dans l'aperçu

#### 🔄 Réinitialiser
1. Cliquer sur le bouton **"🔄 Réinitialiser"**
2. Confirmer l'action
3. L'icône par défaut est restaurée

### Où apparaît l'icône ?
- ✅ **Barre d'outils QGIS** (icône du plugin)
- ✅ **Menu Extensions** de QGIS
- ⚠️ **Nécessite un redémarrage de QGIS** pour prendre effet

### Recommandations
- **Format** : PNG avec transparence (fond transparent)
- **Dimensions** : 64x64 pixels (carré)
- **Style** : Contraste élevé pour visibilité
- **Poids** : Moins de 500 KB

---

## 💾 Sauvegarde des paramètres

### Bouton "💾 Sauvegarder les paramètres"

#### Fonction
Enregistre vos paramètres personnalisés dans un fichier de configuration local.

#### Utilisation
1. Configurer le logo et/ou l'icône
2. Cliquer sur **"💾 Sauvegarder les paramètres"**
3. Confirmation affichée

#### Fichier créé
```
cheminer_indus/settings.json
```

Contenu :
```json
{
  "custom_logo_path": "/chemin/vers/votre/logo.png",
  "custom_icon_path": "/chemin/vers/votre/icon.png"
}
```

#### Persistance
- ✅ Paramètres **automatiquement rechargés** au démarrage du plugin
- ✅ Conservés après fermeture de QGIS
- ✅ Partagés entre sessions

---

## 📤 Export des paramètres

### Bouton "📤 Exporter les paramètres"

#### Fonction
Exporte vos paramètres dans un fichier JSON externe pour sauvegarde ou partage.

#### Utilisation
1. Configurer le logo et l'icône
2. Cliquer sur **"📤 Exporter les paramètres"**
3. Choisir l'emplacement et le nom du fichier
4. Fichier JSON créé

#### Cas d'usage
- **Backup** : Sauvegarde de vos paramètres
- **Partage** : Distribuer aux collègues
- **Multi-client** : Une configuration par client
- **Migration** : Transférer vers un autre poste

#### Exemple de fichier exporté
```json
{
  "custom_logo_path": "/home/user/logos/client_A.png",
  "custom_icon_path": "/home/user/icons/client_A.png",
  "exported_date": "2026-01-19 12:30:45"
}
```

---

## 📥 Import des paramètres

### Bouton "📥 Importer les paramètres"

#### Fonction
Importe des paramètres depuis un fichier JSON précédemment exporté.

#### Utilisation
1. Cliquer sur **"📥 Importer les paramètres"**
2. Sélectionner un fichier JSON
3. Les paramètres sont appliqués immédiatement
4. ⚠️ **Ne pas oublier** de cliquer sur "💾 Sauvegarder" ensuite !

#### Avantages
- **Gain de temps** : Configuration instantanée
- **Standardisation** : Mêmes paramètres sur tous les postes
- **Flexibilité** : Changement rapide selon le projet

---

## 🔄 Workflow recommandé

### Configuration initiale

```
1. Onglet ⚙️ PARAMÈTRES
2. 📁 Parcourir → Sélectionner logo
3. 📁 Parcourir → Sélectionner icône
4. 💾 Sauvegarder les paramètres
5. 🔄 Redémarrer QGIS (pour l'icône)
6. ✅ Plugin configuré !
```

### Changement de client

```
1. 📥 Importer les paramètres (client_B.json)
2. 💾 Sauvegarder les paramètres
3. 🔄 Redémarrer QGIS
4. ✅ Configuration client B active
```

### Backup de configuration

```
1. 📤 Exporter les paramètres
2. Sauvegarder le fichier JSON
3. ✅ Configuration sauvegardée
```

---

## 🎨 Exemples de personnalisation

### Exemple 1 : Collectivité locale

**Logo** : Blason de la ville (PNG, 200x80px)
**Icône** : Logo simplifié de la commune (64x64px)
**Utilisation** : Rapports officiels avec identité municipale

### Exemple 2 : Bureau d'études

**Logo** : Logo entreprise + slogan (PNG, 400x100px)
**Icône** : Initiales de l'entreprise (64x64px)
**Utilisation** : Branding professionnel sur tous les livrables

### Exemple 3 : Multi-sites

**Configuration A** : Site industriel Nord
**Configuration B** : Site industriel Sud
**Utilisation** : Import/export selon le site

---

## ⚠️ Points d'attention

### Logo

✅ **Effet immédiat dans :**
- Interface du plugin
- Nouveaux rapports PDF

❌ **Ne modifie PAS :**
- Rapports PDF déjà générés
- Logo dans les documents imprimés

### Icône

✅ **Visible après redémarrage dans :**
- Barre d'outils QGIS
- Menu Extensions

⚠️ **Nécessite impérativement :**
- Fermeture complète de QGIS
- Réouverture de QGIS
- Rechargement du plugin

❌ **Ne fonctionne PAS si :**
- Simple rechargement du plugin
- Cache QGIS non vidé

---

## 🐛 Dépannage

### Le logo ne s'affiche pas dans l'aperçu

**Causes possibles :**
- Chemin de fichier invalide
- Fichier corrompu
- Format non supporté

**Solutions :**
1. Vérifier que le fichier existe
2. Réessayer avec un autre fichier PNG
3. Utiliser **"🔄 Réinitialiser"** puis recommencer

---

### L'icône ne change pas après redémarrage

**Causes possibles :**
- Paramètres non sauvegardés
- Cache QGIS

**Solutions :**
1. Vérifier que **"💾 Sauvegarder"** a été cliqué
2. Fermer **complètement** QGIS (pas juste le plugin)
3. Supprimer le cache QGIS :
   ```
   Windows : C:\Users\[USER]\AppData\Roaming\QGIS\QGIS3\profiles\default\python\__pycache__
   Linux : ~/.local/share/QGIS/QGIS3/profiles/default/python/__pycache__
   ```
4. Rouvrir QGIS

---

### Le fichier settings.json n'est pas créé

**Causes possibles :**
- Permissions insuffisantes
- Erreur lors de la sauvegarde

**Solutions :**
1. Vérifier les permissions du dossier `cheminer_indus`
2. Exécuter QGIS en tant qu'administrateur (Windows)
3. Vérifier les logs d'erreur dans la console Python QGIS

---

### Import échoue

**Causes possibles :**
- Fichier JSON mal formaté
- Chemins de fichiers invalides dans le JSON

**Solutions :**
1. Vérifier la syntaxe JSON avec un validateur en ligne
2. Éditer les chemins dans le JSON pour qu'ils correspondent à votre système
3. Réexporter une nouvelle configuration propre

---

## 📋 Checklist de vérification

### Avant de générer un rapport

- [ ] Logo personnalisé configuré
- [ ] Logo sauvegardé
- [ ] Aperçu du logo correct dans l'onglet Paramètres
- [ ] Test de génération de rapport PDF
- [ ] Logo visible dans le rapport

### Avant de redémarrer QGIS (icône)

- [ ] Icône personnalisée configurée
- [ ] Icône sauvegardée
- [ ] Aperçu de l'icône correct dans l'onglet Paramètres
- [ ] QGIS fermé complètement
- [ ] QGIS rouvert
- [ ] Icône visible dans la barre d'outils

### Avant de partager une configuration

- [ ] Logo et icône testés
- [ ] Paramètres exportés
- [ ] Fichier JSON vérifié
- [ ] Instructions de déploiement fournies
- [ ] Chemins relatifs ou absolus documentés

---

## 💡 Astuces et bonnes pratiques

### 1. Organisation des fichiers

Créer une arborescence dédiée :
```
/mon_entreprise/
  /logos/
    logo_officiel.png
    logo_client_A.png
    logo_client_B.png
  /icones/
    icon_standard.png
    icon_client_A.png
  /configs/
    config_client_A.json
    config_client_B.json
```

### 2. Nommage des fichiers

Convention recommandée :
```
logo_[client]_[version].png
icon_[client]_[version].png
config_[client]_[date].json
```

Exemples :
```
logo_mairie_tours_v1.png
icon_mairie_tours_v1.png
config_mairie_tours_20260119.json
```

### 3. Versions de logo

Prévoir plusieurs versions :
- **logo_full.png** : Logo complet avec texte
- **logo_compact.png** : Logo sans texte
- **logo_mono.png** : Version monochrome

### 4. Backup automatique

Script bash pour sauvegarder automatiquement :
```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
cp cheminer_indus/settings.json backup/settings_$DATE.json
echo "Backup créé : settings_$DATE.json"
```

---

## 🔗 Liens utiles

- **Documentation plugin** : README.md
- **Guide rechargement** : RELOAD_PLUGIN.md
- **Nouvelles fonctionnalités** : NOUVELLES_FONCTIONNALITES.md
- **Repository GitHub** : https://github.com/papadembasene97-sudo/qgis_plugin

---

**Date de création** : 2026-01-19  
**Version** : v1.2.4  
**Auteur** : GenSpark AI Developer

---

## ✅ Récapitulatif rapide

| Action | Bouton | Effet | Redémarrage nécessaire |
|--------|--------|-------|------------------------|
| Parcourir logo | 📁 Parcourir | Sélectionner fichier logo | ❌ Non |
| Réinitialiser logo | 🔄 Réinitialiser | Restaurer logo par défaut | ❌ Non |
| Parcourir icône | 📁 Parcourir | Sélectionner fichier icône | ✅ Oui |
| Réinitialiser icône | 🔄 Réinitialiser | Restaurer icône par défaut | ✅ Oui |
| Sauvegarder | 💾 Sauvegarder | Enregistrer dans settings.json | ❌ Non |
| Exporter | 📤 Exporter | Créer fichier JSON externe | ❌ Non |
| Importer | 📥 Importer | Charger depuis fichier JSON | ❌ Non (puis sauvegarder) |

**🎉 Profitez de votre plugin personnalisé !**
