# Aegis Security

A local, passive source scanner for obvious hard-coded secret patterns and selected risky Python constructs. It reports file and line references but never includes the matched secret value in a finding.

## Install

~~~powershell
python -m pip install -e ./core
~~~

No additional runtime dependencies are required.

## Run

~~~powershell
python main.py --workspace C:\path\to\project
~~~

## Scope

- Scans local source/configuration files under the selected workspace.
- Detects private-key headers and likely secret assignments.
- Detects Python eval/exec and subprocess shell=True call patterns.
- Skips symlinks, common vendor folders, oversized files, and .env.example templates.
- Does not connect to hosts, exploit vulnerabilities, or run active scans.

Findings are heuristic and can contain false positives or false negatives. Review results manually. This starter is not a replacement for a full SAST/SCA platform or professional security assessment.
