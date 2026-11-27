# Installation Guide

## Requirements

- Python 3.11 or newer.
- Git.
- A virtual environment is strongly recommended.

The Toolixa directory website is static. It is not required to run any agent.

## Clone and prepare

~~~powershell
git clone https://github.com/tasnimamin38/toolixa-agents.git
cd toolixa-agents
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ./core
~~~

On macOS or Linux, activate with source .venv/bin/activate.

## Install one agent

Install only the selected agent's requirements. For example, Web Scraper:

~~~powershell
python -m pip install -r agents/06-web-scraper/requirements.txt
~~~

Other initial agents use only the Python standard library plus toolixa-core.

Run an agent from its directory:

~~~powershell
cd agents/06-web-scraper
python main.py --help
~~~

## Provider keys

The local starters do not require a paid model provider. Future provider-backed adapters must document the exact provider environment variables they consume. Never add real credentials to agent.json, source code, README files, catalog data, logs, or Git.

## Verify installation

From repository root:

~~~powershell
python scripts/build_catalog.py --check
python -m pytest -q
~~~

## Standalone distribution

An agent folder depends on the compatible toolixa-core package unless its README explicitly says otherwise. Do not distribute a copied folder as a standalone bundle until its core dependency is pinned or included and installation has been tested in a clean virtual environment.
