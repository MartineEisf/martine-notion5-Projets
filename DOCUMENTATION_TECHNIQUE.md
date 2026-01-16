# 🧠 MARTINE IA - Documentation Technique Permanente

## 1. Architecture et Orchestration

L'outil est scindé en deux moteurs principaux :

### A. Moteur de Projets (`src/estimate_projects.py`)
- **Unité** : Semaines.
- **Logique "Senior PM"** : Utilise GPT-4o pour estimer la durée globale d'un projet en fonction :
    - Du descriptif et des notes de page.
    - Du résumé des tâches liées (les 10 premières).
    - Du contexte global (Ordre, Statut, Priorité).
    - De l'historique des projets passés similaires.
- **Filtres Métier** :
    - **Quick Win** : Plafonne la réponse IA.
    - **Au long court** : Identifié via la colonne `Ordre`, force la mise à 0 de `ACTU`.

### B. Moteur de Tâches (`src/main.py`)
- **Unité** : Heures (décimales, arrondi au 1/4 d'heure).
- **Cible** : Uniquement les "feuilles" (tâches sans sous-éléments) de type "Tâche".
- **Contextualisation** : Récupère le contenu complet de la page pour une précision maximale.

---

## 2. Détection Intelligente des Changements

Martine IA implémente un système de **Hashage SHA-256** pour l'auto-ré-estimation.

### Processus :
1. **Concaténation** des données : `Nom + Description + Contenu Page + Résumé Tâches + Contexte`.
2. **Calcul** du hash SHA-256.
3. **Comparaison** avec le champ `🤖⏱️Hash Source IA` dans Notion.
4. **Trigger** : Si Hash différent $\rightarrow$ Envoi à l'IA $\rightarrow$ Mise à jour de `ACTU` + Nouveau Hash.

> [!TIP]
> Pour forcer une ré-estimation sans rien changer, videz simplement la colonne `ACTU` ou le champ `Hash` dans Notion.

---

## 3. Configuration Notion (Base Projets)

| Propriété | Usage Technique |
| :--- | :--- |
| `🤖⏱️I Durée est IA INIT (sem)` | Valeur de référence (écrite 1 seule fois). |
| `🤖⏱️A Durée est IA ACTU (sem)` | Valeur vivante, mise à jour par l'IA au moindre changement. |
| `🤖⏱️Hash Source IA` | Stockage de l'empreinte pour la détection de modifications. |
| `Ordre` | Utilisé pour détecter les "Quick Win" et "Au long court". |
| `Tâches IA` | Relation utilisée pour extraire le résumé des tâches. |

---

## 4. Multi-modèles (GPT / Gemini)

Le système est agnostique du modèle d'IA :
- **GPT-4o** : Utilisé par défaut pour les projets pour sa vision "Senior PM".
- **Gemini** : Configurable dans le `.env` pour les tâches massives.

---

*Dernière mise à jour technique : 16/01/2026*
