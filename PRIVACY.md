# Privacy policy

Effective October 5, 2026. This policy covers the `code-guide` plugin and skill (https://github.com/seanoliver/code-guide), published by Sean Oliver.

`code-guide` has no server, accounts, analytics, or telemetry. The developer receives no data when you use it.

## Personal data collected

The developer collects none. Any personal data in your code, git history, or PR text (author names or emails, for example) stays in the guide files on your machine and goes to your model provider as described under Recipients.

## Data the skill handles on your machine

- Your agent reads source code, git history, and, in PR mode, the pull request description (through `gh pr view`) to write the guide.
- `build.py` reads files from your local checkout and runs `git diff` locally. It makes no network requests.
- The guide (`guide.json` and `guide.html`) is written to `docs/guides/` at your project root, or to a temp directory when there is no project. It embeds the code it shows.
- The skill also saves a screenshot of the guide to check that it renders.

## Purposes

Code and PR text are read only to build the guide you asked for.

## Recipients

- **The developer:** none.
- **Your model provider:** your agent sends code to the model you already use (for example, OpenAI for Codex or Anthropic for Claude Code), under that provider's terms.
- **CDNs:** when you open `guide.html`, your browser downloads elkjs from `cdn.jsdelivr.net` and highlight.js from `cdnjs.cloudflare.com`. No code or guide data is sent. The CDN operators receive standard request data such as your IP address and user agent.
- **Your git host:** the skill runs `git fetch origin` in both modes, and `gh pr view` in PR mode, with your existing credentials.

## Retention

- The developer retains nothing.
- Guide files and screenshots stay on your machine until you delete them.
- The skill removes its git worktree at the end of a run. In PR mode, the `cg-pr-<n>` branch it fetches stays in your repository until you delete it.
- Your model provider's retention follows its own policy.

## Your controls

- Delete a guide by deleting its folder under `docs/guides/`.
- Guides embed the code they show. Add `docs/guides/` to `.gitignore` to keep them out of commits.
- Delete a fetched PR branch with `git branch -D cg-pr-<n>`.
- Your agent's permission settings decide which commands run without asking.
- Uninstall the plugin to stop all use.

## Changes and contact

Changes to this policy are committed to https://github.com/seanoliver/code-guide, and its git history records every version. For questions, open an issue at https://github.com/seanoliver/code-guide/issues.
