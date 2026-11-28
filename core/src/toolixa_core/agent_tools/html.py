"""Bounded extraction from a supplied local HTML file; no network access."""
from __future__ import annotations
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin,urlsplit
from toolixa_core.agent_tools.workspace import read_workspace_text
from toolixa_core.tools.base import ToolCallContext,ToolSpec

class _DocumentParser(HTMLParser):
 def __init__(self,base_url:str|None,max_links:int)->None:
  super().__init__(convert_charrefs=True); self.base_url=base_url; self.max_links=max_links
  self.title_parts=[]; self.headings=[]; self.links=[]; self.description=None; self.canonical=None
  self._capture=None; self._buffer=[]; self._heading_level=None; self._seen_links=set()
 def handle_starttag(self,tag:str,attrs:list[tuple[str,str|None]])->None:
  values={key.lower():value or "" for key,value in attrs}
  if tag=="title": self._capture,self._buffer="title",[]
  elif tag in {"h1","h2","h3"}: self._capture,self._buffer,self._heading_level="heading",[],int(tag[1])
  elif tag=="meta" and values.get("name","").lower()=="description": self.description=values.get("content","").strip()[:1000] or None
  elif tag=="link" and "canonical" in values.get("rel","").lower():
   candidate=values.get("href","").strip()
   if candidate: self.canonical=urljoin(self.base_url or "",candidate)
  elif tag=="a" and "href" in values and len(self.links)<self.max_links:
   href=values["href"].strip(); resolved=urljoin(self.base_url or "",href); scheme=urlsplit(resolved).scheme.lower()
   if href and scheme in {"","http","https"} and resolved not in self._seen_links:
    self._seen_links.add(resolved); self.links.append({"href":resolved,"text":""}); self._capture,self._buffer="link",[]
 def handle_endtag(self,tag:str)->None:
  if tag=="title" and self._capture=="title":
   self.title_parts.append(" ".join(" ".join(self._buffer).split())[:300]); self._capture=None
  elif tag in {"h1","h2","h3"} and self._capture=="heading":
   value=" ".join(" ".join(self._buffer).split())
   if value and len(self.headings)<150: self.headings.append({"level":self._heading_level,"text":value[:500]})
   self._capture=None
  elif tag=="a" and self._capture=="link":
   if self.links: self.links[-1]["text"]=" ".join(" ".join(self._buffer).split())[:300]
   self._capture=None
 def handle_data(self,data:str)->None:
  if self._capture in {"title","heading","link"}: self._buffer.append(data)

class ExtractHTMLFileTool:
 spec=ToolSpec("html.extract_file","Extract metadata, heading hierarchy and links from a bounded local HTML file. Never fetches the base URL or any link.",("workspace.read",),{"type":"object","properties":{"path":{"type":"string","minLength":1,"maxLength":500},"base_url":{"type":"string","maxLength":2048},"max_links":{"type":"integer","minimum":0,"maximum":200}},"required":["path"],"additionalProperties":False})
 def invoke(self,arguments:dict[str,Any],context:ToolCallContext)->dict[str,Any]:
  relative,source=read_workspace_text(context,arguments["path"],max_bytes=1_000_000)
  if len(source)>1_000_000: raise ValueError("HTML source exceeds the 1 MB limit")
  base_url=arguments.get("base_url")
  if base_url:
   parsed=urlsplit(base_url)
   if parsed.scheme not in {"http","https"} or not parsed.hostname or parsed.username or parsed.password: raise ValueError("base_url must be an absolute HTTP(S) URL without credentials")
  maximum=arguments.get("max_links",100)
  if not 0<=maximum<=200: raise ValueError("max_links must be between 0 and 200")
  parser=_DocumentParser(base_url,maximum); parser.feed(source); parser.close()
  return {"path":relative.as_posix(),"title":parser.title_parts[0] if parser.title_parts else None,"description":parser.description,"canonical":parser.canonical,"headings":parser.headings,"links":parser.links,"links_returned":len(parser.links),"network_requests":0,"scope":"local_html_only"}
