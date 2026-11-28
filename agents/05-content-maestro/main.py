"""Editorial brief scaffold that clearly distinguishes planning from research."""

from __future__ import annotations

import argparse
import json

from toolixa_core.agent_runtime_cli import run_agent_cli
from toolixa_core.agent_tools import (
    ListWorkspaceFilesTool,
    ReadWorkspaceFileTool,
    SearchLocalDocsTool,
    ValidateEditorialBriefTool,
)
from toolixa_core.runtime.agent import AgentDefinition


def build_brief(
    topic: str, *, audience: str = "general", content_format: str = "article"
) -> dict[str, object]:
    normalized = topic.strip()
    if not normalized:
        raise ValueError("topic cannot be empty")
    if not audience.strip() or not content_format.strip():
        raise ValueError("audience and content_format cannot be empty")
    return {
        "topic": normalized,
        "audience": audience.strip(),
        "format": content_format.strip(),
        "research_status": "not_performed",
        "title_angles": [
            f"What readers should know about {normalized}",
            f"Common misconceptions about {normalized}",
            f"Practical decisions involving {normalized}",
        ],
        "outline": [
            {"section": "Hook and audience problem", "purpose": "Explain why the topic matters."},
            {"section": "Core explanation", "purpose": "Define key terms and mechanisms."},
            {
                "section": "Evidence and examples",
                "purpose": "Insert verified data and sourced examples.",
            },
            {
                "section": "Risks and trade-offs",
                "purpose": "Explain limitations and counterpoints.",
            },
            {
                "section": "Practical takeaway",
                "purpose": "Give clear next steps without unsupported promises.",
            },
        ],
        "research_questions": [
            f"What are the latest authoritative facts about {normalized}?",
            "Which official regulator, government, or primary-source documents support the key claims?",
            "What dates, eligibility rules, fees, and geographic limits must be stated?",
        ],
        "fact_check": [
            "Verify figures against current primary sources.",
            "Record source URL and publication or update date.",
            "Check geographic and eligibility limitations.",
            "Separate confirmed facts from opinion and editorial framing.",
            "Do not publish unverified performance, savings, or ranking claims.",
        ],
        "sources": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--audience", default="general")
    parser.add_argument("--format", dest="content_format", default="article")
    args = parser.parse_args()
    print(
        json.dumps(
            build_brief(args.topic, audience=args.audience, content_format=args.content_format),
            indent=2,
        )
    )


def build_agent() -> AgentDefinition:
    return AgentDefinition(
        id="content-maestro",
        name="Content Maestro",
        system_prompt=(
            "You are a senior editorial strategist and fact-checking producer. Build a complete content package "
            "for the requested audience and format: audience insight, differentiated angles, narrative arc, section "
            "outline, retention/re-engagement beats, visual suggestions and a practical CTA. Search local source "
            "documents and cite factual claims with exact file/line evidence. Use the editorial brief validator to "
            "identify unsupported claims and malformed source references. The validator checks structure only; it "
            "does not fetch sources or prove factual accuracy. Clearly label unverified claims and never invent "
            "statistics, quotations, source reviews or current facts."
        ),
        tools=(
            ListWorkspaceFilesTool(),
            ReadWorkspaceFileTool(),
            SearchLocalDocsTool(),
            ValidateEditorialBriefTool(),
        ),
        min_tool_calls=1,
    )


if __name__ == "__main__":
    raise SystemExit(run_agent_cli(build_agent(), description=__doc__ or "05-content-maestro"))
