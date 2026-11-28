"""Validate editorial briefs and their source-reference coverage."""
from __future__ import annotations
from typing import Any
from urllib.parse import urlsplit
from toolixa_core.tools.base import ToolCallContext,ToolSpec

class ValidateEditorialBriefTool:
 spec=ToolSpec("content.validate_editorial_brief","Check editorial structure and whether factual claims have plausible HTTPS references. Does not fetch sources or certify truth.",(),{"type":"object","properties":{"title":{"type":"string","minLength":1,"maxLength":200},"audience":{"type":"string","minLength":1,"maxLength":200},"content_format":{"type":"string","minLength":1,"maxLength":100},"sections":{"type":"array","maxItems":50,"items":{"type":"string","minLength":1,"maxLength":300}},"claims":{"type":"array","maxItems":100,"items":{"type":"object","properties":{"claim":{"type":"string","minLength":1,"maxLength":1000},"source_urls":{"type":"array","maxItems":10,"items":{"type":"string","minLength":1,"maxLength":2048}}},"required":["claim","source_urls"],"additionalProperties":False}}},"required":["title","audience","content_format","sections","claims"],"additionalProperties":False})
 def invoke(self,arguments:dict[str,Any],context:ToolCallContext)->dict[str,Any]:
  del context
  unsupported=[]; malformed=[]
  for index,claim in enumerate(arguments["claims"],1):
   if not claim["source_urls"]: unsupported.append(index)
   for url in claim["source_urls"]:
    parsed=urlsplit(url)
    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password: malformed.append({"claim_index":index,"reason":"source must be an absolute HTTPS URL"})
  return {"valid_structure":bool(arguments["sections"]) and not unsupported and not malformed,"title_present":bool(arguments["title"].strip()),"audience_present":bool(arguments["audience"].strip()),"sections_count":len(arguments["sections"]),"claims_count":len(arguments["claims"]),"claims_without_source":unsupported,"invalid_source_references":malformed,"source_fetch_performed":False,"fact_accuracy_verified":False}
