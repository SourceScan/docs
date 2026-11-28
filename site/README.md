# Maintaining the SourceScan docs

Edit the articles in [content/](content/). The generator renders them as HTML and Markdown and writes discovery files for crawlers. [legacy-paths.tsv](legacy-paths.tsv) and [legacy-anchors.tsv](legacy-anchors.tsv) preserve links from the former docs site.

## Preview

Use Python 3.9 or later with the Markdown version pinned in [requirements.txt](requirements.txt). Run these commands from the repository root in an isolated development environment:

```sh
python3 site/build.py --noindex --out dist/preview
python3 site/tests/check_site.py dist/preview --expect-noindex
python3 -m http.server 8000 --bind 127.0.0.1 --directory dist/preview
```

With the server running, check HTTP routes, then run the browser suite in a second terminal. The browser suite also needs Chromium and the Python `websocket-client` module.

```sh
python3 site/tests/check_site.py dist/preview --expect-noindex --base http://127.0.0.1:8000/
python3 site/tests/browser_check.py http://127.0.0.1:8000/ dist/browser-report
```

## Vercel Git builds

The root [vercel.json](../vercel.json) installs the pinned renderer in a virtual environment and publishes `dist/vercel`. With Vercel system environment variables enabled, `VERCEL_ENV=production` adds the public canonical URLs, both sitemaps and Vercel Web Analytics. Other builds block indexing and omit analytics. Enable Web Analytics in the docs project before the production deployment. The analytics bootstrap runs on `https://docs.sourcescan.dev` and sends canonical page views with origin-only referrers.

Run `node site/tests/check_vercel.cjs PROD PREVIEW` with the production and preview output directories to check the routing config and analytics behavior offline.

## Manual production upload

Build into a new or empty output directory. Use `--analytics` to include Vercel Web Analytics alongside the public canonical URLs, both sitemaps and an indexable robots file.

```sh
python3 site/build.py --site-url https://docs.sourcescan.dev --analytics --out dist/release/public
python3 site/tests/check_site.py dist/release/public --expect-site-url https://docs.sourcescan.dev
cp site/deploy/vercel.json dist/release/
```

Use `dist/release/` as the Vercel upload root, with the routing configuration beside `public/`. The generated empty `.nojekyll` can be omitted after validation. Upload only the static output and routing configuration to the docs project.
