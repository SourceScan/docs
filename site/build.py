"""Render the Pages artifact from the Markdown and legacy route tables."""

import argparse
import csv
import json
import posixpath
import re
import shutil
from collections import namedtuple
from html import escape
from pathlib import Path
from string import Template
from urllib.parse import urlsplit
from xml.etree.ElementTree import Element, SubElement, indent, tostring

import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor


SOURCE = Path(__file__).resolve().parent
Page = namedtuple("Page", "label directory group")
# Navigation order. Each group label is shown in the sidebar; the singular form
# is shown above the page title.
PAGES = {
    "index": Page("Overview", "", "Start"),
    "lookup": Page("Look up a contract", "lookup", "Guides"),
    "results": Page("Read a result", "results", "Guides"),
    "quickstart": Page("Verify a Rust contract", "quickstart", "Guides"),
    "builders": Page("Choose a builder image", "builders", "Guides"),
    "how-verification-works": Page("How verification works", "how-verification-works", "Reference"),
    "api": Page("Registry and API", "api", "Reference"),
    "support": Page("Support status", "support", "Reference"),
    "troubleshooting": Page("Troubleshooting", "troubleshooting", "Help"),
    "legacy": Page("Legacy paths", "legacy", "Help"),
}
EYEBROW = {"Start": "", "Guides": "Guide", "Reference": "Reference", "Help": "Help"}
# Table cells whose whole content is one of these bold words render as a
# status label. The word stays readable in the Markdown and in the HTML.
STATUS = {
    "Verified": "ok", "Match": "ok",
    "Mismatch": "bad", "Unsupported": "bad",
    "Unconfirmed": "warn", "Unavailable": "warn", "Not verified": "warn", "Not deployed": "warn",
    "Historical": "neutral",
}


def relative(directory, path):
    return posixpath.relpath(path or ".", directory or ".")


def html_link(target, directory):
    page, separator, anchor = target.partition("#")
    return relative(directory, PAGES[page].directory).rstrip("/") + "/" + separator + anchor


def markdown_link(target, directory):
    page, separator, anchor = target.partition("#")
    return relative(directory, page + ".md") + separator + anchor


class PageLinks(Treeprocessor):
    def __init__(self, md, directory):
        super().__init__(md)
        self.directory = directory

    def run(self, root):
        for link in root.iter("a"):
            href = urlsplit(link.attrib["href"])
            page = href.path.removesuffix(".md")
            if not href.netloc and not href.scheme and href.path.endswith(".md") and page in PAGES:
                target = page + ("#" + href.fragment if href.fragment else "")
                link.set("href", html_link(target, self.directory))
            elif href.scheme in ("http", "https"):
                classes = link.get("class", "").split()
                link.set("class", " ".join(classes + ["external"]))
        for image in root.iter("img"):
            if image.attrib["src"].startswith("images/"):
                image.set("src", relative(self.directory, image.attrib["src"]))
                image.set("loading", "lazy")
        for cell in root.iter("td"):
            children = list(cell)
            if (len(children) == 1 and children[0].tag == "strong" and not (cell.text or "").strip()
                    and not (children[0].tail or "").strip() and children[0].text in STATUS):
                children[0].tag = "span"
                children[0].set("class", "status status-" + STATUS[children[0].text])
        for cards in root.iter("div"):
            if "cards" in cards.get("class", "").split():
                group_cards(cards)
        for table in list(root.iter("table")):
            stack_table(table)


def stack_table(table):
    """Label each cell with its column so narrow screens can stack rows.

    Explicit roles keep table semantics when CSS changes the display type."""
    table.set("class", "stack")
    table.set("role", "table")
    headers = []
    for section in table:
        section.set("role", "rowgroup")
        for row in section:
            row.set("role", "row")
            for index, cell in enumerate(row):
                if cell.tag == "th":
                    cell.set("role", "columnheader")
                    headers.append("".join(cell.itertext()).strip())
                else:
                    cell.set("role", "cell")
                    if index < len(headers) and headers[index]:
                        cell.set("data-label", headers[index])


def group_cards(container):
    """Wrap each h3 and the blocks after it in a card."""
    children = list(container)
    for child in children:
        container.remove(child)
    card = None
    for child in children:
        if child.tag == "h3":
            card = SubElement(container, "div", {"class": "card"})
        if card is None:
            container.append(child)
        else:
            card.append(child)


class RelativeLinks(Extension):
    def __init__(self, directory):
        self.directory = directory
        super().__init__()

    def extendMarkdown(self, md):
        md.treeprocessors.register(PageLinks(md, self.directory), "page_links", 1)


def rows(name):
    with (SOURCE / name).open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source, delimiter="\t"))


def write(out, relative_path, text):
    path = out / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def plain_markdown(raw):
    """Drop presentation-only syntax from the Markdown copy of a page."""
    lines = [line for line in raw.splitlines()
             if not re.fullmatch(r"\s*(<div [^>]*markdown[^>]*>|</div>|\{:[^}]*\})\s*", line)]
    text = "\n".join(lines) + "\n"
    text = re.sub(r"\{:[^}\n]*\}", "", text)
    return re.sub(r"\n{3,}", "\n\n", text)


def nav_html(page, directory, suffix):
    groups = {}
    for target, info in PAGES.items():
        groups.setdefault(info.group, []).append(target)
    parts = []
    for group, targets in groups.items():
        heading = f"nav-{group.lower()}-{suffix}"
        items = []
        for target in targets:
            current = ' aria-current="page"' if target == page else ""
            items.append(f'<li><a href="{html_link(target, directory)}"{current}>'
                         f"{escape(PAGES[target].label)}</a></li>")
        parts.append(f'<div class="nav-section"><p class="nav-group" id="{heading}">{group}</p>'
                     f'<ul aria-labelledby="{heading}">{"".join(items)}</ul></div>')
    return "".join(parts)


def toc_entries(tokens):
    for token in tokens:
        if token["level"] == 2:
            yield token
        yield from toc_entries(token["children"])


def toc_html(tokens):
    entries = list(toc_entries(tokens))
    if len(entries) < 2:
        return "", ""
    items = "".join(f'<li><a href="#{token["id"]}">{escape(token["name"])}</a></li>' for token in entries)
    side = f'<nav class="toc" aria-label="On this page"><p class="toc-title">On this page</p><ul>{items}</ul></nav>'
    inline = (f'<details class="toc-inline"><summary>On this page</summary>'
              f'<nav aria-label="On this page"><ul>{items}</ul></nav></details>')
    return side, inline


def pager_html(page, directory):
    order = list(PAGES)
    index = order.index(page)
    links = []
    if index > 0:
        previous = order[index - 1]
        links.append(f'<a class="pager-previous" href="{html_link(previous, directory)}">'
                     f'<span class="pager-label">Previous</span>{escape(PAGES[previous].label)}</a>')
    if index < len(order) - 1:
        following = order[index + 1]
        links.append(f'<a class="pager-next" href="{html_link(following, directory)}">'
                     f'<span class="pager-label">Next</span>{escape(PAGES[following].label)}</a>')
    return f'<nav class="pager" aria-label="Previous and next page">{"".join(links)}</nav>'


def description(raw):
    for block in raw.split("\n\n")[1:]:
        text = block.strip()
        if text and not text.startswith(("#", "<", "[", "|", "`", "-", "!", "{")):
            text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
            text = re.sub(r"[`*]", "", " ".join(text.split()))
            return text if len(text) <= 200 else text[:197].rsplit(" ", 1)[0] + "..."
    return ""


def build_pages(out, pages, site_url, noindex, analytics):
    template = Template((SOURCE / "page.html").read_text(encoding="utf-8"))
    analytics_head = (SOURCE / "analytics.html").read_text(encoding="utf-8") if analytics else ""
    for page, info in PAGES.items():
        raw = pages[page]
        directory = info.directory
        md = markdown.Markdown(extensions=[
            "fenced_code", "tables", "attr_list", "md_in_html", "toc", RelativeLinks(directory)])
        body = md.convert(raw)
        # Code blocks can scroll sideways, so keyboard users must be able to focus them.
        body = body.replace("<pre>", '<pre tabindex="0">')
        side_toc, inline_toc = toc_html(md.toc_tokens)
        if inline_toc:
            body = body.replace("</h1>", "</h1>" + inline_toc, 1)
        eyebrow = EYEBROW[info.group]
        head = []
        if site_url:
            head.append(f'  <link rel="canonical" href="{escape(site_url + "/" + (directory + "/" if directory else ""), quote=True)}">\n')
        if noindex:
            head.append('  <meta name="robots" content="noindex">\n')
        write(out, posixpath.join(directory, "index.html"), template.substitute(
            head_extra="".join(head) + analytics_head,
            title=escape(raw.splitlines()[0].removeprefix("# ")),
            description=escape(description(raw), quote=True),
            root=relative(directory, ""),
            raw=markdown_link(page, directory),
            nav_desktop=nav_html(page, directory, "d"),
            nav_mobile=nav_html(page, directory, "m"),
            current=escape(info.label),
            eyebrow=f'<p class="eyebrow">{eyebrow}</p>' if eyebrow else "",
            body=body,
            toc=side_toc,
            pager=pager_html(page, directory),
            layout="layout has-toc" if side_toc else "layout",
        ))
        write(out, page + ".md", plain_markdown(raw))


def build_aliases(out, site_url):
    source_anchors = rows("legacy-anchors.tsv")
    for row in rows("legacy-paths.tsv"):
        legacy_html = row["legacy_html"]
        legacy_md = row["legacy_markdown"].lstrip("/")
        replacement = row["replacement"]
        page = replacement.split("#")[0]
        label = escape(PAGES[page].label)
        directory = legacy_html.lstrip("/")
        target = escape(html_link(replacement, directory), quote=True)
        anchors = {
            fragment: html_link(anchor["replacement"], directory)
            for anchor in source_anchors if anchor["legacy_html"] == legacy_html
            for fragment in anchor["fragments"].split(",")
        }
        payload = escape(json.dumps(anchors), quote=True)
        script = escape(relative(directory, "assets/legacy.js"), quote=True)
        styles = escape(relative(directory, "assets/docs.css"), quote=True)
        canonical = ""
        if site_url:
            page_path, _, _ = replacement.partition("#")
            target_dir = PAGES[page_path].directory
            canonical = f'\n  <link rel="canonical" href="{escape(site_url + "/" + (target_dir + "/" if target_dir else ""), quote=True)}">'
        write(out, directory + "/index.html", f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">{canonical}
  <noscript><meta http-equiv="refresh" content="0; url={target}"></noscript>
  <title>SourceScan documentation moved</title>
  <link rel="stylesheet" href="{styles}">
  <script defer src="{script}"></script>
</head>
<body class="moved">
  <main id="main">
    <h1>SourceScan documentation moved</h1>
    <p>Continue to <a id="replacement" href="{target}" data-anchors="{payload}">{label}</a>.</p>
  </main>
</body>
</html>
""")
        md_directory = posixpath.dirname(legacy_md)
        md_target = markdown_link(replacement, md_directory)
        web_target = html_link(replacement, md_directory)
        write(out, legacy_md, f"# SourceScan documentation moved\n\n"
              f"Continue to [{label} in Markdown]({md_target}) or "
              f"[open the docs page]({web_target}).\n")


def build_indexes(out, pages, site_url, noindex):
    index = ["# SourceScan", "", "> Reproducible Rust contract verification for NEAR.", ""]
    for group in dict.fromkeys(info.group for info in PAGES.values()):
        index += [f"## {group}", ""]
        for page, info in PAGES.items():
            if info.group == group:
                url = f"{site_url}/{page}.md" if site_url else f"./{page}.md"
                index.append(f"- [{info.label}]({url})")
        index.append("")
    write(out, "llms.txt", "\n".join(index))
    write(out, "llms-full.txt", "\n\n---\n\n".join(plain_markdown(pages[page]) for page in PAGES))
    robots = "User-agent: *\nDisallow: /\n" if noindex else "User-agent: *\nAllow: /\n"
    if site_url:
        urls = Element("urlset", {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"})
        for info in PAGES.values():
            path = f"/{info.directory}/" if info.directory else "/"
            SubElement(SubElement(urls, "url"), "loc").text = site_url + path
        indent(urls)
        sitemap = tostring(urls, encoding="unicode", xml_declaration=True) + "\n"
        write(out, "sitemap.xml", sitemap)
        write(out, "sitemap-pages.xml", sitemap)
        if not noindex:
            robots += f"Sitemap: {site_url}/sitemap.xml\n"
    write(out, "robots.txt", robots)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=SOURCE.parent / "dist",
                        help="create an artifact in a new or empty directory")
    parser.add_argument("--site-url", default="",
                        help="public HTTPS base URL, including any path prefix; adds canonical links, "
                             "sitemaps and absolute links in llms.txt")
    parser.add_argument("--noindex", action="store_true",
                        help="for staging: robots.txt disallows all crawling and every page carries noindex")
    parser.add_argument("--analytics", action="store_true",
                        help="include Vercel Web Analytics on canonical production docs pages")
    args = parser.parse_args()
    site_url = args.site_url.rstrip("/")
    url = urlsplit(site_url)
    if site_url and (url.scheme != "https" or not url.hostname or url.query or url.fragment or url.username):
        parser.error("--site-url must be an HTTPS base URL without credentials, query or fragment")
    if args.analytics and (args.noindex or site_url != "https://docs.sourcescan.dev"):
        parser.error("--analytics requires an indexable https://docs.sourcescan.dev build")
    out = args.out.resolve()
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        parser.error("--out must be a new or empty directory")
    out.mkdir(parents=True, exist_ok=True)
    pages = {page: (SOURCE / "content" / (page + ".md")).read_text(encoding="utf-8")
             for page in PAGES}
    build_pages(out, pages, site_url, args.noindex, args.analytics)
    build_aliases(out, site_url)
    build_indexes(out, pages, site_url, args.noindex)
    shutil.copytree(SOURCE / "assets", out / "assets")
    shutil.copytree(SOURCE.parent / "images", out / "images")
    (out / ".nojekyll").touch()
    print(f"Wrote {len(PAGES)} docs pages and {len(rows('legacy-paths.tsv'))} legacy route pairs to {out}")


if __name__ == "__main__":
    main()
