# Dev Copilot

A safe first-step coding assistant foundation. This starter inventories Python files and checks syntax with Python's AST parser. It does not call an LLM, modify files, install packages, or execute project code.

## Install

From the repository root:

~~~powershell
python -m pip install -e ./core
~~~

No additional runtime dependencies are required.

## Run

~~~powershell
python main.py --workspace C:\path\to\project --max-files 500
~~~

The command prints JSON containing the number of files scanned and any Python syntax errors with line/column details.

## Permissions and limits

- Reads Python source files under the selected workspace only.
- Skips symlinks and common generated/vendor directories.
- Stops after the configured file limit.
- Does not write files, invoke a shell, or access the network.

This is a local analyzer, not an autonomous code-editing agent. Code generation, patch application, and test execution require separate reviewed provider and isolated-executor adapters.
