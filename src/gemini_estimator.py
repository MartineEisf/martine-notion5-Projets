import requests
import json
import re
import time
from typing import Dict, List, Optional


class GeminiEstimator:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        self.api_key = api_key
        self.model = model
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def _call_api(self, payload: Dict) -> Optional[Dict]:
        """Appelle l'API avec retry automatique sur 429"""
        max_retries = 3
        wait_time = 10  # Départ à 10s
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}?key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.json()
                
                if response.status_code == 429:
                    print(f"    ⚠️ Rate Limit (429). Pause {wait_time}s...")
                    time.sleep(wait_time)
                    wait_time *= 2  # Exponential backoff
                    continue
                
                print(f"❌ Erreur Gemini API ({response.status_code}): {response.text}")
                return None
                
            except Exception as e:
                print(f"❌ Exception appel API: {e}")
                time.sleep(5)
        
        print("❌ Abandon après plusieurs tentatives.")
        return None

    def estimate_task_time(
        self, 
        task_name: str,
        task_description: str,
        project_context: str,
        historical_tasks: List[Dict],
        task_content: str = ""
    ) -> Optional[float]:
        """
        Estime le temps nécessaire pour une tâche
        Returns: temps en minutes (float) ou None si erreur
        """
        
        history_str = self._format_history(historical_tasks)
        
        prompt = f"""CONTEXTE DU PROJET:
{project_context}

HISTORIQUE DES TÂCHES SIMILAIRES:
{history_str}

TÂCHE À ESTIMER:
Nom: {task_name}
Description: {task_description}

CONTENU DÉTAILLÉ DE LA TÂCHE (Page Notion):
{task_content if task_content else "Aucun contenu détaillé disponible."}

INSTRUCTIONS:
1. Analyse l'historique des tâches similaires (notées en heures 'h')
2. Prends en compte la complexité décrite dans la description ET le contenu détaillé
3. Estime le temps nécessaire de manière RÉALISTE (les humains sous-estiment souvent)
4. Réponds UNIQUEMENT avec un nombre entier de minutes (ex: si tu penses 2h, écris 120)
5. Ne réponds QUE le nombre, rien d'autre. Pas de texte avant ni après.

ESTIMATION EN MINUTES (entier uniquement) :"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 50
            }
        }
            
        result = self._call_api(payload)
        if not result:
            return None
            
        try:
            text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            match = re.search(r'\d+', text)
            if match:
                return float(match.group())
            return None
        except Exception:
            return None

    
    def estimate_project_duration(
        self,
        project_name: str,
        project_description: str,
        project_content: str,
        tasks_summary: str,
        historical_projects: List[Dict]
    ) -> Optional[float]:
        """
        Estime la durée globale d'un projet en semaines.
        Approche "Senior PM": évalue la charge globale, pas la somme des tâches.
        Returns: durée en semaines (0.5, 1, 1.5, 2, 3, 4, 6, 8, 12) ou None
        """
        
        history_str = self._format_project_history(historical_projects)
        
        prompt = f"""Tu es un SENIOR PROJECT MANAGER avec 15 ans d'expérience.
Tu dois estimer la durée GLOBALE d'un projet, PAS la somme des tâches.

RÈGLES IMPORTANTES:
- Inclus les temps incompressibles: validations client, déploiement, itérations, imprévus
- Les projets prennent TOUJOURS plus de temps que la somme des tâches
- Sois réaliste et prudent (mieux vaut surestimer que sous-estimer)

HISTORIQUE DE PROJETS SIMILAIRES:
{history_str}

PROJET À ESTIMER:
Nom: {project_name}
Description: {project_description}

CONTENU DE LA PAGE PROJET (notes de cadrage, contraintes):
{project_content if project_content else "Pas de notes de cadrage."}

APERÇU DES TÂCHES DU PROJET:
{tasks_summary if tasks_summary else "Aucune tâche listée."}

VALEURS POSSIBLES: 0.5, 1, 1.5, 2, 3, 4, 6, 8, 12 (semaines)

Réponds UNIQUEMENT avec un seul nombre parmi ces valeurs.
Pas de texte, pas d'explication, juste le chiffre.

DURÉE ESTIMÉE EN SEMAINES:"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 20
            }
        }
            
        result = self._call_api(payload)
        if not result:
            return None
            
        try:
            text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                weeks = float(match.group(1))
                valid_values = [0.5, 1, 1.5, 2, 3, 4, 6, 8, 12]
                return min(valid_values, key=lambda x: abs(x - weeks))
            return None
        except Exception:
            return None
    
    def _format_history(self, tasks: List[Dict]) -> str:
        """Formate l'historique des tâches pour le prompt"""
        if not tasks:
            return "Aucune tâche similaire trouvée dans l'historique."
        
        lines = []
        for task in tasks[:10]:
            nom = task.get("nom", "Sans nom")
            temps = task.get("temps_reel", 0)
            desc = task.get("description", "")[:100]
            lines.append(f"- {nom}: {temps}h ('{desc}')")
        
        return "\n".join(lines)
    
    def _format_project_history(self, projects: List[Dict]) -> str:
        """Formate l'historique des projets pour le prompt"""
        if not projects:
            return "Aucun projet similaire dans l'historique."
        
        lines = []
        for proj in projects[:5]:
            nom = proj.get("nom", "Sans nom")
            duree = proj.get("duree_reelle", "?")
            desc = proj.get("description", "")[:80]
            lines.append(f"- {nom}: {duree} semaines ('{desc}')")
        
        return "\n".join(lines)
    
    def batch_estimate(
        self,
        tasks_to_estimate: List[Dict],
        all_tasks_history: List[Dict],
        project_name: str = "Projet EISF"
    ) -> Dict[str, float]:
        """
        Estime plusieurs tâches en batch
        Returns: Dict[task_id -> estimated_minutes]
        """
        estimates = {}
        
        for i, task in enumerate(tasks_to_estimate, 1):
            task_id = task.get("id")
            task_name = task.get("nom", "Tâche sans nom")
            task_desc = task.get("description", "")
            task_content = task.get("content", "")
            
            print(f"🤖 Estimation {i}/{len(tasks_to_estimate)}: {task_name}")
            
            similar_tasks = [
                t for t in all_tasks_history
                if t.get("projet") == task.get("projet") and t.get("temps_reel", 0) > 0
            ]
            
            estimated_time = self.estimate_task_time(
                task_name=task_name,
                task_description=task_desc,
                project_context=f"Projet: {project_name}",
                historical_tasks=similar_tasks,
                task_content=task_content
            )
            
            if estimated_time:
                estimates[task_id] = estimated_time
                print(f"  ✅ {estimated_time} min estimées")
            else:
                print(f"  ⚠️ Échec estimation")
        
        return estimates
