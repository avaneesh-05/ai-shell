import json
import os
from pathlib import Path

_translations = {}
_current_lang = "en"

# Path to the locales directory inside the package
_locales_path = Path(__file__).parent.parent / 'locales'

def set_language(lang: str = "en"):
    """Sets the language for the application."""
    global _current_lang, _translations
    _current_lang = lang if lang else "en"
    if _current_lang != "en":
        try:
            with open(_locales_path / f'{_current_lang}.json', 'r', encoding='utf-8') as f:
                _translations = json.load(f)
        except FileNotFoundError:
            # Fallback to English if translation file doesn't exist
            _translations = {}
            _current_lang = "en"

def _(key: str) -> str:
    """Translates a key using the loaded language file."""
    if _current_lang == "en":
        return key
    return _translations.get(key, key)

# Initialize with English
set_language("en")