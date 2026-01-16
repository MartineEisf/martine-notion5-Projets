"""
Script de configuration : Création de la base PHASES
"""
import os
import sys
from dotenv import load_dotenv

# Charger .env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path, override=True)

# Import client
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notion_client import NotionClient

def create_phases_db():
    print("🚀 Initialisation de la base PHASES...")
    
    token = os.getenv("NOTION_TOKEN")
    client = NotionClient(token)
    
    # 1. Utiliser le parent fourni par l'utilisateur
    # Page: https://www.notion.so/T-ches-29a59135c8828066bc93f8c250a67e95
    parent_page_id = "29a59135-c882-8066-bc93-f8c250a67e95"
    db_taches_id = os.getenv("DATABASE_TACHES")
    print(f"✅ Parent défini (page Tâches) : {parent_page_id}")
    
    # 2. Définir le schéma
    properties = {
        "Nom": {"title": {}},
        "Statut": {
            "select": {
                "options": [
                    {"name": "À faire", "color": "gray"},
                    {"name": "En cours", "color": "blue"},
                    {"name": "Terminé", "color": "green"}
                ]
            }
        },
        "Budget temps (h)": {"number": {"format": "number"}},
        # Relation vers Tâches
        "Tâches": {
            "relation": {
                "database_id": db_taches_id,
                "type": "dual_property",
                "dual_property": {} # Crée une relation bidirectionnelle
            }
        }
    }
    
    # Ajouter Projet si DB Projets existe
    db_projets_id = os.getenv("DATABASE_PROJETS")
    if db_projets_id:
        print(f"🔗 Liaison avec la DB Projets ({db_projets_id})...")
        properties["Projet"] = {
            "relation": {
                "database_id": db_projets_id,
                "type": "dual_property",
                "dual_property": {}
            }
        }
    else:
        print("ℹ️ Pas de DATABASE_PROJETS, création d'un Select 'Projet' simple.")
        properties["Projet"] = {"select": {}}

    # 3. Créer la DB
    print("🛠️ Création de la database 'Phases'...")
    new_db_id = client.create_database(parent_page_id, "Phases [Martine IA]", properties)
    
    if new_db_id:
        print("\n✨ SUCCÈS ! Base Phases créée.")
        print(f"🆔 ID: {new_db_id}")
        print("👉 Ajoute cet ID dans ton fichier .env :")
        print(f"DATABASE_PHASES={new_db_id}")

if __name__ == "__main__":
    create_phases_db()
