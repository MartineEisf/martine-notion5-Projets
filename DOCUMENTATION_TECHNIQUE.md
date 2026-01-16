# 🧠 MARTINE IA - Documentation Technique Permanente

Ce document décrit l'architecture, le fonctionnement et la configuration de l'outil **Martine IA**. Il sert de référence technique pour la maintenance et les évolutions futures.

---

## 1. Architecture du Système

L'outil est conçu comme une application Python modulaire qui automatise la gestion du temps dans Notion via l'intelligence artificielle d'OpenAI.

### 📁 Structure des fichiers
- **`.env`** : Variables de configuration (Tokens, IDs de base de données).
- **`src/main.py`** : Script principal (Logique métier et orchestration).
- **`src/notion_client.py`** : Interface avec l'API Notion (Lecture/Écriture).
- **`src/gpt_estimator.py`** : Moteur d'IA (Génération des estimations).
- **`logs/`** : Historique des estimations générées au format JSON.

---

## 2. Fonctionnement Détaillé

### Cycle d'exécution
Le script suit un processus rigoureux pour garantir la fiabilité des données :

1.  **Extraction** : Scan de la base Notion synchronisée.
2.  **Filtrage strict** :
    *   **Type** : Uniquement les éléments dont la colonne `Type` contient "Tâche".
    *   **Feuilles uniquement** : Exclusion des tâches parents (celles ayant des "Sous-éléments") pour éviter les doublons.
    *   **Vierge** : Seuls les éléments sans estimation existante (ou à 0) sont traités.
3.  **Contextualisation** : Pour chaque tâche éligible, le script récupère :
    *   Le titre et la description.
    *   Le contenu complet de la page Notion (texte, listes, etc.).
    *   L'historique des 10 dernières tâches similaires (même projet) ayant un temps réel renseigné.
4.  **Estimation IA** : Envoi du contexte à GPT-4o.
5.  **Injection** : Écriture de la valeur dans la colonne Notion cible.

---

## 3. Configuration de la Base Notion

L'outil s'appuie sur une structure de base de données spécifique nommée **"Tâches IA"**.

### Propriétés Requises (Colonnes) :
| Nom de colonne | Type | Usage |
| :--- | :--- | :--- |
| `Nom` | Titre | Nom de la tâche utilisé par l'IA. |
| `Type` | Select | Filtre (doit être "Tâche"). |
| `Sous-élément` | Relation | Permet d'identifier si c'est une sous-tâche (feuille). |
| `🤖⏱️Temps est IA (h) ENFANT` | Nombre | Cible où l'IA écrit son estimation (en heures décimales). |
| `Description` | Texte | Contexte supplémentaire pour l'IA. |
| `Projet/Tlt` | Relation | Utilisé pour regrouper les tâches par contexte projet. |

---

## 4. Logique de l'IA (Le "Cerveau")

L'estimation ne repose pas sur une simple hypothèse, mais sur une analyse comparative :

### Le Raisonnement :
- **Analyse du contenu** : L'IA ne se contente pas du titre ; elle "lit" les étapes détaillées listées dans la page Notion pour évaluer la complexité réelle.
- **Récalibrage par l'historique** : En voyant que "Créer une maquette" a pris 4h par le passé, elle ajustera son estimation pour une tâche similaire au lieu de donner une valeur générique.
- **Formatage** : L'IA est instruite pour fournir un nombre entier de minutes, que le script convertit ensuite en heures décimales (arrondi au quart d'heure) pour Notion.

---

## 5. Maintenance et Dépannage

### Ajouter une nouvelle colonne
Si vous changez le nom d'une colonne dans Notion, vous devez mettre à jour les constantes au début de `src/main.py` (variables `PROP_...`).

### Erreurs fréquentes
- **SyntaxError (HEAD/====)** : Indique un conflit de fusion Git non résolu. Nettoyer le fichier `main.py` pour supprimer ces marqueurs.
- **401 Unauthorized** : Le `NOTION_TOKEN` dans le `.env` est expiré ou le script n'a plus accès à la page Notion (vérifier l'accès à l'intégration).
- **Estimations à zéro** : Vérifier que le `Type` est bien "Tâche" et que l'élément n'est pas un parent.

---

*Document mis à jour le : 09/01/2026*
