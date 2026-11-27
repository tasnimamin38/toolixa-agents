# Web Scraper

A safe local-HTML extraction starter. It reads an HTML file from disk and extracts the title, meta description, headings, canonical URL, and links.

## Install

~~~powershell
python -m pip install -e ../../core
python -m pip install -r requirements.txt
~~~

## Run

~~~powershell
python main.py --file C:\path\to\saved-page.html --base-url https://example.org/page
~~~

The optional base URL is used only to resolve relative links. It is not fetched.

## Security boundary

This version does not make outbound HTTP requests, follow links, use browser automation, bypass access controls, or fetch private URLs. Network crawling is intentionally withheld until a transport can pin validated DNS results to the actual connection or use a separately enforced egress proxy. The local parser is suitable for saved HTML and test fixtures only.
