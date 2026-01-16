"""
MARTINE IA - Script Principal (Estimation Tâches)
Lit Notion (base "Tâches IA"), estime via GPT ou Gemini, met à jour les temps en heures
UNIQUEMENT pour les sous-tâches (feuilles) sans estimation existante
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Forcer l'encodage UTF-8 pour Windows (pour les émojis)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def find_env_file():
    """Cherche le fichier .env en remontant l'arborescence"""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        env_path = current / ".env"
        if env_path.exists():
            return env_path
        current = current.parent
    return None


# Chargement robuste du .env
env_path = find_env_file()
if env_path:
    from dotenv import load_dotenv
    load_dotenv(env_path, override=True)
else:
    raise FileNotFoundError("❌ Fichier .env introuvable!")

# Ajouter le dossier courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from notion_client import NotionClient

# Configuration depuis variables d'environnement (.env)
NOTION_TOKEN = os.getenv("NOTION_TOKEN")

# Choix du moteur d'estimation: "gemini" ou "gpt" (défaut: gemini)
ESTIMATOR_ENGINE = os.getenv("ESTIMATOR_ENGINE", "gemini").lower()

# Mode DEBUG (ne modifie pas Notion, affiche seulement)
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# Configuration du moteur
if ESTIMATOR_ENGINE == "gemini":
    from gemini_estimator import GeminiEstimator
    GEMINI_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
    if not GEMINI_KEY:
        raise ValueError("❌ GEMINI_API_KEY manquant dans .env")
    estimator = GeminiEstimator(GEMINI_KEY, GEMINI_MODEL)
else:
    from gpt_estimator import GPTEstimator
    GPT_KEY = os.getenv("GPT_API_KEY")
    GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o")
    if not GPT_KEY:
        raise ValueError("❌ GPT_API_KEY manquant dans .env")
    estimator = GPTEstimator(GPT_KEY, GPT_MODEL)

# Database ID de la base "Tâches IA"
DB_TACHES_IA = os.getenv("DATABASE_TACHES_IA", os.getenv("DATABASE_TACHES"))

# Noms des propriétés Notion (EXACTS)
PROP_NOM = "Nom"  # Title
PROP_SOUS_ELEMENT = "Sous-élément"  # Relation pour détecter les parents
PROP_ESTIMATION_ENFANT = "🤖⏱️Temps est IA (h) ENFANT"  # Number - cible à écrire
PROP_DESCRIPTION = "Description"  # Rich text (si disponible)
PROP_TYPE = "Type"  # Select ou Multi-select

# Vérifications
if not NOTION_TOKEN:
    raise ValueError("❌ NOTION_TOKEN manquant dans le fichier .env")
if not DB_TACHES_IA:
    raise ValueError("❌ DATABASE_TACHES_IA manquant dans le fichier .env")

# Initialiser client Notion
notion = NotionClient(NOTION_TOKEN)


def is_leaf_task(page: dict) -> bool:
    """
    Vérifie si une page est une feuille (sous-tâche sans enfants).
    Une feuille a la propriété 'Sous-élément' vide (relation vide).
    """
    try:
        props = page.get("properties", {})
        sous_element_prop = props.get(PROP_SOUS_ELEMENT, {})
        prop_type = sous_element_prop.get("type")
        
        if prop_type == "relation":
            relations = sous_element_prop.get("relation", [])
            return len(relations) == 0
        
        # Si le type n'est pas "relation", on considère que c'est une feuille
        return True
    except Exception:
        # En cas d'erreur, on considère que c'est une feuille (sécurité)
        return True


def get_estimation_value(page: dict) -> float:
    """
    Récupère la valeur de l'estimation enfant.
    Retourne 0.0 si vide ou non défini.
    """
    try:
        value = notion.get_property_value(page, PROP_ESTIMATION_ENFANT)
        if value is None:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def query_notion_tasks_to_estimate() -> list:
    """
    Récupère les tâches à estimer depuis la base Notion "Tâches IA".
    Filtre : 
      - Sous-élément est vide (feuilles uniquement)
      - Estimation enfant est vide ou = 0
    
    Le filtre Notion sur relation.is_empty est utilisé, 
    puis filtrage Python pour l'estimation.
    """
    print("\n🔍 Recherche des tâches à estimer...")
    
    # Filtre Notion : Sous-élément est vide (relation.is_empty)
    # NOTE: Si le filtre ne fonctionne pas parfaitement, on fait un filtrage Python ensuite
    filter_obj = {
        "property": PROP_SOUS_ELEMENT,
        "relation": {
            "is_empty": True
        }
    }
    
    try:
        all_pages = notion.query_database(DB_TACHES_IA, filter_obj)
    except Exception as e:
        print(f"⚠️ Erreur lors du filtrage Notion, récupération de toutes les pages: {e}")
        all_pages = notion.query_database(DB_TACHES_IA)
    
    to_estimate = []
    skipped_parents = 0
    skipped_already_estimated = 0
    skipped_wrong_type = 0
    
    for page in all_pages:
        page_id = page.get("id")
        nom = notion.get_property_value(page, PROP_NOM) or "Sans nom"
        
        # Vérifier si c'est une feuille
        if not is_leaf_task(page):
            print(f"   SKIP parent: {nom}")
            skipped_parents += 1
            continue
        
        # Vérifier si déjà estimée
        estimation = get_estimation_value(page)
        if estimation > 0:
            print(f"   SKIP already estimated: {nom} ({estimation}h)")
            skipped_already_estimated += 1
            continue
        
        # Vérifier le type (doit être "Tâche")
        tache_type = notion.get_property_value(page, PROP_TYPE)
        
        # Gérer le cas où Type est une Multi-sélection (liste) ou Sélection unique (chaîne)
        is_tache = False
        if isinstance(tache_type, list):
            is_tache = "Tâche" in tache_type
        else:
            is_tache = (tache_type == "Tâche")

        if not is_tache:
            print(f"   SKIP wrong type: {nom} (Type: {tache_type})")
            skipped_wrong_type += 1
            continue
        
        # Récupérer les détails pour l'estimation
        description = notion.get_property_value(page, PROP_DESCRIPTION) or ""
        
        # Récupérer le contenu détaillé de la page
        print(f"   📄 Lecture du contenu pour : {nom}")
        try:
            content = notion.get_page_content(page_id)
        except Exception as e:
            print(f"   ⚠️ Impossible de lire le contenu: {e}")
            content = ""
        
        # Récupérer le projet si disponible
        projet = []
        try:
            projet_value = notion.get_property_value(page, "Projet/Tlt")
            if projet_value:
                projet = projet_value if isinstance(projet_value, list) else [projet_value]
        except Exception:
            pass
        
        to_estimate.append({
            "id": page_id,
            "nom": nom,
            "description": description,
            "projet": projet,
            "content": content
        })
    
    print(f"\n📊 Résumé:")
    print(f"   - Parents ignorés: {skipped_parents}")
    print(f"   - Déjà estimées: {skipped_already_estimated}")
    print(f"   - Type invalide (non 'Tâche'): {skipped_wrong_type}")
    print(f"   - À estimer: {len(to_estimate)}")
    
    return to_estimate


def update_notion_estimate(page_id: str, hours: float) -> bool:
    """
    Met à jour l'estimation d'une page dans Notion.
    Écrit dans la propriété "🤖⏱️Temps est IA (h) ENFANT" (Number).
    
    Args:
        page_id: ID de la page Notion
        hours: Temps estimé en heures décimales
    
    Returns:
        True si succès, False sinon
    """
    if DEBUG_MODE:
        print(f"   [DEBUG] Simulation: {hours}h")
        return True
    
    try:
        success = notion.update_page(page_id, {
            PROP_ESTIMATION_ENFANT: {"number": hours}
        })
        return success
    except Exception as e:
        print(f"   ❌ Erreur lors de la mise à jour: {e}")
        return False


def get_historical_tasks() -> list:
    """
    Récupère l'historique des tâches avec temps réel > 0
    pour servir de contexte à l'estimation.
    """
    print("\n📚 Chargement de l'historique...")
    
    try:
        taches = notion.query_database(DB_TACHES_IA)
    except Exception as e:
        print(f"⚠️ Erreur chargement historique: {e}")
        return []
    
    history = []
    for tache in taches:
        # Chercher un champ temps réel (si disponible)
        temps_reel = None
        for prop_name in ["⏱️ Temps réel agrégé (h)", "Temps réel (h)", "Temps réel"]:
            try:
                temps_reel = notion.get_property_value(tache, prop_name)
                if temps_reel:
                    break
            except Exception:
                continue
        
        if temps_reel and temps_reel > 0:
            history.append({
                "id": tache.get("id"),
                "nom": notion.get_property_value(tache, PROP_NOM) or "Sans nom",
                "description": notion.get_property_value(tache, PROP_DESCRIPTION) or "",
                "temps_reel": temps_reel,
                "projet": notion.get_property_value(tache, "Projet/Tlt") or [],
            })
    
    print(f"📊 {len(history)} tâches historiques chargées")
    return history


def run_estimations():
    """Lance les estimations IA et met à jour Notion"""
    engine_name = "Gemini" if ESTIMATOR_ENGINE == "gemini" else "GPT"
    print(f"\n🤖 Lancement des estimations {engine_name} (heures décimales)...")
    if DEBUG_MODE:
        print("⚠️  MODE DEBUG ACTIVÉ - Pas d'écriture dans Notion")
    
    tasks_to_estimate = query_notion_tasks_to_estimate()
    if not tasks_to_estimate:
        print("✅ Toutes les tâches sont déjà estimées ou ce sont des parents")
        return
    
    historical_tasks = get_historical_tasks()
    
    # Batch estimation
    estimates = estimator.batch_estimate(
        tasks_to_estimate=tasks_to_estimate,
        all_tasks_history=historical_tasks,
        project_name="EISF Alternance"
    )
    
    # Mettre à jour Notion
    print("\n💾 Mise à jour Notion...")
    updated = 0
    failed = 0
    
    for task in tasks_to_estimate:
        task_id = task.get("id")
        task_name = task.get("nom", "Sans nom")
        
        if task_id in estimates:
            estimated_minutes = estimates[task_id]
            
            # Conversion en heures décimales
            raw_hours = estimated_minutes / 60
            
            # Arrondi au quart d'heure le plus proche (ex: 1.15 -> 1.25, 1.05 -> 1.0)
            # On multiplie par 4, on arrondit à l'entier, puis on divise par 4
            rounded_hours = round(raw_hours * 4) / 4
            
            # Sécurité: minimum 0.25h si GPT a estimé quelque chose
            if rounded_hours == 0 and estimated_minutes > 0:
                rounded_hours = 0.25
                
            success = update_notion_estimate(task_id, rounded_hours)
            
            if success:
                print(f"   WRITE {task_name}: {rounded_hours}h ({estimated_minutes} min)")
                updated += 1
            else:
                print(f"   ❌ FAILED {task_name}")
                failed += 1
    
    print(f"\n✅ Résultat: {updated} estimations enregistrées, {failed} échecs")
    
    # Sauvegarder log (non critique - on continue même si ça échoue)
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
        # Si "logs" existe en tant que fichier, le supprimer pour créer un dossier
        if os.path.exists(log_dir) and not os.path.isdir(log_dir):
            os.remove(log_dir)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_path = os.path.join(log_dir, f"estimations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "database_id": DB_TACHES_IA,
            "estimates": {
                task_id: {
                    "task_name": next((t["nom"] for t in tasks_to_estimate if t["id"] == task_id), "Unknown"),
                    "estimated_minutes": estimates[task_id],
                    "written_hours": round((estimates[task_id] / 60) * 4) / 4 if estimates[task_id] / 60 >= 0.125 else 0.25
                }
                for task_id in estimates
            },
            "summary": {
                "total_estimated": len(estimates),
                "successfully_written": updated,
                "failed": failed
            }
        }
        
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        print(f"📝 Log sauvegardé: {log_path}")
    except Exception as e:
        print(f"⚠️ Log non sauvegardé (non critique): {e}")


def main():
    """Fonction principale"""
    engine_name = "Gemini" if ESTIMATOR_ENGINE == "gemini" else "GPT"
    print("=" * 60)
    print("🧠 MARTINE IA - Estimation automatique des temps (Tâches)")
    print(f"   Base: Tâches IA")
    print(f"   Moteur: {engine_name}")
    print("   Mode: Heures décimales (arrondi au quart d'heure)")
    print("   Cible: Feuilles uniquement (pas de parents)")
    if DEBUG_MODE:
        print("   ⚠️  MODE DEBUG ACTIVÉ (pas d'écriture)")
    print("=" * 60)
    
    try:
        # Estimer via IA et mettre à jour Notion
        run_estimations()
        
        print("\n" + "=" * 60)
        print("✅ TRAITEMENT TERMINÉ")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()