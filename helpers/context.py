# helpers/context.py
"""
Gathers filesystem and git context to feed into LLM prompts.
"""
import os
import subprocess
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

    # 4. Git-aware context
    git_context = get_git_context()
    if git_context:
        context_lines.append("")
        context_lines.append(git_context)

    return "\n".join(context_lines)


def get_git_context() -> str:
    """
    If the current directory is inside a git repository, return a summary of:
      - Repository root path
      - Current branch name
      - Dirty / modified / untracked files
      - Last 5 commit subjects
    Returns an empty string if not in a git repo or on any error.
    """
    try:
        # Quick check: are we in a git repo?
        repo_root = _git("rev-parse", "--show-toplevel")
        if not repo_root:
            return ""

        parts = [f"Git Repository: {repo_root}"]

        # Current branch
        branch = _git("rev-parse", "--abbrev-ref", "HEAD")
        if branch:
            parts.append(f"Branch: {branch}")

        # Dirty status — short summary
        status = _git("status", "--short")
        if status:
            status_lines = status.strip().splitlines()
            modified = [l[3:] for l in status_lines if l.startswith(" M") or l.startswith("M ")]
            added = [l[3:] for l in status_lines if l.startswith("A ") or l.startswith("?? ")]
            deleted = [l[3:] for l in status_lines if l.startswith(" D") or l.startswith("D ")]

            if modified:
                parts.append(f"Modified files: {', '.join(modified[:10])}")
            if added:
                parts.append(f"New/untracked files: {', '.join(added[:10])}")
            if deleted:
                parts.append(f"Deleted files: {', '.join(deleted[:10])}")
        else:
            parts.append("Working tree: clean")

        # Recent commits (last 5)
        log = _git("log", "--oneline", "-5", "--no-decorate")
        if log:
            parts.append(f"Recent commits:\n{log}")

        # Remote URL (helps identify the project)
        remote = _git("remote", "get-url", "origin")
        if remote:
            parts.append(f"Remote origin: {remote}")

        return "\n".join(parts)

    except Exception:
        return ""


def _git(*args: str) -> str:
    """
    Runs a git command and returns stripped stdout, or empty string on failure.
    Times out after 3 seconds to avoid hangs on large repos.
    """
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return ""
    except Exception:
        return ""