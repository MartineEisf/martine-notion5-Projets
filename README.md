# 🧠 Martine IA - Estimation Automatique Projets & Tâches

Assistant intelligent pour l'estimation automatique des durées dans Notion (Projets en semaines, Tâches en heures) via GPT/Gemini.

## ✨ Fonctionnalités Clés

- **Estimation Multi-niveaux** :
  - **Projets** : Estimation globale de la charge en semaines (`src/estimate_projects.py`).
  - **Tâches** : Estimation détaillée en heures décimales (`src/main.py`).
- **Auto-Ré-estimation IA (Intelligente)** :
  - Utilise un système de **Hashage SHA-256** pour détecter tout changement de contenu (Nom, Description, Tâches liées, Notes).
  - Ré-estime automatiquement si les informations sources évoluent.
- **Règles Métier Intégrées** :
  - **Quick Win** : Plafonnement automatique pour les projets à gain rapide.
  - **Au long court** : Exclusion et remise à zéro automatique des estimations.
  - **Double Sync** : Mise à jour simultanée des champs `INIT` (valeur de référence) et `ACTU` (valeur actuelle).
- **Multi-Modèles** : Support natif d'OpenAI (GPT-4o) et Google (Gemini).
- **Raccourci Bureau** : Lancement d'un clic via le raccourci Windows.

## 🚀 Installation & Utilisation

### Prérequis
- Python 3.8+
- Intégration Notion configurée
- Clés API OpenAI ou Google Gemini

### Configuration
Créez un fichier `.env` à la racine :
```env
# Notion
NOTION_TOKEN=ntn_...
DATABASE_PROJETS_IA=id_base_projets
DATABASE_TACHES_IA=id_base_taches

# IA
GPT_API_KEY=sk-...
GEMINI_API_KEY=...
```

### Lancement
- **Via le Bureau** : Double-cliquez sur "Martine IA - Estimation Projets".
- **Via la console** :
  ```bash
  python src/estimate_projects.py   # Pour les projets
  python src/main.py               # Pour les tâches
  ```

## 🔧 Fonctionnement du Hashage
Pour éviter les appels API inutiles, Martine stocke une "empreinte" (`🤖⏱️Hash Source IA`) des données du projet.
1. Vous modifiez une info dans Notion.
2. Martine calcule un nouveau hash.
3. Si le hash $\neq$ stocké $\rightarrow$ **Ré-estimation auto**.
4. Pour forcer manuellement : vider le champ `ACTU` dans Notion.

## 📁 Structure
- `src/` : Code source (Notion, GPTEstimator, GeminiEstimator).
- `logs/` : Historique des estimations JSON.
- `RUN_ESTIMATION.bat` : Script de lancement Windows.

---
*Documentation mise à jour le 16/01/2026*
