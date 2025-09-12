import os
import platform
from .i18n import _

def detect_shell() -> str:
    """
    Detects the current user's shell.
    Returns 'powershell' on Windows, otherwise the basename of the SHELL env var.
    Defaults to 'bash'.
    """
    if platform.system() == "Windows":
        return "powershell"
    
    try:
        shell_path = os.environ.get("SHELL", "bash")
        return os.path.basename(shell_path)
    except Exception as e:
        raise Exception(f"{_('Shell detection failed unexpectedly')}: {e}")