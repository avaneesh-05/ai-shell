from importlib import metadata

try:
    # This is the modern way to get a package's version
    __version__ = metadata.version("ai-shell")
except metadata.PackageNotFoundError:
    # Fallback for when the package is not installed (e.g., during development)
    __version__ = "0.1.0"

command_name = "ai"
project_name = "AI Shell"
repo_url = "https://github.com/BuilderIO/ai-shell" # Original repo URL
