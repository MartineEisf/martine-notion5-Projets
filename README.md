# 🧠 Martine IA - Estimation Automatique des Temps

Assistant intelligent pour l'estimation automatique des temps de tâches dans Notion via GPT.

## ✨ Fonctionnalités

- **Estimation automatique** : Utilise GPT pour estimer le temps nécessaire pour chaque tâche
- **Ré-estimation intelligente** : Détecte automatiquement les changements de contenu et ré-estime
- **Intégration Notion** : Lit et écrit directement dans vos bases Notion
- **Historique** : Apprend de vos tâches passées pour des estimations plus précises
- **Logs détaillés** : Sauvegarde toutes les estimations en JSON

## 🚀 Installation Rapide

### Prérequis

- Python 3.8+
- Un compte Notion avec une intégration API
- Une clé API OpenAI (GPT)

### Étapes

1. **Cloner le repository**
```bash
git clone <votre-repo>
cd martine-notion3
```

2. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

3. **Configurer les variables d'environnement**

Créez un fichier `.env` à la racine :
```env
# Notion API
NOTION_TOKEN=votre_token_notion
DATABASE_TACHES=id_de_votre_base_taches

# GPT API
GPT_API_KEY=votre_cle_openai
GPT_MODEL=gpt-4o
```

4. **Lancer le script**
```bash
python src/main.py
```

## 📖 Documentation Complète

Consultez le [Guide Utilisateur](GUIDE_UTILISATEUR.md) pour :
- Configuration détaillée de Notion
- Utilisation avancée
- Automatisation quotidienne
- Résolution de problèmes

## 🔧 Configuration Notion

Le script crée automatiquement les colonnes suivantes dans votre base Tâches :

- `⏱️ Temps estimé IA (min)` : Estimation en minutes
- `⏱️ Temps réel agrégé (min)` : Temps réel passé
- `📊 Écart (%)` : Différence entre estimé et réel
- `🔄 Hash contenu` : Empreinte pour détecter les changements

## 🎯 Utilisation

### Estimation de nouvelles tâches

Le script estime automatiquement toutes les tâches sans estimation :

```bash
python src/main.py
```

### Ré-estimation automatique

Modifiez simplement le contenu d'une tâche dans Notion. Au prochain lancement, le script détectera le changement et ré-estimera automatiquement.

### Forcer une ré-estimation

Effacez la valeur de `⏱️ Temps estimé IA (min)` dans Notion pour la tâche concernée.

## 📁 Structure du Projet

```
martine-notion3/
├── src/
│   ├── main.py              # Script principal
│   ├── notion_client.py     # Client API Notion
│   └── gpt_estimator.py     # Estimateur GPT
├── logs/                    # Logs des estimations
├── .env                     # Variables d'environnement (non versionné)
├── .gitignore              # Fichiers à ignorer
├── requirements.txt        # Dépendances Python
└── README.md              # Ce fichier
```

## 🔒 Sécurité

- Le fichier `.env` est automatiquement ignoré par Git
- Ne partagez jamais vos tokens Notion ou clés API
- Les logs ne contiennent pas d'informations sensibles

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## 📝 Licence

Ce projet est sous licence MIT.

## 🆘 Support

Pour toute question ou problème, consultez le [Guide Utilisateur](GUIDE_UTILISATEUR.md) ou ouvrez une issue.
