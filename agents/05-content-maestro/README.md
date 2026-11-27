# Content Maestro

A research-aware content planning starter. It creates an editorial brief, suggested angles, section outline, research questions, and a fact-check checklist.

## Run

~~~powershell
python main.py --topic "How high-yield savings accounts work" --audience "US consumers" --format "video script"
~~~

## Important limitation

This starter does not browse the web, retrieve sources, or call a language model. Its output explicitly marks research as not performed and identifies the facts that a human or configured research adapter should verify before publication.
