# Guide d’utilisation complet — Agents TRACK-EAU-POLL

> **Objectif** : Ce guide décrit de manière claire et intuitive toutes les fonctionnalités du plugin **TRACK-EAU-POLL**, avec des emplacements dédiés pour insérer vos captures d’écran.

---

## 1) Vue d’ensemble

TRACK-EAU-POLL permet de :
- **Cheminer** un réseau (amont/aval) pour analyser les écoulements.
- **Identifier** les industriels connectés.
- **Détecter** les PV liés au réseau et analyser leur conformité.
- **Gérer** des visites, désélections de branches, et générer des rapports.
- **Paramétrer** vos couches SIG pour une intégration rapide.

> 📸 **Capture à insérer** : Vue générale du plugin  
> _[Capture 1 : Interface principale]_

---

## 2) Démarrage rapide (3 minutes)

1. **Ouvrir le plugin** depuis la barre d’outils QGIS.  
2. Aller dans **⚙️ PARAMÈTRES** et **sélectionner les couches** (canalisations, ouvrages, industriels, liaisons, PV…).  
3. Revenir dans **CHEMINEMENT**, saisir un **ID ouvrage départ**.  
4. Cliquer sur **Cheminer**.

> 📸 **Capture à insérer** : Paramètres des couches  
> _[Capture 2 : Sélection des couches SIG]_

> 📸 **Capture à insérer** : Cheminement en cours  
> _[Capture 3 : Onglet Cheminement]_

---

## 3) Onglet **CHEMINEMENT**

### 3.1 Saisir un ID de départ
- **ID ouvrage départ** : identifiant du nœud de départ.
- **Sélection carte** : choisir un nœud directement sur la carte.

> 📸 _[Capture 4 : Saisie ID ouvrage + sélection carte]_

### 3.2 Rechercher un ouvrage
- Utiliser **Recherche** pour filtrer et retrouver un ouvrage par nom/ID.

> 📸 _[Capture 5 : Recherche d’ouvrage]_

### 3.3 Type de cheminement
- **Amont vers Aval** : trace le réseau de l’amont vers l’aval.
- **Aval vers Amont** : trace le réseau de l’aval vers l’amont.
- **Cheminement Pollution** : trace et détecte industriels + PV.

> 📸 _[Capture 6 : Choix du type de cheminement]_

### 3.4 Filtres réseau
- **Catégorie** : EU, EP, Unitaire.
- **Fonction** : Transport, Collecte.

> 📸 _[Capture 7 : Filtres de réseau]_

### 3.5 Boutons rapides
- **Cheminer** : lance la trace.
- **Flux** : affiche/masque les flux.
- **Couleurs** : personnalise les couleurs du réseau.

> 📸 _[Capture 8 : Boutons Cheminer / Flux / Couleurs]_

---

## 4) Onglet **VISITE‑INDUS**

### 4.1 Visites de nœuds
- **Visiter (Pollué O/N)** : enregistre la visite du nœud.
- Les visites alimentent le suivi et les diagnostics.

> 📸 _[Capture 9 : Visites de nœuds]_

### 4.2 Industriels connectés
- **Afficher Indus connectés** : ouvre le dock avec la liste des industriels.

> 📸 _[Capture 10 : Liste des industriels]_

### 4.3 Notes de pollution
- Renseignez une **note** associée à un pollueur.

> 📸 _[Capture 11 : Notes de pollution]_

### 4.4 Rattacher une astreinte
- Associe un contact d’astreinte à une situation donnée.

> 📸 _[Capture 12 : Rattacher astreinte]_

---

## 5) Onglet **ACTIONS**

### 5.1 Bassin de collecte
- Génère un **bassin de collecte** (en aval→amont).

> 📸 _[Capture 13 : Bassin de collecte]_

### 5.2 Diagnostics
- Lancer un diagnostic complet sur le réseau sélectionné.

> 📸 _[Capture 14 : Diagnostic réseau]_

### 5.3 Rapport
- Générer un rapport PDF automatiquement.

> 📸 _[Capture 15 : Génération rapport]_

---

## 6) Onglet **🏠 PV**

### 6.1 Analyse PV (conformes & non conformes)
- Cliquer sur **Analyser le cheminement** pour détecter les PV proches du réseau.
- Les PV sont listés avec **conformité** et **type de visite**.

> 📸 _[Capture 16 : Analyse PV]_

### 6.2 Indices visuels
- **Conforme / Non conforme** : couleur de la cellule.
- **Visite / Contre‑visite** : couleur différente.

> 📸 _[Capture 17 : Couleurs conformité]_

### 6.3 Actions
- **Zoomer** : focus sur un PV.
- **Désigner comme pollueur** : marque un PV.
- **Voir dans OSMOSE** : ouvre la fiche PV.
- **Exporter CSV** : export rapide.

> 📸 _[Capture 18 : Actions sur PV]_

---

## 7) Dock **Analyses** (Industriels + PV)

### 7.1 Industriels
- Table complète avec colonnes **Nom, Activité, Produits, Risques**.
- Les lignes sont **colorées** selon la colonne *Risques*.

> 📸 _[Capture 19 : Dock Industriels avec couleurs]_

### 7.2 PV non conformes
- Liste des PV issus du cheminement.

> 📸 _[Capture 20 : Dock PV non conformes]_

---

## 8) Onglet **⚙️ PARAMÈTRES**

### 8.1 Sélection des couches SIG
Renseignez les couches :
- **Canalisations**
- **Ouvrages**
- **Cours d’eau / fossés**
- **Industriels**
- **Liaisons Indus**
- **Astreintes**
- **PV Conformité**

> 📸 _[Capture 21 : Sélection des couches]_

### 8.2 Actualiser les couches
Recharge les couches disponibles dans QGIS.

> 📸 _[Capture 22 : Actualiser les couches]_

---

## 9) Bonnes pratiques

- Toujours vérifier que les couches sont **valides** dans QGIS.
- Utiliser **Cheminement Pollution** pour l’analyse industrielle complète.
- Mettre à jour régulièrement les couches (bouton “Actualiser”).
- Utiliser les couleurs de risques pour **prioriser** les visites terrain.

---

## 10) FAQ rapide

**Q : Pourquoi aucun industriel ne s’affiche ?**  
R : Vérifiez la couche **Industriels** et les champs d’ID.

**Q : Pourquoi aucun PV n’est détecté ?**  
R : Vérifiez la couche PV et la distance de recherche.

**Q : Le cheminement est lent ?**  
R : Utilisez les filtres réseau, limitez l’étendue, et vérifiez la charge des couches.

---

## 11) Suivi des captures

| Capture | Description | Statut |
|--------|-------------|--------|
| 1 | Interface principale | ☐ |
| 2 | Sélection des couches | ☐ |
| 3 | Cheminement | ☐ |
| 4 | Saisie ID ouvrage | ☐ |
| 5 | Recherche ouvrage | ☐ |
| 6 | Type de cheminement | ☐ |
| 7 | Filtres réseau | ☐ |
| 8 | Boutons Cheminer/Flux/Couleurs | ☐ |
| 9 | Visites de nœuds | ☐ |
|10 | Liste industriels | ☐ |
|11 | Notes pollution | ☐ |
|12 | Astreinte | ☐ |
|13 | Bassin collecte | ☐ |
|14 | Diagnostic | ☐ |
|15 | Rapport | ☐ |
|16 | Analyse PV | ☐ |
|17 | Couleurs conformité | ☐ |
|18 | Actions PV | ☐ |
|19 | Dock Industriels | ☐ |
|20 | Dock PV non conformes | ☐ |
|21 | Sélection couches | ☐ |
|22 | Actualiser couches | ☐ |

