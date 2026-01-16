"""
Estimateur de temps via GPT (OpenAI)
Utilise l'historique + description pour prédire les durées
"""
import requests
import json
import re
from typing import Dict, List, Optional

class GPTEstimator:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"
    
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
        
        # Construire le contexte historique
        history_str = self._format_history(historical_tasks)
        
        # Prompt pour GPT
        system_prompt = "Tu es un assistant de gestion de projet expert en estimation de temps."
        user_prompt = f"""CONTEXTE DU PROJET:
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

        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 50
                },
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ Erreur GPT API ({response.status_code}): {response.text}")
                return None
            
            result = response.json()
            text = result["choices"][0]["message"]["content"].strip()
            
            # Extraire le nombre
            match = re.search(r'\d+', text)
            if match:
                minutes = float(match.group())
                return minutes
            else:
                print(f"⚠️ Réponse GPT non parsable: {text}")
                return None
                
        except Exception as e:
            print(f"❌ Erreur estimation: {e}")
            return None
    
    def _format_history(self, tasks: List[Dict]) -> str:
        """Formate l'historique pour le prompt"""
        if not tasks:
            return "Aucune tâche similaire trouvée dans l'historique."
        
        lines = []
        for task in tasks[:10]:  # Limiter à 10 tâches max
            nom = task.get("nom", "Sans nom")
            temps = task.get("temps_reel", 0)
            desc = task.get("description", "")[:100]  # Tronquer
            lines.append(f"- {nom}: {temps}h ('{desc}')")
        
        return "\n".join(lines)
    
    def estimate_project_duration(
        self,
        project_name: str,
        project_description: str,
        project_content: str,
        tasks_summary: str = "",
        historical_projects: List[Dict] = []
    ) -> Optional[float]:
        """
        Estime la durée globale d'un projet en SEMAINES
        Mode "Senior PM" : vue d'ensemble, charge globale
        """
        
        # Formater l'historique des projets
        history_str = ""
        if historical_projects:
            history_lines = []
            for p in historical_projects[:5]:
                h_weeks = p.get('duree_reelle', '?')
                h_name = p.get('nom', 'Sans nom')
                history_lines.append(f"- {h_name}: {h_weeks} semaines")
            history_str = "\n".join(history_lines)
        else:
            history_str = "Pas d'historique disponible."

        system_prompt = "Tu es un Chef de Projet Senior (Senior PM) expert en estimation de charge macro."
        user_prompt = f"""RÔLE:
Tu es un Chef de Projet Senior expérimenté. 
Tu dois estimer la charge de travail globale d'un projet SANS faire la somme des tâches, mais en l'évaluant dans sa globalité (complexité, incertitudes, temps incompressible, gestion, révisions).

PROJET À ESTIMER:
Nom: {project_name}
Description: {project_description}

CONTENU DÉTAILLÉ / NOTES DU PROJET:
{project_content if project_content else "Pas de notes détaillées."}

RÉSUMÉ DES TÂCHES IDENTIFIÉES:
{tasks_summary if tasks_summary else "Pas de tâches liées."}

HISTORIQUE PROJETS SIMILAIRES:
- Sol 1 & 2 (Références): > 12 semaines (Projets très complexes, ne pas sous-estimer)
{history_str}

ÉCHELLE DE TEMPS AUTORISÉE (SEMAINES) - SOIS LARGE :
- 1 semaine (Tâche simple)
- 2 semaines
- 4 semaines (1 mois)
- 6 semaines (1.5 mois)
- 8 semaines (2 mois)
- 10 semaines
- 12 semaines (3 mois)
- 16 semaines (4 mois)
- 20 semaines (5 mois)
- 24 semaines (6 mois)

INSTRUCTIONS CRITIQUES:
1. 🔍 ANALYSE LE CONTEXTE (Description/Propriétés) : 
   - Si tu vois "Quick Win" ou "Gain rapide" -> L'estimation DOIT être courte (max 2-3 semaines), sauf incohérence technique majeure.
   - Si tu vois "Fond", "Structurant" -> Minimum 4-6 semaines.
2. ⚠️ ATTENTION À LA SOUS-ESTIMATION : Pour les projets complexes (hors Quick Win), c'est le piège n°1. Les "Sol 1" et "Sol 2" ont dépassé 10 semaines.
3. Si le projet semble simple mais implique de l'IA, du développement ou de la coordination, tape HAUT.
4. Inclus une forte marge d'incertitude ("cone of uncertainty"). Mieux vaut surestimer que l'inverse.
5. Analyse la complexité technique : API ? Authentification ? Data ? Si oui -> Minimum 4-6 semaines.
5. Ne tente PAS de décomposer en heures. Pense en "semaines de travail effectif" (délais, validation, debug).
6. Choisis L'UNE des valeurs autorisées ci-dessus.
7. Réponds UNIQUEMENT par le chiffre (ex: 6).

DURÉE ESTIMÉE EN SEMAINES (Optimiste = Interdit) :"""

        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 20
                },
                timeout=30
            )

            if response.status_code != 200:
                print(f"❌ Erreur GPT API ({response.status_code}): {response.text}")
                return None

            result = response.json()
            text = result["choices"][0]["message"]["content"].strip()

            # Extraire le nombre (peut être décimal)
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                weeks = float(match.group(1))
                # Valider que c'est une valeur autorisée
                valid_values = [0.5, 1, 1.5, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24]
                # Arrondir à la valeur autorisée la plus proche
                closest = min(valid_values, key=lambda x: abs(x - weeks))
                return closest
            else:
                print(f"⚠️ Réponse GPT non parsable: {text}")
                return None
        except Exception as e:
            print(f"❌ Erreur estimation projet GPT: {e}")
            return None

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
            
            # Filtrer l'historique (tâches similaires du même projet)
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
