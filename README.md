# AI Shell 🤖

An AI-powered shell assistant that translates natural language into shell commands, powered by Google Gemini.

## ✨ Features

- 🚀 **Natural Language → Shell Commands** — Describe what you want in plain English, get executable commands
- 📧 **Email Drafting & Sending** — AI-assisted email composition with iterative refinement
- 📦 **GitHub/GitLab Cloning** — Clone repositories with natural language (supports both platforms)
- 💬 **Interactive Chat** — Have a conversation with AI directly in your terminal
- 🔒 **Security PIN** — Protect against accidental execution of dangerous commands (`rm`, `sudo`, etc.)
- 🌐 **Multi-language Support** — i18n-ready with locale files
- 📋 **Clipboard Integration** — Copy generated commands to clipboard
- 📝 **Shell History** — Executed commands are appended to your shell history

---

## 📦 Installation

> It is strongly recommended to use a virtual environment.

1. **Clone the repository:**
   ```sh
   git clone https://github.com/avaneesh-05/ai-shell.git
   cd ai-shell
   ```

2. **Create and activate a virtual environment:**
   ```sh
   python -m venv .venv
   source .venv/bin/activate      # Linux/macOS
   # .venv\Scripts\activate       # Windows
   ```

3. **Install in development mode:**
   ```sh
   pip install -e .
   ```
   This installs all dependencies and makes the `ai` command available in your shell.

---

## ⚙️ Configuration

Before using the tool, you need to configure your Google Gemini API key.

1. **Get an API Key**: Visit [Google AI Studio](https://aistudio.google.com/app/apikey) to create your API key.

2. **Set the API Key** (interactive UI):
   ```sh
   ai config ui
   ```

3. **Or set it directly:**
   ```sh
   ai config set GOOGLE_API_KEY=YOUR_API_KEY_HERE
   ```

   Configuration is saved to `~/.ai_shell_config.json`.

### Available Config Options

| Key              | Description                    | Default            |
| ---------------- | ------------------------------ | ------------------ |
| `GOOGLE_API_KEY` | Your Gemini API key            | *(required)*       |
| `MODEL`          | Gemini model to use            | `gemini-2.0-flash` |
| `SILENT_MODE`    | Skip command explanations      | `false`            |
| `LANGUAGE`       | Interface language             | `en`               |
| `EMAIL_USER`     | Email address for sending      | *(optional)*       |
| `EMAIL_PASSWORD` | Email app password             | *(optional)*       |
| `SECURITY_PIN`   | PIN for risky command approval | `1234`             |

---

## 🚀 Usage

### Generate Commands (Direct Shortcut)

The fastest way — just type `ai` followed by your request:

```sh
ai "find all .txt files and delete them"
ai "list all running docker containers"
ai "create a python script that prints hello world"
```

### Generate Commands (Explicit)

```sh
ai prompt "compress all .log files into an archive"
ai prompt --silent "show disk usage"
```

### Interactive Chat

Start a back-and-forth conversation with the AI:

```sh
ai chat
```

### Send Emails

AI Shell detects email intent and walks you through composing and sending:

```sh
ai "send an email to john@example.com about the project update"
ai "draft a professional email to the team about the deadline"
```

### Clone Repositories

Supports both GitHub and GitLab:

```sh
ai "clone https://github.com/user/repo"
ai "download the gitlab repo org/project"
```

### Other Commands

```sh
ai --version            # Show version
ai --silent "prompt"    # Run without explanations
ai config ui            # Interactive configuration wizard
ai config set KEY=VAL   # Set a config value directly
ai config get KEY       # Get a config value
ai update               # Update AI Shell
```

---

## 🏗️ Project Structure

```
ai-shell/
├── cli.py                  # Main CLI entry point
├── __main__.py             # Package runner
├── pyproject.toml          # Project configuration & dependencies
├── commands/
│   ├── prompt_command.py   # Natural language → shell commands
│   ├── chat_command.py     # Interactive chat mode
│   ├── config_command.py   # Configuration management
│   └── update_command.py   # Self-update command
├── helpers/
│   ├── completion.py       # LLM completion & execution planning
│   ├── config.py           # Config file management
│   ├── constants.py        # Project constants
│   ├── context.py          # Directory context awareness
│   ├── email_sender.py     # SMTP email sending
│   ├── email_workflow.py   # AI-powered email drafting workflow
│   ├── error.py            # Error handling
│   ├── github_cloner.py    # Git clone operations
│   ├── github_workflow.py  # AI-powered repo cloning workflow
│   ├── i18n.py             # Internationalization
│   ├── os_detect.py        # OS/shell detection
│   ├── security.py         # Risky command protection (PIN)
│   └── shell_history.py    # Shell history integration
└── locales/
    └── en.json             # English translations
```

---

## 🔒 Security

AI Shell includes a safety feature for risky commands. When a generated command contains dangerous operations (e.g., `rm`, `sudo`, `chmod`, `dd`), you'll be prompted to enter your **Security PIN** before execution.

The default PIN is `1234`. Change it via:

```sh
ai config ui
```

---

## 📄 License

MIT


