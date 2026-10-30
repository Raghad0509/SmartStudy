# SmartStudyMCP

SmartStudyMCP is a local **Model Context Protocol (MCP) server** for organizing study tasks and notes. It uses the official MCP Python SDK's FastMCP API and SQLite, a small database stored on your computer. Tools, Resources, and Prompts are implemented and registered in separate modules.

Connect it to an MCP-compatible AI client such as Claude Desktop to manage your study data in a conversation. Tasks, notes, search, quizzes, and study plans are implemented locally; **the server itself does not need an API key or a paid AI service**. An AI client may have its own account or service requirements.

## What you need

- Windows 10 or later
- Python 3.11 or newer
- Claude Desktop for the Claude setup below (optional; another MCP client can also connect)

To check that Python is installed, open PowerShell and run:

```powershell
py --version
py -0p
```

If `py` is not recognized, install Python 3.11 or newer and enable the Python launcher during setup. You can also use `python --version` if `python` is on your PATH.

## Install and run in Windows PowerShell

Open PowerShell and change to the folder containing `server.py`. For the example location used in this project:

```powershell
Set-Location "$HOME\Desktop\SmartStudyMCP"
```

Create a virtual environment and install the dependencies:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

These commands use the virtual environment directly, so you do not need to change PowerShell's script execution policy or activate the environment. If you prefer activation, run `.\.venv\Scripts\Activate.ps1` first, then use `python` in place of `.\.venv\Scripts\python.exe`.

The server is designed to be started by an MCP client using **stdio**. Claude Desktop configuration is below. To start it manually for a startup check, run:

```powershell
.\.venv\Scripts\python.exe .\server.py
```

An idle process is expected: it is waiting for MCP protocol messages, not opening a chat or accepting ordinary text commands. Stop the check with `Ctrl+C`. Diagnostic logs go to stderr; stdout is reserved for MCP communication.

On its first start, the server creates `smartstudy.db` beside `server.py`. Tasks and notes persist in this SQLite file. To store the database somewhere else for the current PowerShell session, set the environment variable before launching the client:

```powershell
$env:SMARTSTUDY_DB_PATH = "$HOME\Documents\SmartStudy\smartstudy.db"
```

## Connect to Claude Desktop

1. Install the project dependencies using the commands above.
2. From the project folder, print the **absolute** executable and server paths:

   ```powershell
   (Resolve-Path .\.venv\Scripts\python.exe).Path
   (Resolve-Path .\server.py).Path
   ```

3. Open Claude Desktop's configuration file:

   ```powershell
   notepad "$env:APPDATA\Claude\claude_desktop_config.json"
   ```

   If the folder or file does not exist, create it. The configuration is JSON. For a new, otherwise-empty file, use this structure and replace both example paths with the absolute paths printed in step 2:

   ```json
   {
     "mcpServers": {
       "smart-study": {
         "command": "C:\\Users\\YourName\\Desktop\\SmartStudyMCP\\.venv\\Scripts\\python.exe",
         "args": [
           "C:\\Users\\YourName\\Desktop\\SmartStudyMCP\\server.py"
         ]
       }
     }
   }
   ```

   **If the file already contains configuration, do not replace it.** Keep all existing settings and MCP server entries. Add only the `"smart-study"` property inside the existing `"mcpServers"` object. For example, merge the new entry alongside an existing server:

   ```json
   {
     "mcpServers": {
       "an-existing-server": {
         "command": "C:\\Path\\To\\ExistingServer.exe",
         "args": []
       },
       "smart-study": {
         "command": "C:\\Users\\YourName\\Desktop\\SmartStudyMCP\\.venv\\Scripts\\python.exe",
         "args": [
           "C:\\Users\\YourName\\Desktop\\SmartStudyMCP\\server.py"
         ]
       }
     }
   }
   ```

   Keep the comma between entries as shown, replace the example paths with your own, and preserve the rest of your existing file. If `"mcpServers"` is not present, add it at the top level without removing unrelated top-level settings. In JSON, Windows path separators must be written as `\\`.

4. Save the file and fully quit and restart Claude Desktop. Check the app's MCP integrations or available tools for **SmartStudyMCP**.

Use the full path to `.venv\Scripts\python.exe` for `"command"` and the full path to `server.py` for its argument. Do not use a relative path, a shell command, or the `py` launcher in the Claude configuration.

## Try it in Claude

These are example requests to type into Claude after the server is connected. Claude chooses the relevant tool based on your request; task and note changes are saved in the local database.

**Create and list a task**

> Add a high-priority Biology task called "Review cell division" due 2030-05-12, then show my Biology tasks.

This uses `add_study_task` followed by `list_study_tasks`. The task tool returns its saved ID, which you can use in later requests.

**Save and find a note**

> Save a Physics note titled "Newton's third law" with this content: "For every action, there is an equal and opposite reaction." Then search my notes for "opposite reaction".

This uses `save_study_note` and `search_study_notes`.

**Ask for practice questions**

> Make three practice questions from my Physics notes.

This uses `generate_quiz` with saved notes for the subject. Generated questions are clearly labeled **not verified facts**: they are practice prompts, not authoritative answers or fact-checking.

**Make a weekly schedule**

> I have 90 minutes per day for Math and Biology. Math is due 2030-05-12. Make me a study plan for the week.

This can use `create_study_plan` to produce a structured seven-day schedule. You can also ask Claude to use the `weekly_study_plan` prompt for an AI-written schedule with breaks and review sessions.

**Read your dashboard**

> How many tasks are pending or overdue?

Claude can read the `study://summary` resource to get the current counts. The counts come from SQLite rather than from conversation history.

## Project files

```text
SmartStudyMCP/
|-- server.py
|-- tools.py
|-- resources.py
|-- prompts.py
|-- database.py
|-- requirements.txt
|-- README.md
`-- tests/
    |-- test_database.py
    `-- test_tools.py
```

- `server.py` creates the one shared `FastMCP` server, initializes the shared SQLite database, imports each feature module's registration function, registers all three primitive groups, and starts the stdio transport.
- `tools.py` defines and registers the eight callable study tools.
- `resources.py` defines and registers three resource readers that fetch current data from SQLite.
- `prompts.py` defines and registers four reusable prompt templates for the connected AI client.
- `database.py` owns SQLite schema initialization, validation, and data-access methods used by tools and resources. Existing `study_tasks` and `study_notes` tables are created only when absent; the server does not replace the database file.
- `requirements.txt` lists the official MCP Python SDK dependency.
- `tests/test_database.py` tests the SQLite layer; `tests/test_tools.py` tests tool behavior and verifies tools, resources, and prompts are registered.

## How the MCP features work

MCP has three different primitives. `server.py` creates the shared FastMCP instance named `mcp` and passes that same instance to `register_tools`, `register_resources`, and `register_prompts`. Each module decorates its own functions with the official FastMCP `@mcp.tool()`, `@mcp.resource(...)`, or `@mcp.prompt()` API during its registration call. The modules receive a database provider where needed, so they can access the shared SQLite database without importing `server.py` or creating circular imports.

When run as a script, `server.py` calls `mcp.run(transport="stdio")`. MCP messages use stdout; diagnostic logging is directed to stderr. SQLite access is centralized in `database.py`.

### Tools: actions that can read or change data

Tools are callable operations. Claude can select one when a request calls for an action:

| Tool | Purpose |
| --- | --- |
| `add_study_task` | Create a task with title, subject, due date, and priority |
| `list_study_tasks` | List tasks, optionally filtered by status or subject |
| `update_study_task` | Change a task's title, subject, due date, priority, or status |
| `delete_study_task` | Delete a task by ID and report whether it was deleted |
| `save_study_note` | Save a note with a title, subject, and content |
| `search_study_notes` | Search notes by keyword, subject, or both |
| `generate_quiz` | Build labeled practice questions from supplied text or saved notes |
| `create_study_plan` | Produce a structured seven-day schedule from subjects, daily study minutes, and optional deadlines |

Dates use `YYYY-MM-DD`. Priorities are `low`, `medium`, or `high`; task statuses are `pending`, `in_progress`, or `completed`. Input is validated, SQL values are parameterized, and missing records or empty search results are reported without silently replacing existing data.

`generate_quiz` and `create_study_plan` run locally and deterministically; they do not call an AI model. The quiz tool generates study prompts from source text and explicitly marks them as unverified practice material. The AI client can separately use the prompts below to produce model-generated responses.

### Resources: readable current data

Resources provide data for an MCP client to read. They are backed by SQLite and queried when read, so later tool changes appear in the resource contents:

- `study://tasks` — all saved tasks
- `study://notes` — all saved notes
- `study://summary` — total, completed, pending, and overdue task counts

Resources provide a current view of saved data; they are not tools for editing it.

### Prompts: reusable instructions for the AI client

Prompts are templates that the MCP client can fill with arguments and give to its AI model. They do not execute a model from the server:

- `weekly_study_plan` — request a realistic weekly schedule from subjects, study time, and deadlines
- `explain_topic` — request a clear explanation with examples
- `quiz_me` — request an interactive, one-question-at-a-time quiz
- `summarize_notes` — request a concise summary of supplied notes

For example, `explain_topic` takes a topic such as `"photosynthesis"` and returns a prepared instruction for Claude to explain it. The model's response is generated by the AI client, not by SQLite or the MCP server.

## Run the tests

From the project directory:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests cover database persistence, task creation and updates, deletion, note search, validation, empty results, task summaries, tool behavior, and registration of tools, resources, and prompts. They use temporary SQLite databases and do not modify your regular study database.

## Run the server

From the project directory, start the stdio server with:

```powershell
.\.venv\Scripts\python.exe .\server.py
```

The server waits for an MCP client on stdin/stdout. For normal use, connect it to Claude Desktop using the configuration above instead of typing into the terminal.

## Troubleshooting

- **`py` or Python is not found:** install Python 3.11 or newer, enable the Python launcher, reopen PowerShell, and check `py -0p`. If only `python` works, use `python -m venv .venv` instead of `py -3 -m venv .venv`.
- **MCP dependency is missing:** from the project directory run `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`. Use the same `.venv` Python executable in Claude's configuration.
- **PowerShell says script execution is disabled:** the setup and test commands above call `.venv\Scripts\python.exe` directly and do not require environment activation.
- **Claude cannot start the server:** check that both configuration paths exist, point to the project's virtual environment Python and `server.py`, and are absolute paths. Check JSON syntax and commas, preserve the existing configuration, and restart Claude Desktop completely.
- **You see an idle terminal after running `server.py`:** that is expected for a stdio server waiting for its MCP client. It is not an interactive command prompt.
- **Startup fails or the database cannot be created:** run the server command from PowerShell to see stderr diagnostics. Ensure the project/database folder is writable, or set `SMARTSTUDY_DB_PATH` to a writable absolute file path before launching the MCP client.
