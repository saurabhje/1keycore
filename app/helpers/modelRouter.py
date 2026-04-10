import json
import os

def load_provider_config():
    current_file_path = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
    config_path = os.path.join(project_root, "models.json")
    with open(config_path, "r") as f:
        return json.load(f)

PROVIDER_CONFIG = load_provider_config()

def get_best_model(available_provider_names: list, tier: str) -> str:
    """
    available_provider_names: ['openai', 'google']
    tier: 'economy', 'standard', or 'premium'
    """
    candidates = []
    # Access the 'providers' key from your JSON
    all_provider_data = PROVIDER_CONFIG["providers"]

    for p_name in available_provider_names:
        p_data = all_provider_data.get(p_name)
        if not p_data or not p_data.get("enabled"):
            continue
            
        model_info = p_data["models"].get(tier)
        if not model_info or not model_info.get("enabled"):
            continue
            
        # Scoring logic using fields from your JSON
        score = (
            model_info["quality"] * 0.5 +
            model_info["speed"] * 0.3 - 
            model_info["cost"] * 0.4
        )
        candidates.append((score, model_info["id"]))
        
    return max(candidates, key=lambda x: x[0])[1]

def score_complexity(message: str, system_prompt: str | None) -> str:
    score = 0
    msg_lower = message.lower()
    
    words = len(message.split())
    if words > 200: score += 3
    elif words > 50: score += 1
    
    premium_keywords = ["analyze", "implement", "architecture", "debug", "optimize", "research"]
    economy_keywords = ["what is", "define", "list", "summarize", "translate"]
    
    for kw in premium_keywords:
        if kw in msg_lower: score += 2
    for kw in economy_keywords:
        if kw in msg_lower: score -= 1
        
    if system_prompt: score += 1
    
    if score >= 4: return "premium"
    elif score >= 2: return "standard"
    else: return "economy"