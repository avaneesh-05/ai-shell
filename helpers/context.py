import os
from pathlib import Path

def get_current_directory_context(limit: int = 50) -> str:
    """
    Returns a summary of the current directory, Desktop, AND Downloads.
    """
    context_lines = []
    
    # 1. Scan Current Working Directory (CWD)
    cwd = Path.cwd()
    context_lines.append(f"Current Location: {cwd}")
    try:
        items = list(cwd.iterdir())
        files = [f.name for f in items if f.is_file()]
        dirs = [d.name for d in items if d.is_dir()]
        
        if files:
            context_lines.append(f"Files in current dir: {', '.join(files[:30])}")
        if dirs:
            context_lines.append(f"Folders in current dir: {', '.join(dirs[:15])}")
    except Exception:
        context_lines.append("(Could not read current directory)")

    # 2. SPECIAL: Peek into Desktop
    desktop = Path.home() / "Desktop"
    if desktop.exists() and cwd != desktop:
        try:
            d_items = list(desktop.iterdir())
            d_files = [f.name for f in d_items if f.is_file()]
            if d_files:
                context_lines.append(f"Files on DESKTOP: {', '.join(d_files[:20])}")
        except Exception:
            pass

    # 3. SPECIAL: Peek into Downloads (NEW)
    downloads = Path.home() / "Downloads"
    if downloads.exists() and cwd != downloads:
        try:
            dl_items = list(downloads.iterdir())
            dl_files = [f.name for f in dl_items if f.is_file()]
            if dl_files:
                context_lines.append(f"Files in DOWNLOADS: {', '.join(dl_files[:20])}")
        except Exception:
            pass

    return "\n".join(context_lines)