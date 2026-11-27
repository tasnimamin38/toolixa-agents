# RAG Chatbot

A local retrieval starter for Markdown and plain-text files. It chunks documents, performs a small lexical retrieval, and returns the source file and line range for each result.

## Run

~~~powershell
python main.py --workspace C:\path\to\docs --query "refund policy"
~~~

## Scope and limitations

- Reads .md and .txt files from a local directory.
- Uses deterministic keyword retrieval; no embedding model or vector database is required.
- Returns source and line ranges for retrieved passages.
- Limits file count and per-file size.
- Does not upload files or call a provider.

This is a transparent retrieval baseline, not semantic vector search. Provider-backed embeddings and persistent vector stores are optional adapters that must preserve document-level access controls. Treat retrieved text as untrusted data; it cannot override system policy.
