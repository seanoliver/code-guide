#!/usr/bin/env python3
"""Build a code-guide canvas from a guide.json spec.

    build.py guide.json [-o out.html] [--open]
    build.py --pr-files <repo-path> <base>     # list files changed vs base (scoping helper)

Lines are referenced by substring anchors and resolved against the files on disk,
so the rendered code is always the real code. Fails loudly on any bad reference.
"""
import argparse, json, os, re, subprocess, sys, webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
ROLES = {'core', 'supporting', 'plumbing', 'contract', 'test'}
FLAGS = {'gotcha'}  # 'changed' is computed, never authored
LINK_KINDS = {'call', 'data', 'http'}
# Hard length limits. The canvas is read at a glance; long text is what makes it an eye chart.
LIMITS = {'title': 60, 'question': 110, 'tldr': 80, 'file.role': 32, 'node.role': 40,
          'area.label': 28, 'highlight.title': 40, 'highlight.body': 160,
          'link.label': 24, 'tour.title': 40, 'tour.body': 140}
MAX_TLDR = 5
errors = []


def err(msg):
    errors.append(msg)


def git_diff(repo_dir, base, path):
    """Return (changed_new_lines:set, removed:[{after, old_start, lines}]) for one file.

    Each removed block holds every old line of its hunk and sits after new-file line `after`,
    so a merged view shows it directly above the lines that replaced it."""
    out = subprocess.run(['git', '-C', repo_dir, 'diff', '--unified=0', '--no-color', f'{base}...HEAD', '--', path],
                         capture_output=True, text=True)
    if out.returncode != 0:
        err(f'git diff failed for {path}: {out.stderr.strip()}')
        return set(), []
    changed, removed, cur = set(), [], None
    for line in out.stdout.split('\n'):
        m = re.match(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
        if m:
            old_start = int(m.group(1))
            new_start = int(m.group(3))
            new_n = int(m.group(4) if m.group(4) is not None else 1)
            changed.update(range(new_start, new_start + new_n))
            # a pure deletion (+N,0) names the line it follows; otherwise the block precedes new_start
            cur = {'after': new_start if new_n == 0 else new_start - 1, 'old_start': old_start, 'lines': []}
            removed.append(cur)
        elif cur and line.startswith('-') and not line.startswith('---'):
            cur['lines'].append(line[1:])
    removed = [dict(r, count=len(r['lines'])) for r in removed if r['lines']]
    return changed, removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec', nargs='?')
    ap.add_argument('-o', '--out')
    ap.add_argument('--open', action='store_true')
    ap.add_argument('--pr-files', nargs=2, metavar=('REPO', 'BASE'))
    a = ap.parse_args()

    if a.pr_files:
        repo, base = a.pr_files
        r = subprocess.run(['git', '-C', repo, 'diff', '--stat', f'{base}...HEAD'], capture_output=True, text=True)
        print(r.stdout or r.stderr)
        return
    if not a.spec:
        ap.error('spec is required')

    spec_path = os.path.abspath(a.spec)
    spec = json.load(open(spec_path))
    spec_dir = os.path.dirname(spec_path)
    repos = {k: os.path.expanduser(v) for k, v in spec.get('repos', {}).items()}
    mode = spec.get('mode', 'explore')
    pr = spec.get('pr') or {}

    files, src = [], {}
    for f in spec['files']:
        fid = f['id']
        if f.get('repo') not in repos:
            err(f"file {fid}: repo {f.get('repo')!r} not in spec.repos")
            continue
        full = os.path.join(repos[f['repo']], f['path'])
        if not os.path.exists(full):
            err(f'file {fid}: not found: {full}')
            continue
        lines = open(full, encoding='utf-8', errors='replace').read().split('\n')
        if lines and lines[-1] == '':
            lines.pop()
        start, end = f.get('range') or (1, len(lines))
        src[fid] = (lines, start, end)
        entry = {'id': fid, 'repo': f['repo'], 'path': f['path'], 'role': f.get('role', ''),
                 'startLine': start, 'totalLines': len(lines),
                 'code': '\n'.join(lines[start - 1:end]), 'changed': [], 'removed': []}
        if mode == 'pr' and f['repo'] == pr.get('repo'):
            changed, removed = git_diff(repos[f['repo']], pr['base'], f['path'])
            entry['changed'] = sorted(n for n in changed if start <= n <= end)
            entry['removed'] = [r for r in removed if start - 1 <= r['after'] <= end]
        files.append(entry)

    nodes = {n['id']: n for n in spec.get('nodes', [])}  # external, non-code nodes

    def resolve(fid, at, nth=None, after=None, ctx=''):
        """Anchor → 1-based line number. `at` is a substring or an int line number."""
        if fid not in src:
            err(f'{ctx}: unknown file {fid!r}')
            return None
        lines, start, end = src[fid]
        if isinstance(at, int):
            if not start <= at <= end:
                err(f'{ctx}: line {at} outside {fid} range {start}-{end}')
                return None
            return at
        lo = start
        if after is not None:
            lo = resolve(fid, after, ctx=ctx + ' (after)') or start
        hits = [i + 1 for i in range(lo - 1, end) if at in lines[i]]
        if not hits:
            err(f'{ctx}: anchor {at!r} not found in {fid}')
            return None
        if nth is None and len(hits) > 1:
            err(f'{ctx}: anchor {at!r} matches {len(hits)} lines in {fid} {hits[:8]}; add "nth" or "after"')
            return None
        n = nth or 1
        if n > len(hits):
            err(f'{ctx}: anchor {at!r} nth={n} but only {len(hits)} matches in {fid}')
            return None
        return hits[n - 1]

    def endpoint(e, ctx):
        if 'node' in e:
            if e['node'] not in nodes:
                err(f"{ctx}: unknown node {e['node']!r}")
            return {'node': e['node']}
        return {'file': e['file'], 'line': resolve(e['file'], e['at'], e.get('nth'), e.get('after'), ctx)}

    highlights = []
    for i, h in enumerate(spec.get('highlights', [])):
        ctx = f'highlight[{i}] {h.get("title", "")!r}'
        if h.get('role') not in ROLES:
            err(f"{ctx}: role {h.get('role')!r} not in {sorted(ROLES)}")
        bad = set(h.get('flags', [])) - FLAGS
        if bad:
            err(f'{ctx}: unknown flags {sorted(bad)} (allowed {sorted(FLAGS)}; "changed" is automatic)')
        a_ = resolve(h['file'], h['at'], h.get('nth'), h.get('after'), ctx)
        b_ = resolve(h['file'], h['to'], h.get('to_nth'), a_ if a_ else None, ctx + ' (to)') if 'to' in h else a_
        if a_ and b_ and b_ < a_:
            err(f'{ctx}: "to" resolves before "at" ({b_} < {a_})')
        highlights.append({'id': h.get('id'), 'file': h['file'], 'from': a_, 'to': b_, 'role': h.get('role'),
                           'flags': list(h.get('flags', [])), 'title': h['title'], 'body': h.get('body', '')})

    by_file = {f['id']: f for f in files}
    for h in highlights:
        f = by_file.get(h['file'])
        if f and h['from'] and any(h['from'] <= n <= h['to'] for n in f['changed']):
            h['flags'].append('changed')

    links, link_ids = [], set()
    for i, l in enumerate(spec.get('links', [])):
        ctx = f"link[{i}] {l.get('id', '')}"
        if l.get('kind') not in LINK_KINDS:
            err(f"{ctx}: kind {l.get('kind')!r} not in {sorted(LINK_KINDS)}")
        if l['id'] in link_ids:
            err(f'{ctx}: duplicate id')
        link_ids.add(l['id'])
        links.append({'id': l['id'], 'kind': l['kind'], 'label': l.get('label', ''),
                      'from': endpoint(l['from'], ctx + ' from'), 'to': endpoint(l['to'], ctx + ' to')})

    tour = []
    for i, t in enumerate(spec.get('tour', [])):
        ctx = f'tour[{i}] {t.get("title", "")!r}'
        for lid in t.get('links', []):
            if lid not in link_ids:
                err(f'{ctx}: unknown link {lid!r}')
        tour.append({'title': t['title'], 'body': t.get('body', ''),
                     'focus': endpoint(t['focus'], ctx), 'links': t.get('links', [])})

    ref_ids = {h['id'] for h in highlights if h.get('id')} | link_ids
    hl_ids = [h['id'] for h in highlights if h.get('id')]
    if len(hl_ids) != len(set(hl_ids)):
        err('duplicate highlight ids')
    tldr = []
    for i, t in enumerate(spec.get('tldr', [])):
        t = {'text': t, 'refs': []} if isinstance(t, str) else t
        for r in t.get('refs', []):
            if r not in ref_ids:
                err(f'tldr[{i}]: unknown ref {r!r} (must be a highlight id or link id)')
        tldr.append({'text': t['text'], 'refs': t.get('refs', [])})

    placed = set()

    def walk(areas, path):
        for ar in areas:
            for fid in ar.get('files', []):
                if fid not in by_file and fid not in nodes:
                    err(f"area {ar['id']}: unknown file/node {fid!r}")
                placed.add(fid)
            walk(ar.get('children', []), path + [ar['id']])
    walk(spec.get('areas', []), [])
    for fid in list(by_file) + list(nodes):
        if fid not in placed:
            err(f'{fid} is not placed in any area')

    def lim(key, text, ctx):
        n = len(text.replace('`', '')) if text else 0  # backticks mark inline code; they don't count
        if n > LIMITS[key]:
            err(f'{ctx}: {key} is {n} chars (max {LIMITS[key]}): {text[:50]!r}...')
        if text and text.count('`') % 2:
            err(f'{ctx}: {key} has an unclosed backtick: {text[:50]!r}')
    lim('title', spec.get('title'), 'spec')
    lim('question', spec.get('question'), 'spec')
    if len(tldr) > MAX_TLDR:
        err(f'tldr has {len(tldr)} bullets (max {MAX_TLDR})')
    for i, t in enumerate(tldr): lim('tldr', t['text'], f'tldr[{i}]')
    for f in spec['files']: lim('file.role', f.get('role'), f"file {f['id']}")
    for n in nodes.values(): lim('node.role', n.get('role'), f"node {n['id']}")
    def walk_lim(areas):
        for ar in areas:
            lim('area.label', ar.get('label'), f"area {ar['id']}")
            walk_lim(ar.get('children', []))
    walk_lim(spec.get('areas', []))
    for h in highlights:
        lim('highlight.title', h['title'], f"highlight {h.get('id') or h['title']!r}")
        lim('highlight.body', h['body'], f"highlight {h.get('id') or h['title']!r}")
    for l in links: lim('link.label', l['label'], f"link {l['id']}")
    for t in tour:
        lim('tour.title', t['title'], f"tour {t['title']!r}")
        lim('tour.body', t['body'], f"tour {t['title']!r}")

    if errors:
        print(f'code-guide: {len(errors)} error(s) in {a.spec}:', file=sys.stderr)
        for e in errors:
            print('  - ' + e, file=sys.stderr)
        sys.exit(1)

    data = {'meta': {k: spec.get(k) for k in ('title', 'question', 'mode')} | {'tldr': tldr, 'pr': pr or None},
            'files': files, 'nodes': list(nodes.values()), 'areas': spec.get('areas', []),
            'highlights': highlights, 'links': links, 'tour': tour}
    tpl = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    payload = json.dumps(data).replace('</', '<\\/')
    if '/*__GUIDE_DATA__*/' not in tpl:
        sys.exit('template.html is missing the /*__GUIDE_DATA__*/ placeholder')
    html = tpl.replace('/*__GUIDE_DATA__*/', f'window.GUIDE = {payload};')
    out = a.out or os.path.join(spec_dir, os.path.splitext(os.path.basename(spec_path))[0] + '.html')
    open(out, 'w', encoding='utf-8').write(html)
    n_lines = sum(f['code'].count('\n') + 1 for f in files)
    print(f'wrote {out}  ({len(files)} files, {n_lines} lines, {len(highlights)} highlights, {len(links)} links, {len(tour)} tour steps)')
    if a.open:
        webbrowser.open('file://' + os.path.abspath(out))


if __name__ == '__main__':
    main()
