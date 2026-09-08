#!/usr/bin/env python3
# Copyright 2026 INVITU (<https://www.invitu.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import sys
import json

try:
    import httpx
except ImportError:
    sys.stderr.write(
        "[web-browser] ERROR: 'httpx' not found. Install with: pip install httpx\n"
    )
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.stderr.write(
        "[web-browser] ERROR: 'beautifulsoup4' not found. Install with: pip install beautifulsoup4\n"
    )
    sys.exit(1)

_REMOVE_TAGS = {"script", "style", "nav", "footer", "header", "noscript", "iframe"}
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr,en;q=0.9",
}
_JS_THRESHOLD = 200


def log(msg):
    sys.stderr.write(f"[web-browser] {msg}\n")
    sys.stderr.flush()


def _extract(html: str, extract_links: bool) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    for tag in soup(_REMOVE_TAGS):
        tag.decompose()
    body = soup.find("main") or soup.find("article") or soup.find("body") or soup
    text = " ".join(body.get_text(" ", strip=True).split())
    links = []
    if extract_links:
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            label = a.get_text(strip=True)
            if href.startswith("http") and label:
                links.append({"url": href, "label": label})
    return {"title": title, "text": text, "links": links}


def web_fetch(url: str, extract_links: bool = False) -> dict:
    log(f"Fetching: {url}")
    try:
        with httpx.Client(
            headers=_HEADERS, follow_redirects=True, timeout=15
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except httpx.TimeoutException:
        return {"isError": True, "content": f"Timeout fetching {url}"}
    except httpx.HTTPStatusError as e:
        return {"isError": True, "content": f"HTTP {e.response.status_code}: {url}"}
    except Exception as e:
        return {"isError": True, "content": f"Request error: {e}"}

    content_type = resp.headers.get("content-type", "")
    if "text/html" not in content_type and "text/plain" not in content_type:
        return {
            "isError": True,
            "content": f"Unsupported content type: {content_type}",
        }

    extracted = _extract(resp.text, extract_links)
    text = extracted["text"]
    is_dynamic = len(text) < _JS_THRESHOLD

    result = {
        "url": str(resp.url),
        "title": extracted["title"],
        "text": text[:20000],
        "truncated": len(text) > 20000,
    }
    if extract_links:
        result["links"] = extracted["links"][:100]
    if is_dynamic:
        result["warning"] = (
            "Very little text extracted — this page may require JavaScript rendering. "
            "Consider using a browser-based approach for dynamic content."
        )
    return result


def build_tools():
    return [
        {
            "name": "web_fetch",
            "description": (
                "Fetch a web page and extract its text content. "
                "Works for static HTML pages. "
                "Returns title, clean text, and optionally links. "
                "If the page relies heavily on JavaScript, a warning is included. "
                "Use for: reading articles, extracting contact info from directories, "
                "scraping public data, reading documentation."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full URL to fetch (must start with http:// or https://)",
                    },
                    "extract_links": {
                        "type": "boolean",
                        "description": "If true, also return all hyperlinks found on the page.",
                    },
                },
                "required": ["url"],
            },
        },
    ]


def handle_request(request: dict) -> dict | None:
    method = request.get("method")
    req_id = request.get("id")

    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "web-browser-mcp", "version": "1.0.0"},
        }
    elif method == "tools/list":
        result = {"tools": build_tools()}
    elif method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name == "web_fetch":
            url = args.get("url", "").strip()
            if not url:
                res = {"isError": True, "content": "'url' is required"}
            elif not url.startswith(("http://", "https://")):
                res = {"isError": True, "content": "URL must start with http:// or https://"}
            else:
                res = web_fetch(url, args.get("extract_links", False))
                if not res.get("isError"):
                    res = {"content": json.dumps(res, ensure_ascii=False)}
                else:
                    res = {"isError": True, "content": res.get("content", "Unknown error")}
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }

        result = {
            "content": [{"type": "text", "text": res.get("content", "")}],
            "isError": res.get("isError", False),
        }
    elif method == "notifications/initialized":
        return None
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"},
        }

    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def main():
    log("Web Browser MCP server v1.0 started")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError as e:
            log(f"Invalid JSON: {e}")
        except Exception as e:
            log(f"Unhandled error: {e}")


if __name__ == "__main__":
    main()
