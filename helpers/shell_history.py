import os
from pathlib import Path

def get_history_file() -> str | None:
    """
    Gets the history file path based on the current shell.
    """
    shell_name = os.path.basename(os.environ.get("SHELL", ""))
    home_dir = Path.home()

    history_map = {
        "bash": home_dir / ".bash_history",
        "zsh": home_dir / ".zsh_history",
        "fish": home_dir / ".local" / "share" / "fish" / "fish_history",
        "ksh": home_dir / ".ksh_history",
        "tcsh": home_dir / ".history",
    }
    return str(history_map.get(shell_name)) if shell_name in history_map else None

def append_to_shell_history(command: str):
    """
    Appends a command to the shell's history file.
    """
    history_file = get_history_file()
    if not history_file:
        return

    try:
        last_command = ""
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                if lines:
                    last_command = lines[-1].strip()
        
        if command.strip() != last_command:
            with open(history_file, "a", encoding="utf-8") as f:
                f.write(f"{command}\n")
    except Exception:
        # Silently fail if there are any issues with reading/writing history
        pass