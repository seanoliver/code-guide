# guide.json schema

The complete worked example is `examples/sealed-pr-11.json`, a PR guide for a public side project. Copy its shape.

```jsonc
{
  "title": "Return failed signup callbacks to signup",
  "question": "How does a failed signup magic link end up back on `/signup`?",  // the question this guide answers
  "mode": "pr",                                            // or "explore"
  "pr": { "repo": "sealed", "base": "514a1db^", "number": 11 },  // pr mode only; diff is base...HEAD; number shown in header
  "repos": { "sealed": "~/code/address-book" },            // repo key → checkout path
  "tldr": [ { "text": "A failed callback redirects to `/${flow}?error=1`.", "refs": ["h-fail", "l9"] } ],

  "files": [                                               // order = reading order
    { "id": "confirm", "repo": "sealed", "path": "src/app/auth/confirm/route.ts",
      "role": "Callback: verify or bounce",                // one line, shown on the tile
      "range": [1, 80] }                                   // optional; default is the whole file
  ],
  "nodes": [ { "id": "sb", "label": "Supabase Auth", "role": "Issues OTP, verifies token" } ],  // non-code endpoints

  "areas": [                                               // app structure; every file/node placed exactly once
    { "id": "repo", "label": "address-book/", "children": [
      { "id": "a-confirm", "label": "auth/confirm/", "files": ["confirm"] } ] },
    { "id": "ext", "label": "External", "external": true, "files": ["sb"] }
  ],

  "highlights": [
    { "id": "h-fail", "file": "confirm",
      "at": "return NextResponse.redirect(new URL(`/${flow}?error=1`",  // substring of the first line (or an int line number)
      "to": "request.url));",                              // optional last line; searched from `at` onward
      "nth": 1, "after": "export async function GET", "to_nth": 1,   // optional disambiguators
      "role": "core",                                      // core | supporting | plumbing | contract | test
      "flags": ["gotcha"],                                 // optional; "changed" is added automatically in pr mode
      "title": "Failure returns to the right page",        // 2-6 words
      "body": "Was hardcoded `/login?error=1`. A new user with an expired link now sees signup." }  // `code` renders as inline code
  ],

  "links": [
    { "id": "l8", "kind": "call",                          // call | data | http
      "label": "parses flow",                              // http: use "GET /path"
      "from": { "file": "confirm", "at": "const flow = parseAuthFlow(" },
      "to":   { "file": "flow", "at": "export function parseAuthFlow" } },
    { "id": "l13", "kind": "http", "label": "verifyOtp",
      "from": { "file": "confirm", "at": "supabase.auth.verifyOtp(" }, "to": { "node": "sb" } }
  ],

  "tour": [
    { "title": "Failure goes back to `/signup`", "body": "…",
      "focus": { "file": "confirm", "at": "return NextResponse.redirect(new URL(`/${flow}?error=1`" }, "links": ["l13"] }
  ]
}
```

## Anchor rules

- An anchor is a substring of **one line**. Multi-line strings never match. Anchor on the most distinctive single line.
- `at` + `nth`: the nth match in the file, or the nth after the `after` line when `after` is set.
- `to` + `to_nth`: the nth match **counting from the `at` line onward** (inclusive). It does not count across the whole file.
- An int works in place of a substring (`"at": 42`). Use one only when no line is distinctive.

## Roles (exactly one per highlight)

| Role | Meaning | Example |
|---|---|---|
| `core` | Does the thing being asked about | the fetch, the evaluation, the branch on the variant |
| `supporting` | Changes how the core path runs | guards, caching, ordering, overrides |
| `plumbing` | Passes things along, with no logic of its own | wrappers, context accessors, re-exports |
| `contract` | Types, schemas, API shapes | DTOs, generated API types, zod schemas |
| `test` | Tests that pin the behavior | spec files |

## Flags (zero or more)

- `gotcha`: behaves differently from what a reader would assume. Use it sparingly, about 1 in 5 highlights at most.
- `changed`: added automatically when a highlight overlaps lines changed in the PR diff.

In `pr` mode the Code and Snippets views show a merged diff: deleted lines appear in red, above the lines that replaced them, and added lines appear in green. The **Diff** button (key `d`) switches to the final file.

## Validation (build fails on any of these)

- An anchor isn't found, or it matches several lines with no `nth` or `after`
- A `to` line resolves before its `at` line
- A role, flag, or link kind isn't one of the allowed values
- A link, tour step, or TL;DR ref points to an unknown id
- A file or node isn't placed in any area
- A repo key is missing from `repos`, or a file doesn't exist
