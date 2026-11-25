# SourceScan docs

- Use Conventional Commits for commit messages, PR titles, and squash merges.
- Use **Why**, **Change**, and **Validation** sections by default in PR descriptions. Explain the reason, summarize what changed, and report what was actually checked. Reserve comments for decisions, blockers, and review replies.
- Edit articles in `site/content/`, not the generated HTML. Check version-sensitive commands and verification claims against the upstream release or commit they describe.
- For site changes, follow the [preview checks](site/README.md#preview) in a fresh development VM. When moving or renaming a page or heading, keep its old URL or anchor working and test it in the preview.
