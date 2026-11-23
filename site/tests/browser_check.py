"""Browser checks for a running docs preview, using headless Chromium over CDP.

Usage: python3 site/tests/browser_check.py http://127.0.0.1:PORT/ OUTDIR

Needs Chromium and the python3-websocket package. Checks legacy forwarding with
and without JavaScript, layout overflow, structure, keyboard focus and computed
contrast of interactive states in light and dark themes, and saves screenshots.
"""

import base64
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket

SITE = Path(__file__).resolve().parents[1]
PAGES = ["", "lookup/", "results/", "quickstart/", "builders/", "how-verification-works/",
         "api/", "support/", "troubleshooting/", "legacy/"]
DESKTOP = {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False}
MOBILE = {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True}


class Browser:
    def __init__(self):
        self.profile = tempfile.mkdtemp(prefix="docs-cdp-")
        self.port = 9333
        self.proc = subprocess.Popen(
            ["chromium", "--headless=new", f"--remote-debugging-port={self.port}",
             f"--user-data-dir={self.profile}", "--remote-allow-origins=*", "--no-first-run",
             "--disable-gpu", "--hide-scrollbars", "--force-color-profile=srgb", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/list"))
                target = next(p for p in pages if p["type"] == "page")
                break
            except Exception:
                time.sleep(0.1)
        self.ws = websocket.create_connection(target["webSocketDebuggerUrl"], suppress_origin=True)
        self.next_id = 0
        self.errors = []
        for domain in ("Page", "Runtime", "DOM", "CSS"):
            self.send(f"{domain}.enable")

    def send(self, method, params=None):
        self.next_id += 1
        self.ws.send(json.dumps({"id": self.next_id, "method": method, "params": params or {}}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get("method") == "Runtime.exceptionThrown":
                self.errors.append(message["params"]["exceptionDetails"].get("text", "exception"))
            if message.get("id") == self.next_id:
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error']}")
                return message.get("result", {})

    def js(self, expression):
        result = self.send("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True})
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"])
        return result["result"].get("value")

    def goto(self, url, settle=0.25):
        self.send("Page.navigate", {"url": url})
        last, stable = None, 0
        for _ in range(80):
            time.sleep(0.05)
            try:
                state = self.js("[document.readyState, location.href]")
            except Exception:
                continue
            if state and state[0] == "complete" and state[1] == last:
                stable += 1
                if stable >= 4:
                    break
            else:
                stable = 0
            last = state[1] if state else None
        time.sleep(settle)
        return self.js("location.href")

    def viewport(self, metrics, theme):
        self.send("Emulation.setDeviceMetricsOverride", metrics)
        self.send("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": theme}]})

    def screenshot(self, path, full=False):
        params = {"format": "png"}
        if full:
            size = self.js("[document.documentElement.scrollWidth, document.documentElement.scrollHeight]")
            params.update(captureBeyondViewport=True, clip={"x": 0, "y": 0, "width": size[0], "height": min(size[1], 6000), "scale": 1})
        data = self.send("Page.captureScreenshot", params)["data"]
        Path(path).write_bytes(base64.b64decode(data))

    def key(self, key, code, keycode, text=""):
        base = {"key": key, "code": code, "windowsVirtualKeyCode": keycode, "nativeVirtualKeyCode": keycode}
        self.send("Input.dispatchKeyEvent", {"type": "keyDown", **base, **({"text": text} if text else {})})
        self.send("Input.dispatchKeyEvent", {"type": "keyUp", **base})

    def force(self, selector, states):
        root = self.send("DOM.getDocument", {"depth": -1})["root"]["nodeId"]
        node = self.send("DOM.querySelector", {"nodeId": root, "selector": selector})["nodeId"]
        if not node:
            return False
        self.send("CSS.forcePseudoState", {"nodeId": node, "forcedPseudoClasses": states})
        return True

    def close(self):
        try:
            self.ws.close()
        finally:
            self.proc.terminate()
            self.proc.wait(5)
            shutil.rmtree(self.profile, ignore_errors=True)


CONTRAST_JS = r"""
(function(selector, outer) {
  const el = document.querySelector(selector);
  if (!el) return null;
  const parse = c => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return {r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1}; };
  const lum = c => { const f = v => { v/=255; return v<=0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); };
    return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
  const bgOf = node => { for (let n = node; n; n = n.parentElement) {
      const c = parse(getComputedStyle(n).backgroundColor); if (c && c.a > 0.5) return c; }
    return parse(getComputedStyle(document.body).backgroundColor); };
  const target = outer ? el.closest(outer) || el : el;
  const s = getComputedStyle(el), t = getComputedStyle(target);
  const bg = bgOf(el), around = bgOf(target.parentElement);
  const fg = parse(s.color);
  const size = parseFloat(s.fontSize), weight = parseInt(s.fontWeight, 10);
  const large = size >= 24 || (size >= 18.66 && weight >= 700);
  const out = {text: +ratio(fg, bg).toFixed(2), textMin: large ? 3 : 4.5,
    color: s.color, background: `rgb(${bg.r}, ${bg.g}, ${bg.b})`};
  if (s.textDecorationLine.includes('underline')) out.underline = +ratio(parse(s.textDecorationColor), bg).toFixed(2);
  if (t.outlineStyle !== 'none' && parseFloat(t.outlineWidth) > 0) {
    out.outline = +ratio(parse(t.outlineColor), around).toFixed(2); out.outlineWidth = t.outlineWidth; }
  if (t.borderTopStyle !== 'none' && parseFloat(t.borderTopWidth) > 0) out.border = +ratio(parse(t.borderTopColor), around).toFixed(2);
  if (s.borderLeftStyle !== 'none' && parseFloat(s.borderLeftWidth) >= 3) out.indicator = +ratio(parse(s.borderLeftColor), bgOf(el.parentElement)).toFixed(2);
  if (bg && around && (bg.r !== around.r || bg.g !== around.g || bg.b !== around.b)) out.fill = +ratio(bg, around).toFixed(2);
  return out;
})
"""

# (name, page, viewport, selector, outer element that carries hover/focus styles, states, role)
ELEMENTS = [
    ("Article link", "lookup/", "desktop", "main p a:not(.button)", None, "text"),
    ("Article link, external", "lookup/", "desktop", "main p a.external", None, "text"),
    ("Docs nav link", "lookup/", "desktop", ".nav-desktop a:not([aria-current])", None, "nav"),
    ("Docs nav current page", "lookup/", "desktop", ".nav-desktop a[aria-current='page']", None, "nav-current"),
    ("Header link", "lookup/", "desktop", ".site-links a", None, "nav"),
    ("Footer link", "lookup/", "desktop", ".site-footer a", None, "nav"),
    ("On this page link", "lookup/", "desktop", ".toc a", None, "nav"),
    ("Previous and next link", "lookup/", "desktop", ".pager a", None, "boxed"),
    ("Primary button", "", "desktop", ".button.primary", None, "primary"),
    ("Secondary button", "", "desktop", ".button:not(.primary)", None, "boxed"),
    ("Task card", "", "desktop", ".card h3 a", ".card", "boxed"),
    ("Skip link", "", "desktop", ".skip", None, "primary"),
    ("Code block", "lookup/", "desktop", "pre", None, "static"),
    ("Mobile menu", "lookup/", "mobile", ".nav-mobile summary", ".nav-mobile", "boxed"),
    ("On this page toggle", "lookup/", "mobile", ".toc-inline summary", ".toc-inline", "static"),
    ("Status: Verified", "support/", "desktop", ".status-ok", None, "badge"),
    ("Status: Unsupported", "support/", "desktop", ".status-bad", None, "badge"),
    ("Status: Unconfirmed", "support/", "desktop", ".status-warn", None, "badge"),
    ("Status: Historical", "support/", "desktop", ".status-neutral", None, "badge"),
]
STATES = {"default": [], "hover": ["hover"], "focus": ["focus", "focus-visible"], "active": ["active", "hover", "focus"]}


def contrast_checks(browser, base):
    rows, failures = [], []
    for theme in ("light", "dark"):
        for name, page, view, selector, outer, role in ELEMENTS:
            browser.viewport(MOBILE if view == "mobile" else DESKTOP, theme)
            browser.goto(base + page, settle=0.1)
            states = ["default"] if role in ("badge",) else list(STATES)
            for state in states:
                forced = STATES[state]
                for sel in filter(None, [selector, outer]):
                    browser.force(sel, forced)
                result = browser.js(f"{CONTRAST_JS}({json.dumps(selector)}, {json.dumps(outer)})")
                for sel in filter(None, [selector, outer]):
                    browser.force(sel, [])
                if result is None:
                    failures.append(f"{theme} {name}: element not found")
                    continue
                row = {"theme": theme, "element": name, "state": state, **result}
                problems = []
                if result["text"] < result["textMin"]:
                    problems.append(f"text {result['text']}")
                if state == "focus" and role != "static":
                    if "outline" not in result:
                        problems.append("no focus outline")
                    elif result["outline"] < 3:
                        problems.append(f"focus outline {result['outline']}")
                if state == "focus" and role == "static" and result.get("outline", 3) < 3:
                    problems.append(f"focus outline {result['outline']}")
                if role == "text" and result.get("underline", 0) < 3:
                    problems.append(f"underline {result.get('underline')}")
                if role == "boxed" and result.get("border", 0) < 3 and result.get("fill", 0) < 3:
                    problems.append(f"boundary {result.get('border')}")
                if role == "primary" and result.get("fill", 0) < 3:
                    problems.append(f"fill {result.get('fill')}")
                if role == "nav-current" and result.get("indicator", 0) < 3:
                    problems.append(f"current-page bar {result.get('indicator')}")
                row["result"] = "PASS" if not problems else "FAIL: " + ", ".join(problems)
                if problems:
                    failures.append(f"{theme} {name} {state}: {', '.join(problems)}")
                rows.append(row)
    return rows, failures


def expected_path(replacement):
    page, _, anchor = replacement.partition("#")
    path = "/" if page == "index" else f"/{page}/"
    return path + (f"#{anchor}" if anchor else "")


def legacy_checks(browser, base):
    origin = base.rstrip("/")
    with (SITE / "legacy-paths.tsv").open() as f:
        paths = list(csv.DictReader(f, delimiter="\t"))
    with (SITE / "legacy-anchors.tsv").open() as f:
        anchors = list(csv.DictReader(f, delimiter="\t"))
    cases = [(row["legacy_html"], "", expected_path(row["replacement"])) for row in paths]
    for row in anchors:
        for fragment in row["fragments"].split(","):
            cases.append((row["legacy_html"], fragment, expected_path(row["replacement"])))
    cases.append(("/tutorials/docker-verification", "unknown-old-heading", "/quickstart/"))
    cases.append(("/", "value-proposition", "/#value-proposition"))
    cases.append(("/", "benefits-of-smart-contract-source-code-visibility", "/#benefits-of-smart-contract-source-code-visibility"))
    results, failures = [], []
    browser.viewport(DESKTOP, "light")
    for legacy, fragment, expected in cases:
        url = origin + legacy + (f"#{fragment}" if fragment else "")
        final = browser.goto(url, settle=0.15)
        got = final.removeprefix(origin)
        target_ok = browser.js("(() => { const h = decodeURIComponent(location.hash.slice(1)); return !h || !!document.getElementById(h); })()")
        ok = got == expected and target_ok
        results.append({"mode": "JavaScript", "from": legacy + (f"#{fragment}" if fragment else ""), "to": got, "expected": expected, "ok": ok})
        if not ok:
            failures.append(f"JS redirect {legacy}#{fragment}: got {got}, expected {expected}, target {target_ok}")
    browser.send("Emulation.setScriptExecutionDisabled", {"value": True})
    for row in paths:
        expected = expected_path(row["replacement"])
        final = browser.goto(origin + row["legacy_html"], settle=0.6)
        got = final.removeprefix(origin)
        ok = got == expected
        results.append({"mode": "No JavaScript", "from": row["legacy_html"], "to": got, "expected": expected, "ok": ok})
        if not ok:
            failures.append(f"no-JS redirect {row['legacy_html']}: got {got}, expected {expected}")
    browser.send("Emulation.setScriptExecutionDisabled", {"value": False})
    return results, failures


STRUCTURE_JS = r"""
(() => {
  const issues = [];
  const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  if (document.documentElement.scrollWidth > window.innerWidth + 1) issues.push(`horizontal overflow ${document.documentElement.scrollWidth}px > ${window.innerWidth}px`);
  const h1 = [...document.querySelectorAll('h1')].filter(visible);
  if (h1.length !== 1) issues.push(`${h1.length} visible h1`);
  let last = 0;
  for (const h of document.querySelectorAll('main h1, main h2, main h3, main h4')) {
    const level = +h.tagName[1]; if (last && level > last + 1) issues.push(`heading jump ${last} to ${level}: ${h.textContent.trim()}`); last = level; }
  const ids = {}; for (const el of document.querySelectorAll('[id]')) { ids[el.id] = (ids[el.id] || 0) + 1; }
  for (const [id, n] of Object.entries(ids)) if (n > 1) issues.push(`duplicate id ${id}`);
  for (const img of document.images) { if (!img.hasAttribute('alt')) issues.push(`img without alt ${img.src}`); if (img.complete && img.naturalWidth === 0) issues.push(`broken img ${img.src}`); }
  for (const a of document.querySelectorAll('a')) if (visible(a) && !a.textContent.trim() && !a.getAttribute('aria-label') && !a.querySelector('img[alt]:not([alt=""])')) issues.push(`link without text ${a.href}`);
  const navs = [...document.querySelectorAll('nav')].filter(visible).map(n => n.getAttribute('aria-label') || (n.getAttribute('aria-labelledby') ? 'labelledby' : ''));
  if (navs.some(l => !l)) issues.push('unlabelled nav');
  if (new Set(navs).size !== navs.length) issues.push(`duplicate nav labels ${navs}`);
  if (!document.querySelector('main')) issues.push('no main');
  if (!document.documentElement.lang) issues.push('no lang');
  for (const el of document.querySelectorAll('pre')) if (el.scrollWidth > el.clientWidth && el.tabIndex < 0) issues.push('scrollable pre not focusable');
  const small = [];
  if (matchMedia('(pointer: coarse), (max-width: 46rem)').matches) {
    for (const el of document.querySelectorAll('.nav-mobile summary, .toc-inline summary, .button, .pager a, .site-links a')) {
      const r = el.getBoundingClientRect(); if (visible(el) && r.height < 24) small.push(`${el.textContent.trim()} ${Math.round(r.height)}px`); } }
  if (small.length) issues.push('small targets: ' + small.join('; '));
  if (innerWidth < 500) {
    const narrow = [...document.querySelectorAll('main td')].filter(td => visible(td) && td.getBoundingClientRect().width < 150);
    if (narrow.length) issues.push(`${narrow.length} table cells narrower than 150px`);
    const header = document.querySelector('.site-header').getBoundingClientRect().height;
    if (header > 72) issues.push(`header wraps to ${Math.round(header)}px`);
  }
  return {issues, middleDot: document.body.innerText.includes('·'), title: document.title};
})()
"""


def page_checks(browser, base, outdir):
    results, failures = [], []
    for theme in ("light", "dark"):
        for name, metrics in (("desktop", DESKTOP), ("mobile", MOBILE)):
            browser.viewport(metrics, theme)
            for page in PAGES:
                browser.errors.clear()
                browser.goto(base + page)
                check = browser.js(STRUCTURE_JS)
                slug = page.strip("/") or "overview"
                shot = outdir / f"{slug}-{name}-{theme}.png"
                browser.screenshot(shot)
                if name == "mobile" and page in ("", "lookup/", "support/"):
                    browser.screenshot(outdir / f"{slug}-{name}-{theme}-full.png", full=True)
                issues = check["issues"] + ([f"middle dot in text"] if check["middleDot"] else []) + browser.errors
                results.append({"page": "/" + page, "viewport": name, "theme": theme, "issues": issues, "screenshot": shot.name})
                failures += [f"/{page} {name} {theme}: {issue}" for issue in issues]
    return results, failures


FOCUS_JS = r"""
(() => { const el = document.activeElement; if (!el || el === document.body) return {tag: 'body'};
  const card = el.closest('.card'); const ring = getComputedStyle(card && CSS.supports('selector(:has(a))') ? card : el);
  return {tag: el.tagName.toLowerCase(), text: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40),
    href: el.getAttribute('href'), outline: ring.outlineStyle !== 'none' && parseFloat(ring.outlineWidth) >= 2,
    inView: (() => { const r = el.getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight; })()}; })()
"""


def keyboard_checks(browser, base):
    log, failures = [], []
    browser.viewport(DESKTOP, "light")
    browser.goto(base + "lookup/")
    for step in range(16):
        browser.key("Tab", "Tab", 9)
        focus = browser.js(FOCUS_JS)
        log.append({"step": step + 1, **focus})
        if not focus.get("outline"):
            failures.append(f"desktop Tab {step + 1}: no visible focus on {focus}")
        if not focus.get("inView"):
            failures.append(f"desktop Tab {step + 1}: focused element off screen {focus}")
    if log[0].get("text") != "Skip to content":
        failures.append(f"first Tab stop is not the skip link: {log[0]}")
    browser.goto(base + "lookup/")
    browser.key("Tab", "Tab", 9)
    browser.key("Enter", "Enter", 13, "\r")
    time.sleep(0.2)
    active = browser.js("document.activeElement.id")
    log.append({"step": "Enter on skip link", "active": active})
    if active != "main":
        failures.append(f"skip link moved focus to {active!r}, expected main")
    browser.viewport(MOBILE, "light")
    browser.goto(base + "lookup/")
    tabs_to_menu = None
    for step in range(8):
        browser.key("Tab", "Tab", 9)
        if browser.js("document.activeElement.matches('.nav-mobile summary')"):
            tabs_to_menu = step + 1
            break
    if tabs_to_menu is None:
        failures.append("mobile menu toggle not reachable by Tab")
    else:
        browser.key("Enter", "Enter", 13, "\r")
        opened = browser.js("document.querySelector('.nav-mobile').open")
        browser.key("Tab", "Tab", 9)
        first = browser.js(FOCUS_JS)
        browser.key("Tab", "Tab", 9, )
        browser.js("document.querySelector('.nav-mobile summary').focus()")
        browser.key(" ", "Space", 32, " ")
        closed = not browser.js("document.querySelector('.nav-mobile').open")
        log.append({"step": "mobile menu", "tabsToReach": tabs_to_menu, "enterOpens": opened,
                    "nextFocus": first.get("text"), "spaceCloses": closed})
        if not opened or not closed:
            failures.append(f"mobile menu keyboard toggle failed: open {opened}, close {closed}")
        if first.get("tag") != "a":
            failures.append(f"after opening the menu, Tab went to {first}")
    return log, failures


def main():
    base, outdir = sys.argv[1].rstrip("/") + "/", Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    browser = Browser()
    report, failures = {}, []
    try:
        for name, check in (("legacy", lambda: legacy_checks(browser, base)),
                            ("pages", lambda: page_checks(browser, base, outdir)),
                            ("contrast", lambda: contrast_checks(browser, base)),
                            ("keyboard", lambda: keyboard_checks(browser, base))):
            results, problems = check()
            report[name] = results
            failures += problems
            print(f"{name}: {len(results)} checks, {len(problems)} failures")
    finally:
        browser.close()
    report["failures"] = failures
    (outdir / "report.json").write_text(json.dumps(report, indent=2))
    for failure in failures:
        print("  FAIL " + failure)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
