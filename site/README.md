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

## Production

Build into a new or empty output directory. A production build includes the public canonical URLs, both sitemaps and an indexable robots file; do not promote the noindex preview.

```sh
python3 site/build.py --site-url https://docs.sourcescan.dev --out dist/release/public
python3 site/tests/check_site.py dist/release/public --expect-site-url https://docs.sourcescan.dev
cp site/deploy/vercel.json dist/release/
```

The Vercel upload root is `dist/release/`: the routing configuration sits beside `public/`, not inside it. The generated empty `.nojekyll` is not needed on Vercel and can be omitted from the upload after validation. Upload only the static output and routing configuration to the docs project, never the source checkout. Merging this repository does not itself publish a deployment.
