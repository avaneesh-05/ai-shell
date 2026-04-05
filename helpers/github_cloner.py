import subprocess
import shutil
import os
from helpers.error import KnownError


def clone_repo(repo_url: str, destination: str) -> dict:
    """
    Clones a GitHub repository to the specified destination.
    Returns a dict with 'success', 'path', and 'message' keys.
    """
    # 1. Check if git is installed
    if not shutil.which("git"):
        raise KnownError(
            "Git is not installed on this system. "
            "Please install it first: https://git-scm.com/downloads"
        )

    # 2. Derive the final clone path
    #    e.g. repo_url = "https://github.com/user/repo.git"
    #    repo_name = "repo"
    repo_name = repo_url.rstrip("/").rstrip(".git").split("/")[-1]
    clone_path = os.path.join(destination, repo_name)

    # 3. Check if destination already exists
    if os.path.exists(clone_path):
        return {
            "success": False,
            "path": clone_path,
            "message": f"Directory already exists: {clone_path}",
        }

    # 4. Ensure parent directory exists
    os.makedirs(destination, exist_ok=True)

    # 5. Run git clone
    try:
        result = subprocess.run(
            ["git", "clone", repo_url, clone_path],
            capture_output=True,
            text=True,
            timeout=300,  # 5-minute timeout for large repos
        )

        if result.returncode == 0:
            return {
                "success": True,
                "path": clone_path,
                "message": f"Repository cloned successfully to {clone_path}",
            }
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            return {
                "success": False,
                "path": clone_path,
                "message": f"Git clone failed: {error_msg}",
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "path": clone_path,
            "message": "Git clone timed out after 5 minutes. The repository may be too large.",
        }
    except Exception as e:
        return {
            "success": False,
            "path": clone_path,
            "message": f"Unexpected error during clone: {e}",
        }
