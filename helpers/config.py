import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from .i18n import _
from .error import KnownError

CONFIG_PATH = Path.home() / ".ai_shell_config.json"
DEFAULT_CONFIG = {
    "GOOGLE_API_KEY": None,
    "MODEL": "gemini-1.5-flash",
    "SILENT_MODE": False,
    "LANGUAGE": "en",
}

def get_config() -> Dict[str, Any]:
    """Reads the config file and returns it, creating one if it doesn't exist."""
    if not CONFIG_PATH.exists():
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG
    
    with open(CONFIG_PATH, "r") as f:
        try:
            config = json.load(f)
            # Ensure all default keys exist
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
        except json.JSONDecodeError:
            raise KnownError(f"Error reading config file at {CONFIG_PATH}. It might be corrupted.")

def set_configs(key_values: List[Tuple[str, str]]):
    """Sets one or more configuration values."""
    config = get_config()
    for key, value in key_values:
        if key.upper() not in DEFAULT_CONFIG:
            raise KnownError(f"{_('Invalid config property')}: {key}")
        
        # Coerce boolean strings to booleans
        if value.lower() in ["true", "false"]:
            config[key.upper()] = value.lower() == "true"
        else:
            config[key.upper()] = value

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

def has_own(obj: Dict, key: str) -> bool:
    """Checks if a key exists in a dictionary."""
    return key in obj