#!/usr/bin/env python3
"""Offline local Markdown link/fragment checks for README and current guides.

No HTTP calls or service mutations. Historical external evidence URLs remain
external references; this checks files and anchors against the actual checkout.
"""
import argparse
import html
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


def prose_lines(text):
    """Keep original line numbers while excluding fenced examples."""
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if match:
            marker, tail = match.groups()
            if fence is None:
                fence = marker
                continue
            if marker[0] == fence[0] and len(marker) >= len(fence) and not tail.strip():
                fence = None
                continue
        if fence is None:
            yield number, line


def anchors(text):
    """Explicit HTML anchors plus GitHub-style Unicode heading fragments."""
    found = set()
    seen = {}
    for _, line in prose_lines(text):
        found.update(html.unescape(value) for value in
                     re.findall(r'<a\s+(?:id|name)=["\']([^"\']+)["\']', line, re.I))
        heading = re.match(r'^ {0,3}#{1,6}\s+(.+?)(?:\s+#+)?\s*$', line)
        if heading:
            title = html.unescape(heading.group(1))
            title = re.sub(r'\[([^]]+)\]\([^)]+\)', r'\1', title)
            title = re.sub(r'<[^>]*>', '', title).lower()
            slug = re.sub(r'[^\w\- ]', '', title).replace(' ', '-')
            count = seen.get(slug, 0)
            seen[slug] = count + 1
            found.add(slug if not count else '{}-{}'.format(slug, count))
    return found


def local_links(text):
    """Inline links, reference definitions and HTML hrefs outside code."""
    for number, line in prose_lines(text):
        line = re.sub(r'(`+).*?\1', '', line)
        for match in re.finditer(r'\]\(\s*(?:<([^>]+)>|([^\s)]+))', line):
            yield number, html.unescape(match.group(1) or match.group(2))
        definition = re.match(r'^ {0,3}\[[^]]+\]:\s*<?([^\s>]+)>?', line)
        if definition:
            yield number, html.unescape(definition.group(1))
        for href in re.findall(r'\bhref=["\']([^"\']+)["\']', line, re.I):
            yield number, html.unescape(href)


def check_document(path, root=ROOT):
    root = root.resolve()
    path = path.resolve()
    text = path.read_text(encoding='utf-8')
    errors = []
    cache = {}
    for number, link in local_links(text):
        parsed = urlsplit(link)
        if parsed.scheme or parsed.netloc:
            continue
        target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
        label = '{}:{}: {}'.format(path.relative_to(root), number, link)
        try:
            target.relative_to(root)
        except ValueError:
            errors.append(label + ' escapes the repository')
            continue
        if not target.is_file():
            errors.append(label + ' points to a missing file')
            continue
        if parsed.fragment and target.suffix.lower() == '.md':
            if target not in cache:
                cache[target] = anchors(target.read_text(encoding='utf-8'))
            if unquote(parsed.fragment) not in cache[target]:
                errors.append(label + ' points to a missing anchor')
    return errors


def documentation(root=ROOT):
    return [root / 'README.md'] + sorted((root / 'docs').rglob('*.md'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    documents = documentation(args.root)
    errors = [error for path in documents for error in check_document(path, args.root)]
    if errors:
        for error in errors:
            print(error)
        print('DOCUMENT_LINKS=FAIL')
        return 1
    print('DOCUMENT_LINKS=PASS files={}'.format(len(documents)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
