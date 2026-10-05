---
name: code-guide
description: Use when the user wants to see or understand how code fits together visually, such as "make a guide for this PR", "walk me through this PR visually", "show me how X works in the codebase", "map out the code behind X", "code guide", "canvas of this flow", or wants a Linear-style guided review with zoom. Also use when a code-guide needs new files, callouts, or a correction.
---

# Code Guide

## Overview

This skill produces one self-contained HTML canvas that explains a problem space in a codebase.
- **Zoomed out**, it shows where the files sit in the app structure.
- **Zoomed in**, it shows complete, syntax-highlighted files with callouts, plus arrows between related lines in different files.

**Core principle: you write a spec, and the tool renders it.** You author `guide.json`. `build.py` reads the real files, resolves line anchors, computes the PR diff, validates, and renders with a fixed template that runs ELK auto-layout. Never hand-write HTML, coordinates, or line numbers for a guide.

## Modes

| Mode | Trigger | Scope comes from |
|---|---|---|
| `pr` | A PR, branch, or "review this diff" | `build.py --pr-files <repo> <base>`, plus the code each changed file calls or is called by |
| `explore` | "How does X work" or "where does X come from" | Tracing from the entry point the user names, across repos if the flow crosses them |

## Workflow

1. **Read first, in a worktree.** Never run `checkout`, `switch`, `stash`, or `reset` in the user's checkout. It may hold their in-progress branch. Instead, `git fetch origin`, then create a detached worktree in a temp directory (your session scratchpad, if the harness has one) and point `repos` at it:
   - `explore`: `git -C <repo> worktree add --detach <tmp>/cg-<repo> origin/<primary>`
   - `pr`: `gh pr checkout <n>` is **not allowed**. Use `git fetch origin pull/<n>/head:cg-pr-<n> && git -C <repo> worktree add --detach <tmp>/cg-pr-<n> cg-pr-<n>`, with `pr.base` set to `origin/<base>`. For a merged squash PR, worktree the merge commit and use base `<sha>^`.

   In `pr` mode, read the PR description (`gh pr view <n>`) and the diff before anything else.
2. **Trace the flow.** Start where the user's question starts (the consumer, or the changed line) and follow calls, context reads, and HTTP hops to where the behavior is decided. Stop at external services, and model those as `nodes`. Aim for 3–12 files. More than 15 means the question is too broad: split it or ask.
3. **Write `guide.json`** using the schema in `reference.md`. Rules:
   - Anchor lines by **substring** (`"at": "const flow = parseAuthFlow("`). Use `nth`, `after`, or `to_nth` when a substring repeats.
   - Assign each highlight exactly one **role**: `core`, `supporting`, `plumbing`, `contract`, or `test`. **Flags** are `gotcha` only. `changed` is computed automatically in `pr` mode.
   - Highlight the lines that matter. Leave everything else unhighlighted, and the renderer folds it.
   - **Write for a glance.** The canvas is scanned, not read. Hard limits, enforced by the build: TL;DR bullets ≤80 chars (max 5), file `role` ≤32, area labels ≤28, link labels ≤24, highlight titles ≤40 and bodies ≤160, tour bodies ≤140. When something runs over, cut words. Don't move them into another field.
   - Write each callout body as the *consequence* for a reader, in one plain sentence. Do not restate what the code says.
   - Make each callout title stand on its own. Code view shows callouts collapsed to their title until the reader clicks one open.
   - Wrap every identifier, file name, literal value, route, or code fragment in backticks: `` `parseAuthFlow` ``, `` `route.ts` ``, `` `'signup'` ``, `` `GET /auth/confirm` ``. This applies to titles, bodies, TL;DR bullets, tour text, and file roles. The renderer shows them as inline code. Backticks don't count toward the length limits.
   - Area labels are the folder name only (`lib/`). Leave out descriptions like "(shared by every app)", because the hover shows the full path.
   - Use `range` only for files where a small region is relevant inside a huge file (over 400 lines). Otherwise show the whole file.
   - Write 3–5 TL;DR bullets. Give each one `refs` to the highlight ids and link ids that prove it.
   - Write 4–9 tour steps in reading order. Each step focuses on one line and lists the links it crosses.
   - Build `areas` from the real directory structure, with the repo at the top level and folders nested inside.
4. **Build:** `python3 <skill-dir>/build.py <guide.json> -o <out.html>`, where `<skill-dir>` is this skill's folder (`${CLAUDE_SKILL_DIR}` in Claude Code). If it reports errors, fix the spec and rebuild. Never edit the generated HTML.
5. **Verify in a browser.** Serve the output directory over http (`python3 -m http.server --bind 127.0.0.1`) and open it with whatever browser automation you have (a Playwright MCP, or a headless Chromium script that waits for `window.__guide`). If you have none, open the file and ask the user to confirm. Check:
   - The console is clean.
   - Fit shows every area.
   - One tour step lands on its line.
   - Hovering one TL;DR bullet lights up its refs.

   Fix the spec for any wrong callout or broken flow.
6. **Deliver.** Give the user the HTML path and a System-level screenshot (send them as files if your harness can), and print the local URL. Then remove the worktree with `git worktree remove <path>`. The HTML embeds the code, so it still works afterwards.

## Output location

Write `guide.json` and `guide.html` together in `docs/guides/YYYY-MM-DD-<slug>/` at the project root. For a multi-repo hub, use the hub root. If there is no project, use a temp directory.

## Common mistakes

| Mistake | Fix |
|---|---|
| Writing HTML or tweaking the template for one guide | Change the spec. A template change is a skill change and must work for every guide |
| The render is blank or broken, so you write your own renderer | Stop and report the template bug. A one-off renderer gives up auto-layout, TL;DR hover, and the tour, and nobody else gets the fix |
| Guessing line numbers | Use substring anchors. The build fails on misses and ambiguity, by design |
| Highlighting half the file | The role of a highlight is "worth a reader's attention". Most lines stay unhighlighted |
| Callouts that narrate the code ("calls parseAuthFlow") | Say what it means: "Anything unknown falls back to `login`" |
| Every highlight is `core` | `core` is only the path that answers the question. The rest is supporting, plumbing, or contract |
| TL;DR bullets without refs | Every bullet must point at the code that proves it |

## Out of scope

- Writing or editing code, or posting PR review comments. Use `pr-review` for that
- Animated explainers of concepts with no code. Use `building-interactive-explainers`
- Hosting, publishing, or sharing guides outside the local machine
- Whole-repo architecture maps with no question attached
