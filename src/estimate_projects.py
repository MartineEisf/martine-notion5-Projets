"""
MARTINE IA - Estimation des Projets (Macro)
Estime la durée globale des projets en semaines via Gemini/GPT
Mode "Senior PM": évalue la charge globale, pas la somme des tâches
"""
import os
import sys
import json
import time
import hashlib
from datetime import datetime
from pathlib import Path

# Forcer l'encodage UTF-8 pour Windows
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

# Ajouter src/ au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from notion_client import NotionClient
from gpt_estimator import GPTEstimator

# Configuration depuis .env
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
GPT_API_KEY = os.getenv("GPT_API_KEY")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o")

# Database IDs
DB_PROJETS_IA = os.getenv("DATABASE_PROJETS_IA", os.getenv("DATABASE_PROJETS"))
DB_TACHES_IA = os.getenv("DATABASE_TACHES_IA", os.getenv("DATABASE_TACHES"))

# Propriétés Notion
PROP_NOM = "Projet"
PROP_DESCRIPTION = "Description"
PROP_DUREE_INIT = "🤖⏱️I Durée est IA INIT (sem)"  # Corrigé 'I'
PROP_DUREE_ACTU = "🤖⏱️A Durée est IA ACTU (sem)"  # Corrigé 'A'
PROP_TACHES = "Tâches IA"  # Corrigé 'IA'
PROP_HASH = "🤖⏱️Hash Source IA"  # Nouvelle propriété pour détection de changements

# Mode DEBUG (ne modifie pas Notion)
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# Valeurs autorisées pour la durée en semaines
VALID_DURATIONS = [0.5, 1, 1.5, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24]

# Vérifications
if not NOTION_TOKEN:
    raise ValueError("❌ NOTION_TOKEN manquant dans .env")
if not GPT_API_KEY:
    raise ValueError("❌ GPT_API_KEY manquant dans .env")
if not DB_PROJETS_IA:
    raise ValueError("❌ DATABASE_PROJETS_IA manquant dans .env")

# Initialiser clients
notion = NotionClient(NOTION_TOKEN)
# gemini = GeminiEstimator(GEMINI_KEY, GEMINI_MODEL) # Removed

def get_property_value(page: dict, prop_name: str):
    """Récupère la valeur d'une propriété (wrapper pour gestion d'erreurs)"""
    try:
        return notion.get_property_value(page, prop_name)
    except Exception:
        return None


def calculate_project_hash(project_data: dict) -> str:
    """Calcule un hash SHA-256 des données sources du projet"""
    # On concatène les infos structurantes
    input_str = (
        f"{project_data.get('nom', '')}|"
        f"{project_data.get('description', '')}|"
        f"{project_data.get('content', '')}|"
        f"{project_data.get('tasks_summary', '')}|"
        f"{project_data.get('full_context', '')}"
    )
    return hashlib.sha256(input_str.encode('utf-8')).hexdigest()


def get_projects_to_estimate() -> list:
    """
    Récupère les projets à estimer depuis Notion.
    Filtre: DUREE_INIT vide ou 0
    """
    print("\n🔍 Recherche des projets à estimer...")
    
    try:
        all_projects = notion.query_database(DB_PROJETS_IA)
    except Exception as e:
        print(f"❌ Erreur lecture base Projets: {e}")
        return []
    
    to_estimate = []
    skipped_already = 0
    
    for project in all_projects:
        page_id = project.get("id")
        nom = get_property_value(project, PROP_NOM) or "Sans nom"
        
        # Filtre "Au long court"
        ordre = get_property_value(project, "Ordre")
        if ordre and "Au long court" in str(ordre):
            # On veut VIDER l'estimation si c'est au long court
            duree_actu = get_property_value(project, PROP_DUREE_ACTU)
            if duree_actu: # Si pas déjà vide
                print(f"   🗑️  MARQUÉ POUR RESET (Au long court): {nom}")
                to_estimate.append({
                    "id": page_id,
                    "nom": nom,
                    "action": "CLEAR"
                })
            else:
                print(f"   SKIP (Au long court déjà vide): {nom}")
                skipped_already += 1
            continue

        # Récupérer les infos du projet
        description = get_property_value(project, PROP_DESCRIPTION) or ""
        
        # Récupérer TOUTES les propriétés pour le contexte (Ordre, Statut, etc.)
        properties_context = []
        for prop_name, prop_data in project.get("properties", {}).items():
            if prop_name in [PROP_NOM, PROP_DESCRIPTION, PROP_DUREE_INIT, PROP_DUREE_ACTU, PROP_TACHES]:
                continue
            try:
                val = get_property_value(project, prop_name)
                if val:
                    properties_context.append(f"{prop_name}: {val}")
            except:
                pass
        
        full_context = "\n".join(properties_context)
        print(f"   📄 Lecture du contenu: {nom}")
        try:
            content = notion.get_page_content(page_id)
        except Exception as e:
            print(f"   ⚠️ Impossible de lire le contenu: {e}")
            content = ""
        
        taches_ids = get_property_value(project, PROP_TACHES) or []
        tasks_summary = get_tasks_summary(taches_ids)

        # --- LOGIQUE DE DÉTECTION DE CHANGEMENT (HASH) ---
        current_data = {
            "nom": nom,
            "description": description,
            "content": content,
            "tasks_summary": tasks_summary,
            "full_context": full_context
        }
        current_hash = calculate_project_hash(current_data)
        stored_hash = get_property_value(project, PROP_HASH)
        
        duree_init = get_property_value(project, PROP_DUREE_INIT)
        duree_actu = get_property_value(project, PROP_DUREE_ACTU)
        
        should_reestimate = False
        is_initial = False
        reason = ""
        
        if not duree_init or duree_init <= 0:
            should_reestimate = True
            is_initial = True
            reason = "Première estimation"
        elif current_hash != stored_hash:
            print(f"   ✨ CHANGEMENT DÉTECTÉ pour: {nom}")
            should_reestimate = True
            is_initial = False
            reason = "Mise à jour des infos"
        elif not duree_actu or duree_actu <= 0:
            print(f"   🔄 Ré-estimation IA demandée (ACTU vide) pour: {nom}")
            should_reestimate = True
            is_initial = False
            reason = "Forçage manuel (ACTU vide)"
        
        if not should_reestimate:
            print(f"   SKIP déjà à jour: {nom}")
            skipped_already += 1
            continue
        
        to_estimate.append({
            "id": page_id,
            "nom": nom,
            "description": description,
            "content": content,
            "tasks_summary": tasks_summary,
            "full_context": full_context,
            "action": "ESTIMATE",
            "is_initial": is_initial,
            "new_hash": current_hash,
            "reason": reason
        })
    
    print(f"\n📊 Résumé:")
    print(f"   - Déjà à jour: {skipped_already}")
    print(f"   - Actions prévues: {len(to_estimate)}")
    
    return to_estimate


def get_tasks_summary(task_ids: list) -> str:
    """Génère un résumé des tâches liées à un projet"""
    if not task_ids:
        return "Aucune tâche liée."
    
    summaries = []
    for task_id in task_ids[:10]:  # Limiter à 10 tâches
        try:
            # Récupérer la page de la tâche
            import requests
            headers = {
                "Authorization": f"Bearer {NOTION_TOKEN}",
                "Notion-Version": "2022-06-28"
            }
            r = requests.get(f"https://api.notion.com/v1/pages/{task_id}", headers=headers)
            if r.status_code == 200:
                page = r.json()
                nom = get_property_value(page, "Nom") or "Tâche"
                estimation = get_property_value(page, "🤖⏱️Temps est IA (h) ENFANT")
                if estimation:
                    summaries.append(f"- {nom}: ~{estimation}h estimé")
                else:
                    summaries.append(f"- {nom}: non estimé")
        except Exception:
            continue
    
    if not summaries:
        return f"{len(task_ids)} tâches liées (détails non disponibles)"
    
    return "\n".join(summaries)


def get_historical_projects() -> list:
    """Récupère l'historique des projets avec durée réelle > 0"""
    print("\n📚 Chargement de l'historique des projets...")
    
    try:
        projects = notion.query_database(DB_PROJETS_IA)
    except Exception as e:
        print(f"⚠️ Erreur chargement historique: {e}")
        return []
    
    history = []
    for project in projects:
        # Chercher un champ durée réelle
        duree_reelle = None
        for prop_name in ["Durée réelle (sem)", "⏱️ Durée réelle", "Durée"]:
            try:
                duree_reelle = get_property_value(project, prop_name)
                if duree_reelle:
                    break
            except Exception:
                continue
        
        # Si pas de durée réelle, chercher IA ACTU
        if not duree_reelle or duree_reelle <= 0:
            try:
                duree_actu = get_property_value(project, PROP_DUREE_ACTU)
                if duree_actu and duree_actu > 0:
                    duree_reelle = duree_actu  # On utilise l'actu comme référence faute de mieux
            except Exception:
                pass

        if duree_reelle and duree_reelle > 0:
            history.append({
                "id": project.get("id"),
                "nom": get_property_value(project, PROP_NOM) or "Sans nom",
                "description": get_property_value(project, PROP_DESCRIPTION) or "",
                "duree_reelle": duree_reelle
            })
    
    print(f"📊 {len(history)} projets historiques chargés")
    return history


def update_project_estimate(page_id: str, weeks: float, is_initial: bool = False, new_hash: str = None) -> bool:
    """
    Met à jour l'estimation et le hash d'un projet dans Notion.
    """
    if DEBUG_MODE:
        print(f"   [DEBUG] Simulation écriture: {weeks} semaines (hash: {new_hash[:8] if new_hash else 'N/A'})")
        return True
    
    try:
        properties = {
            PROP_DUREE_ACTU: {"number": weeks}
        }
        
        if is_initial:
            properties[PROP_DUREE_INIT] = {"number": weeks}
            
        if new_hash:
            properties[PROP_HASH] = {"rich_text": [{"text": {"content": new_hash}}]}
        
        success = notion.update_page(page_id, properties)
        return success
    except Exception as e:
        print(f"   ❌ Erreur mise à jour: {e}")
        return False


def run_estimations():
    """Lance les estimations GPT et met à jour Notion"""
    
    # --- PRÉ-REQUIS : Vérifier l'existence de la colonne HASH ---
    print("🔍 Vérification du schéma Notion...")
    try:
        schema = notion.get_database_schema(DB_PROJETS_IA)
        if PROP_HASH not in schema:
            print(f"   🏗️  Création de la colonne '{PROP_HASH}'...")
            notion.add_property_to_database(DB_PROJETS_IA, PROP_HASH, {"rich_text": {}})
    except Exception as e:
        print(f"   ⚠️ Impossible de vérifier le schéma: {e}")

    # Init GPT
    api_key = os.getenv("GPT_API_KEY")
    model = os.getenv("GPT_MODEL", "gpt-4o")
    
    if not api_key:
        print("❌ GPT_API_KEY manquant!")
        return

    estimator = GPTEstimator(api_key, model)
    print(f"\n🤖 Lancement des estimations (mode Senior PM)...")
    print(f"   Moteur: GPT ({model})")
    
    projects = get_projects_to_estimate()
    if not projects:
        print("✅ Tous les projets sont déjà estimés")
        return
    
    historical = get_historical_projects()
    
    # Estimation
    print("\n🧠 Estimation via GPT...")
    updated = 0
    failed = 0
    
    for i, project in enumerate(projects, 1):
        print(f"\n📦 Projet {i}/{len(projects)}: {project['nom']}")
        if project.get("reason"):
            print(f"   Motif: {project['reason']}")
        
        action = project.get("action", "ESTIMATE")
        
        if action == "CLEAR":
            print(f"   🗑️  Suppression des estimations (Au long court)")
            # On met à None pour vider dans Notion
            success = update_project_estimate(project["id"], None, is_initial=False)
            if success:
                updated += 1
            else:
                failed += 1
            continue

        if action == "UPDATE_ACTU_ONLY":
            print(f"   🔄 Synchro ACTU avec INIT ({project['value']} sem)")
            success = update_project_estimate(project["id"], project["value"], is_initial=False)
            if success:
                updated += 1
            else:
                failed += 1
            continue

        # Sinon ESTIMATE
        estimated_weeks = estimator.estimate_project_duration(
            project_name=project["nom"],
            project_description=project["description"] + "\n\nCONTEXTE: " + (project.get("full_context") or ""),
            project_content=project.get("content") or "",
            tasks_summary=project.get("tasks_summary") or "",
            historical_projects=historical
        )
        
        if estimated_weeks is not None:
            print(f"   ✅ Estimation: {estimated_weeks} semaines")
            
            success = update_project_estimate(
                project["id"], 
                estimated_weeks, 
                is_initial=project.get("is_initial", False),
                new_hash=project.get("new_hash")
            )
            
            if success:
                mode_str = "INIT + ACTU" if project.get("is_initial") else "ACTU uniquement"
                print(f"   💾 Écrit dans Notion ({mode_str})")
                updated += 1
            else:
                print(f"   ❌ Échec écriture")
                failed += 1
        else:
            print(f"   ⚠️ Échec estimation")
            failed += 1
    
    print(f"\n✅ Résultat: {updated} projets estimés, {failed} échecs")
    
    # Log
    try:
        log_dir = Path(__file__).resolve().parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_path = log_dir / f"projets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "mode": "DEBUG" if DEBUG_MODE else "PRODUCTION",
            "database_id": DB_PROJETS_IA,
            "summary": {
                "total": len(projects),
                "updated": updated,
                "failed": failed
            }
        }
        
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        print(f"📝 Log sauvegardé: {log_path}")
    except Exception as e:
        print(f"⚠️ Log non sauvegardé: {e}")


def main():
    """Fonction principale"""
    print("=" * 60)
    print("🧠 MARTINE IA - Estimation des Projets (Senior PM)")
    print("   Base: Projets IA")
    print("   Mode: Durée en semaines (0.5 à 12)")
    print("   Moteur: Gemini")
    if DEBUG_MODE:
        print("   ⚠️  MODE DEBUG ACTIVÉ (pas d'écriture)")
    print("=" * 60)
    
    try:
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