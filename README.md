acitvate venv

pip install -e


mabx vcau gxum pzpg

API KEY-AIzaSyADuyBQz9dVIA-bfwraH1TDpZd2Ur-ff14


API KEY-AIzaSyBM7QDqlThZ3pC9EGBDI_9FC6C5-PoqWXE       (Paid)
##  Installation

It is strongly recommended to use a virtual environment.

1.  **Clone the repository and navigate into it.**

2.  **Install Poetry (if you don't have it):**
    ```sh
    pip install poetry
    ```

3.  **Install dependencies using Poetry:**
    ```sh
    poetry install
    ```
    This command reads the `pyproject.toml` file and installs all required packages. It also makes the `ai` command available in your shell.

## Configuration

Before you can use the tool, you need to configure your Google Gemini API key.

1.  **Get an API Key**: Visit [Google AI Studio](https://aistudio.google.com/app/apikey) to create your API key.

2.  **Set the API Key**: Run the following command and paste your key when prompted.
    ```sh
    ai config ui
    ```
    Alternatively, you can set it directly:
    ```sh
    ai config set GOOGLE_API_KEY=YOUR_API_KEY_HERE
    ```
    This will save your configuration to `~/.ai_shell_config.json`.

## Usage

### Generate a Command
You can pass a prompt directly to the `ai` command.

```sh
ai "find all files in the current directory with a .txt extension and delete them"


