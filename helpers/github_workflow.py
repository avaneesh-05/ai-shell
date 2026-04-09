import os
import re
import json
import textwrap
import questionary
from rich.console import Console
from rich.panel import Panel
from .completion import get_gemini_llm

from helpers.config import get_config
from helpers.github_cloner import clone_repo
from helpers.i18n import _

console = Console()

DEFAULT_DESTINATION = os.path.expanduser("~/Desktop")


def detect_platform(url: str) -> str:
    """Detects whether a URL is GitHub, GitLab, or unknown."""
    if not url:
        return "Git"
    url_lower = url.lower()
    if "gitlab" in url_lower:
        return "GitLab"
    if "github" in url_lower:
        return "GitHub"
    return "Git"


def extract_repo_info(user_prompt: str, key: str, model: str) -> dict:
    """
    Uses the LLM to extract GitHub/GitLab repository information from a natural language prompt.
    Returns a dict with 'url', 'owner', 'repo_name', 'platform' keys.
    """
    llm = get_gemini_llm(key, model)

    system_prompt = textwrap.dedent(f"""
        You are a Git repository URL extractor. You support both GitHub and GitLab.
        
        User Request: "{user_prompt}"
        
        Task:
        1. Extract the repository URL, owner, and repo name from the user's request.
        2. Determine the platform: "github" or "gitlab".
        3. If the user provides a shorthand like "owner/repo" without specifying the platform, default to "github".
        4. If the user provides a full URL like "https://github.com/owner/repo" or "https://gitlab.com/owner/repo", extract it directly.
        5. If the user explicitly mentions "gitlab", use gitlab.com as the host.
        6. If the user mentions a repo name without an owner, set owner to null.
        
        Respond ONLY with JSON (no markdown, no code blocks):
        {{"url": "https://github.com/owner/repo", "owner": "owner", "repo_name": "repo", "platform": "github"}}
        
        Examples:
        - "clone gitlab repo user/myproject" → {{"url": "https://gitlab.com/user/myproject", "owner": "user", "repo_name": "myproject", "platform": "gitlab"}}
        - "download https://github.com/user/repo" → {{"url": "https://github.com/user/repo", "owner": "user", "repo_name": "repo", "platform": "github"}}
        - "get me the gitlab repo at gitlab.com/org/tool" → {{"url": "https://gitlab.com/org/tool", "owner": "org", "repo_name": "tool", "platform": "gitlab"}}
        
        If you cannot identify a valid repository, respond with:
        {{"url": null, "owner": null, "repo_name": null, "platform": null}}
    """)

    try:
        response = llm.complete(system_prompt).text.strip()
        # Remove markdown code fences if present
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
            response = response.strip()

        result = json.loads(response)
        # Ensure platform field exists
        if "platform" not in result:
            result["platform"] = detect_platform(result.get("url"))
        return result
    except Exception as e:
        console.print(f"[yellow]Warning: Could not parse repo info. {str(e)}[/yellow]")
        return {"url": None, "owner": None, "repo_name": None, "platform": None}


def validate_repo_url(url: str, platform: str = "github") -> str:
    """
    Validates and normalizes a GitHub/GitLab URL to a proper clone URL.
    Returns the normalized URL or None if invalid.
    """
    if not url:
        return None

    url = url.strip().rstrip("/")

    # Pattern: https://github.com/owner/repo or https://gitlab.com/owner/repo (with optional .git)
    https_match = re.match(
        r"^https?://(github\.com|gitlab\.com)/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?$",
        url,
    )
    if https_match:
        host, owner, repo = https_match.groups()
        return f"https://{host}/{owner}/{repo}.git"

    # Pattern: git@github.com:owner/repo.git or git@gitlab.com:owner/repo.git
    ssh_match = re.match(
        r"^git@(github\.com|gitlab\.com):([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?$",
        url,
    )
    if ssh_match:
        host, owner, repo = ssh_match.groups()
        return f"https://{host}/{owner}/{repo}.git"

    # Pattern: owner/repo (shorthand — uses platform to determine host)
    shorthand = re.match(
        r"^([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)$",
        url,
    )
    if shorthand:
        owner, repo = shorthand.groups()
        host = "gitlab.com" if platform.lower() == "gitlab" else "github.com"
        return f"https://{host}/{owner}/{repo}.git"

    return None


def handle_github_intent(user_prompt: str):
    """
    Main Git Repository Workflow — supports GitHub and GitLab.
    Flow:
    1. Extract repo info from user's prompt using LLM
    2. Validate the URL
    3. Confirm with user (repo URL + destination)
    4. Clone the repo
    5. Report result
    """
    config = get_config()
    key = config.get("GOOGLE_API_KEY")
    model = config.get("MODEL", "gemini-1.5-flash")

    # ===== PHASE 1: EXTRACT REPO INFO =====
    console.print(f"\n[bold cyan]🔍 Analyzing your request...[/bold cyan]\n")

    with console.status("[cyan]Extracting repository information...[/cyan]"):
        repo_info = extract_repo_info(user_prompt, key, model)

    raw_url = repo_info.get("url")
    repo_name = repo_info.get("repo_name", "unknown")
    platform = repo_info.get("platform", "github") or "github"
    platform_label = detect_platform(raw_url) if raw_url else platform.capitalize()

    if not raw_url:
        console.print(
            "[red]❌ Could not identify a Git repository from your request.[/red]"
        )
        console.print(
            "[dim]Tip: Try something like 'clone https://github.com/user/repo' "
            "or 'download gitlab repo user/repo'[/dim]"
        )
        return

    # ===== PHASE 2: VALIDATE URL =====
    clone_url = validate_repo_url(raw_url, platform)

    if not clone_url:
        console.print(f"[red]❌ Invalid repository URL: {raw_url}[/red]")
        console.print("[dim]Supported formats: https://github.com/owner/repo, https://gitlab.com/owner/repo, owner/repo[/dim]")
        return

    # ===== PHASE 3: CONFIRM WITH USER =====
    destination = DEFAULT_DESTINATION

    console.print(
        Panel(
            f"[bold]Platform:[/bold] {platform_label}\n"
            f"[bold]Repository:[/bold] {clone_url}\n"
            f"[bold]Destination:[/bold] {destination}/{repo_name}",
            title=f"📦 {platform_label} Clone",
            border_style="cyan",
        )
    )

    action = questionary.select(
        "What would you like to do?",
        choices=[
            questionary.Choice("✅ Clone to Desktop", value="clone"),
            questionary.Choice("📁 Change destination directory", value="change_dest"),
            questionary.Choice("❌ Cancel", value="cancel"),
        ],
    ).ask()

    if action == "change_dest":
        new_dest = questionary.text(
            "Enter destination directory:",
            default=destination,
        ).ask()
        if new_dest:
            destination = os.path.expanduser(new_dest.strip())

        # Show updated info and re-confirm
        console.print(
            Panel(
                f"[bold]Platform:[/bold] {platform_label}\n"
                f"[bold]Repository:[/bold] {clone_url}\n"
                f"[bold]Destination:[/bold] {destination}/{repo_name}",
                title=f"📦 {platform_label} Clone (Updated)",
                border_style="cyan",
            )
        )
        confirm = questionary.confirm("Proceed with cloning?", default=True).ask()
        if not confirm:
            console.print("[yellow]Clone cancelled.[/yellow]")
            return

    elif action == "cancel" or action is None:
        console.print("[yellow]Clone cancelled.[/yellow]")
        return

    # ===== PHASE 4: CLONE =====
    console.print(f"\n[bold cyan]⬇️  Cloning repository...[/bold cyan]\n")

    with console.status("[cyan]Running git clone... (this may take a moment)[/cyan]"):
        result = clone_repo(clone_url, destination)

    # ===== PHASE 5: REPORT =====
    if result["success"]:
        console.print(
            Panel(
                f"[bold green]✔ {result['message']}[/bold green]\n\n"
                f"[dim]You can now open it:[/dim]\n"
                f"  cd {result['path']}",
                title="✅ Clone Successful",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]✖ {result['message']}[/bold red]",
                title="❌ Clone Failed",
                border_style="red",
            )
        )

        # Offer retry options on failure
        retry = questionary.select(
            "What would you like to do?",
            choices=[
                questionary.Choice("🔁 Try again", value="retry"),
                questionary.Choice("📝 Enter URL manually", value="manual"),
                questionary.Choice("❌ Cancel", value="cancel"),
            ],
        ).ask()

        if retry == "retry":
            with console.status("[cyan]Retrying...[/cyan]"):
                result = clone_repo(clone_url, destination)

            if result["success"]:
                console.print(f"[green]✔ {result['message']}[/green]")
            else:
                console.print(f"[red]✖ {result['message']}[/red]")

        elif retry == "manual":
            manual_url = questionary.text(
                "Enter the full repository URL (GitHub or GitLab):",
            ).ask()
            if manual_url:
                validated = validate_repo_url(manual_url.strip())
                if validated:
                    with console.status("[cyan]Cloning...[/cyan]"):
                        result = clone_repo(validated, destination)
                    if result["success"]:
                        console.print(f"[green]✔ {result['message']}[/green]")
                    else:
                        console.print(f"[red]✖ {result['message']}[/red]")
                else:
                    console.print(f"[red]❌ Invalid URL: {manual_url}[/red]")
        else:
            console.print("[yellow]Cancelled.[/yellow]")
