const assert = require("node:assert/strict");
const { readFileSync, readdirSync } = require("node:fs");
const { join } = require("node:path");
const { test } = require("node:test");
const { runInNewContext } = require("node:vm");

const [production, preview] = process.argv.slice(2);
assert(production && preview, "Usage: node site/tests/check_vercel.cjs PROD PREVIEW");
const endpoint = "/_vercel/insights/script.js";

test("Git builds keep the manual upload's routing and Markdown headers", () => {
  const { installCommand, buildCommand, outputDirectory, ...routing } = require("../../vercel.json");
  const expected = { ...require("../deploy/vercel.json") };
  delete expected.installCommand;
  delete expected.buildCommand;
  delete expected.outputDirectory;
  assert.deepEqual(routing, expected);
});

test("only current production HTML pages have analytics", () => {
  for (const directory of [production, preview]) {
    for (const file of readdirSync(directory, { recursive: true }).filter(file => file.endsWith(".html"))) {
      const html = readFileSync(join(directory, file), "utf8");
      const enabled = directory === production && file !== "404.html" && !html.includes('id="replacement"');
      assert.equal(html.split(endpoint).length - 1, Number(enabled), `${directory}/${file}`);
    }
  }
});

const page = readFileSync(join(production, "quickstart", "index.html"), "utf8");
const canonical = page.match(/<link rel="canonical" href="([^"]+)"/)?.[1];
const bootstrap = page.match(/<script>([\s\S]*?)<\/script>/)?.[1];

function loadAnalytics(url, referrer = "") {
  assert(canonical, "Production quickstart is missing its canonical URL");
  assert(bootstrap, "Production quickstart is missing the Vercel Web Analytics bootstrap");
  const loaded = [];
  const window = {};
  const document = {
    referrer,
    querySelector: () => ({ href: canonical }),
    createElement: tag => ({ tag }),
    head: { append: script => loaded.push(script) },
  };
  runInNewContext(bootstrap, { URL, location: new URL(url), document, window });
  return { loaded, queue: window.vaq };
}

test("analytics sends only canonical page views without query, fragment or custom data", () => {
  assert(page.includes('<meta name="referrer" content="origin">'));
  const url = canonical + "?account=private#fragment";
  const { loaded, queue } = loadAnalytics(url, "https://referrer.example/");
  assert.deepEqual(loaded, [{ tag: "script", src: endpoint }]);
  assert.equal(queue.length, 1);
  const [[command, beforeSend]] = queue;
  assert.equal(command, "beforeSend");
  assert.deepEqual({ ...beforeSend({ type: "pageview", url, payload: { id: "private" } }) },
    { type: "pageview", url: canonical });
  assert.equal(beforeSend({ type: "event", url }), null);
  assert.equal(beforeSend({ type: "pageview", url: canonical + "account-id/" }), null);
  assert.equal(beforeSend({ type: "pageview", url: "https://other.example/quickstart/" }), null);
});

test("analytics skips alternate hosts and incoming referrers containing a path or query", () => {
  for (const [url, referrer] of [
    ["https://docs-preview.vercel.app/quickstart/", ""],
    [canonical, "https://referrer.example/accounts/private"],
    [canonical, "https://referrer.example/?account=private"],
  ]) {
    assert.deepEqual(loadAnalytics(url, referrer), { loaded: [], queue: undefined });
  }
});
