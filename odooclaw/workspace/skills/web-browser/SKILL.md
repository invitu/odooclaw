---
name: web-browser
description: Fetch and extract text content from public web pages (directories, articles, documentation). Use web_fetch when the user asks to read, scrape or extract information from a URL.
homepage: https://github.com/nicolasramos/odooclaw
metadata: {"openclaw":{"emoji":"🌐"}}
---

# Web Browser Skill

## Overview

Fetches public web pages and extracts clean text content using HTTP.
Works for static HTML pages. Pages that require JavaScript rendering may return limited content (a warning is included in the response).

## Tools

### web_fetch

Fetches a URL and returns the page title, extracted text, and optionally all hyperlinks.

**Parameters:**
- `url` (required): Full URL starting with `http://` or `https://`
- `extract_links` (optional): Return all hyperlinks found on the page

**Returns:**
- `title`: Page title
- `text`: Clean extracted text (up to 20,000 chars)
- `truncated`: Whether the text was truncated
- `links`: List of `{url, label}` pairs (if `extract_links=true`)
- `warning`: Present if the page likely requires JavaScript

## Usage Examples

**Extracting contacts from a directory:**
```json
{"name": "web_fetch", "arguments": {"url": "https://annuaire.example.com/contacts", "extract_links": false}}
```

**Reading an article:**
```json
{"name": "web_fetch", "arguments": {"url": "https://example.com/article"}}
```

## Limitations

- Static HTML only — JavaScript-rendered pages return limited content
- Maximum 20,000 characters of extracted text
- Public pages only — no authentication support
