"""Check a built docs artifact: internal links, fragments and the legacy routes.

Usage: python3 site/tests/check_site.py DIST [--base http://127.0.0.1:PORT/]

Static checks read DIST only. With --base, every current page and all legacy
HTML and Markdown routes are also requested from a running server.
"""

import argparse
import csv
import posixpath
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

SITE = Path(__file__).resolve().parents[1]
BANNED = {"·": "middle dot"}


class Collect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links = set(), []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        for key in ("href", "src"):
            if key in attrs and tag in ("a", "link", "img", "script"):
                self.links.append((tag, attrs[key]))


def rows(name):
    with (SITE / name).open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source, delimiter="\t"))


def url_path(dist, file):
    rel = file.relative_to(dist).as_posix()
    return "/" + (rel[: -len("index.html")] if rel.endswith("index.html") else rel)


def resolve(dist, path):
    """Map a site path to a file, the way a static host would."""
    target = dist / unquote(path).lstrip("/")
    if path.endswith("/"):
        target = target / "index.html"
    elif target.is_dir():
        target = target / "index.html"
    return target if target.is_file() else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dist", type=Path)
    parser.add_argument("--base")
    parser.add_argument("--expect-noindex", action="store_true",
                        help="require robots.txt to disallow crawling and every page to carry noindex")
    parser.add_argument("--expect-site-url", default="",
                        help="require canonical links and sitemaps for this public base URL")
    args = parser.parse_args()
    dist = args.dist.resolve()
    site_url = args.expect_site_url.rstrip("/")
    site_path = urlsplit(site_url).path
    failures, checked = [], {"internal targets": set(), "fragments": 0}
    parsed = {}

    def page(file):
        if file not in parsed:
            collector = Collect()
            collector.feed(file.read_text(encoding="utf-8"))
            parsed[file] = collector
        return parsed[file]

    html_files = sorted(dist.rglob("*.html"))
    md_files = sorted(dist.rglob("*.md"))

    def check_target(source, base_path, href):
        parts = urlsplit(href)
        if parts.scheme or parts.netloc or href.startswith(("mailto:", "data:")):
            return
        if parts.path:
            path = posixpath.normpath(urljoin(base_path, parts.path))
            if site_path and parts.path.startswith(site_path + "/"):
                path = path.removeprefix(site_path) or "/"
            if parts.path.endswith("/") and not path.endswith("/"):
                path += "/"
        else:
            path = base_path
        target = resolve(dist, path)
        checked["internal targets"].add(path + ("#" + parts.fragment if parts.fragment else ""))
        if target is None:
            failures.append(f"{source}: missing target {href}")
            return
        if parts.fragment:
            checked["fragments"] += 1
            html = target
            if target.suffix == ".md":
                # A Markdown fragment refers to the heading on the rendered page.
                stem = target.relative_to(dist).with_suffix("").as_posix()
                html = dist / ("" if stem == "index" else stem) / "index.html"
            if html.suffix == ".html" and unquote(parts.fragment) not in page(html).ids:
                failures.append(f"{source}: missing fragment #{parts.fragment} in {html.relative_to(dist)}")

    for file in html_files:
        base_path = url_path(dist, file)
        for _, href in page(file).links:
            check_target(file.relative_to(dist), base_path, href)
    for file in md_files:
        base_path = url_path(dist, file)
        text = file.read_text(encoding="utf-8")
        for href in re.findall(r"\]\(([^)\s]+)\)", text):
            check_target(file.relative_to(dist), base_path, href)

    for file in dist.rglob("*"):
        if file.is_file() and file.suffix in (".html", ".md", ".txt", ".css", ".js", ".xml"):
            text = file.read_text(encoding="utf-8")
            for char, name in BANNED.items():
                if char in text:
                    failures.append(f"{file.relative_to(dist)}: contains {name}")

    # Artifact hygiene: only publishable files, no local paths or scratch output.
    allowed = {".html", ".md", ".txt", ".css", ".js", ".png", ".xml"}
    for file in dist.rglob("*"):
        rel = file.relative_to(dist).as_posix()
        if file.is_dir():
            if file.name in ("__pycache__", "tests", "qa", "site", ".git"):
                failures.append(f"unexpected directory: {rel}")
            continue
        if file.name == ".nojekyll":
            continue
        if file.name.startswith(".") or file.suffix not in allowed:
            failures.append(f"unexpected file: {rel}")
        if file.suffix in (".html", ".md", ".txt", ".css", ".js", ".xml"):
            text = file.read_text(encoding="utf-8")
            for needle in ("127.0.0.1", "localhost", "/Users/", "/private/", "/tmp/", "/home/", "scratchpad"):
                if needle in text:
                    failures.append(f"{rel}: contains local reference {needle!r}")
    if not (dist / ".nojekyll").is_file():
        failures.append("missing .nojekyll")
    not_found = dist / "404.html"
    if not_found not in html_files:
        failures.append("missing 404.html")
    else:
        links = page(not_found).links
        if ("a", site_path + "/") not in links or ("link", site_path + "/assets/docs.css") not in links:
            failures.append("404.html must link to the docs index and stylesheet with root-relative URLs")
        if '<meta name="robots" content="noindex">' not in not_found.read_text(encoding="utf-8"):
            failures.append("404.html: missing noindex")
    robots = (dist / "robots.txt").read_text(encoding="utf-8")
    current_pages = [f for f in html_files
                     if f != not_found and 'id="replacement"' not in f.read_text(encoding="utf-8")]
    if args.expect_noindex:
        if "Disallow: /" not in robots or "Sitemap:" in robots:
            failures.append("robots.txt does not disallow all crawling")
        for f in current_pages:
            if '<meta name="robots" content="noindex">' not in f.read_text(encoding="utf-8"):
                failures.append(f"{f.relative_to(dist)}: missing noindex")
    elif "Disallow: /" in robots:
        failures.append("robots.txt disallows crawling in an indexable build")
    for f in current_pages:
        text = f.read_text(encoding="utf-8")
        canonical = re.findall(r'<link rel="canonical" href="([^"]+)">', text)
        if site_url:
            expected = site_url + url_path(dist, f)
            if canonical != [expected]:
                failures.append(f"{f.relative_to(dist)}: canonical {canonical}, expected {expected}")
        elif canonical:
            failures.append(f"{f.relative_to(dist)}: canonical present without a site URL")
    if site_url:
        for name in ("sitemap.xml", "sitemap-pages.xml"):
            sitemap = dist / name
            locs = re.findall(r"<loc>([^<]+)</loc>", sitemap.read_text(encoding="utf-8")) if sitemap.is_file() else []
            if sorted(locs) != sorted(site_url + url_path(dist, f) for f in current_pages):
                failures.append(f"{name} does not list exactly the current pages")
    checked["current pages"] = len(current_pages)

    legacy = rows("legacy-paths.tsv")
    anchors = rows("legacy-anchors.tsv")
    route_results = []
    for row in legacy:
        alias = resolve(dist, row["legacy_html"] + "/")
        md = row["legacy_markdown"]
        if alias is None:
            failures.append(f"legacy HTML missing: {row['legacy_html']}")
        if md and not (dist / md.lstrip("/")).is_file():
            failures.append(f"legacy Markdown missing: {md}")
        page_name, _, fragment = row["replacement"].partition("#")
        target = dist / ("" if page_name == "index" else page_name) / "index.html"
        if not target.is_file() or (fragment and fragment not in page(target).ids):
            failures.append(f"legacy replacement missing: {row['replacement']}")
    for row in anchors:
        page_name, _, fragment = row["replacement"].partition("#")
        target = dist / ("" if page_name == "index" else page_name) / "index.html"
        if not target.is_file() or (fragment and fragment not in page(target).ids):
            failures.append(f"legacy anchor replacement missing: {row['replacement']}")

    widget_path = "/introduction/sourcescan/"
    widget_alias = resolve(dist, widget_path)
    if widget_alias is None or not any(tag == "a" and urljoin(widget_path, href) == "/"
                                      for tag, href in page(widget_alias).links):
        failures.append(f"{widget_path} must link to the docs homepage")

    if args.base:
        base = args.base.rstrip("/")

        def get(path):
            request = urllib.request.Request(base + path, headers={"User-Agent": "docs-check"})
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    return response.status, response.headers.get_content_type(), response.read().decode("utf-8"), response.url
            except urllib.error.HTTPError as error:
                return error.code, "", "", base + path

        current = ["/"] + [f"/{p.relative_to(dist).parent.as_posix()}/" for p in dist.glob("*/index.html")
                           if (dist / p.relative_to(dist).parent.as_posix()).with_suffix(".md").exists()]
        for path in current + ["/404.html", "/llms.txt", "/llms-full.txt", "/robots.txt"]:
            status, _, _, _ = get(path)
            if status != 200:
                failures.append(f"HTTP {status}: {path}")
        for row in legacy:
            status, kind, body, final = get(row["legacy_html"])
            ok = status == 200 and 'id="replacement"' in body
            route_results.append((row["legacy_html"], status, urlsplit(final).path, ok))
            if not ok:
                failures.append(f"legacy HTML route failed: {row['legacy_html']} -> {status}")
            md = row["legacy_markdown"]
            if not md:
                continue
            status, kind, body, final = get(md)
            ok = status == 200 and "documentation moved" in body
            route_results.append((md, status, kind, ok))
            if not ok:
                failures.append(f"legacy Markdown route failed: {md} -> {status}")

    print(f"HTML files: {len(html_files)}  Markdown files: {len(md_files)}")
    print(f"Distinct internal link targets: {len(checked['internal targets'])}  fragment checks: {checked['fragments']}")
    print(f"Legacy HTML routes: {len(legacy)}  legacy fragment rows: {len(anchors)}  current pages: {checked['current pages']}")
    print(f"Mode: {'noindex' if args.expect_noindex else 'indexable'}, site URL: {site_url or 'none (relative only)'}")
    if route_results:
        passed = sum(1 for result in route_results if result[3])
        print(f"Legacy routes requested over HTTP: {len(route_results)}  passed: {passed}")
        for path, status, detail, ok in route_results:
            print(f"  {'PASS' if ok else 'FAIL'} {status} {path} [{detail}]")
    if failures:
        print(f"\n{len(failures)} failures:")
        for failure in failures:
            print("  " + failure)
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
