#!/usr/bin/env python3
"""
Self-hosted GitHub stats card (stats.svg / stats-light.svg).

Public third-party stats services (github-readme-stats.vercel.app and
friends) get rate-limited or paused unpredictably. This pulls the same
numbers straight from the GitHub REST API and renders them in the same
terminal-card style as generate_projects.py, so the profile never shows
a broken image again.
"""
import json, math, os, sys, urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN", "")
USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "matheusjose04")

def gh(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {TOKEN}" if TOKEN else "",
        "User-Agent": "profile-stats",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)

def fetch_stats():
    profile = gh(f"https://api.github.com/users/{USER}")
    repos, page = [], 1
    while True:
        batch = gh(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}&type=owner")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    stars = sum(r.get("stargazers_count", 0) for r in repos)
    forks = sum(r.get("forks_count", 0) for r in repos)
    langs = {}
    for r in repos:
        if r.get("fork"):
            continue
        try:
            for lang, count in gh(r["languages_url"]).items():
                langs[lang] = langs.get(lang, 0) + count
        except Exception as e:
            print(f"warn: languages for {r.get('full_name')} failed: {e}", file=sys.stderr)

    return {
        "public_repos": profile.get("public_repos", len(repos)),
        "followers": profile.get("followers", 0),
        "stars": stars,
        "forks": forks,
        "languages": langs,
    }

# ---------------- themes (matches generate_projects.py) ----------------
THEMES = {
    "dark": {
        "BG": "#0D1117", "PANEL": "#0F1620", "PANEL_BAR": "#0B0F16",
        "CYAN": "#00D4FF", "VIOLET": "#BC13FE", "EMERALD": "#00FF88",
        "TEXT": "#E6EDF3", "MUTED": "#8B949E", "DIM": "#495566",
        "STROKE": "rgba(0,212,255,0.28)", "RING_BG": "rgba(139,148,158,0.15)",
    },
    "light": {
        "BG": "#FFFFFF", "PANEL": "#FFFFFF", "PANEL_BAR": "#F6F8FA",
        "CYAN": "#1F6FEB", "VIOLET": "#8250DF", "EMERALD": "#1A7F37",
        "TEXT": "#24292F", "MUTED": "#57606A", "DIM": "#94A3B8",
        "STROKE": "rgba(31,111,235,0.30)", "RING_BG": "rgba(100,116,139,0.20)",
    },
}

W, H = 1180, 220
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
THEME = THEMES["dark"]

def donut(languages, cx, cy, r):
    total = sum(languages.values()) or 1
    entries = sorted(languages.items(), key=lambda kv: -kv[1])[:4]
    other = total - sum(v for _, v in entries)
    if other > 0:
        entries.append(("Other", other))
    colors = [THEME["VIOLET"], THEME["CYAN"], THEME["EMERALD"], "#6366F1", "#64748B"]
    C = 2 * math.pi * r
    out, legend, offset = [], [], 0.0
    for i, (lang, v) in enumerate(entries):
        frac = v / total
        seg = frac * C
        col = colors[i % len(colors)]
        out.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="14" '
            f'stroke-dasharray="{seg:.2f} {C - seg:.2f}" stroke-dashoffset="{-offset:.2f}" '
            f'transform="rotate(-90 {cx} {cy})"/>'
        )
        legend.append((lang, frac, col))
        offset += seg
    return "".join(out), legend

def tile(x, y, w, h, label, value, accent):
    return (
        f'<g transform="translate({x},{y})">'
        f'<rect width="{w}" height="{h}" rx="10" fill="{THEME["PANEL"]}" stroke="{THEME["STROKE"]}"/>'
        f'<text x="18" y="30" font-size="11" letter-spacing="1.5" fill="{THEME["MUTED"]}">{label}</text>'
        f'<text x="18" y="{h-16}" font-size="26" font-weight="700" fill="{accent}">{value}</text>'
        f'</g>'
    )

def build(stats):
    repos, followers, stars, forks = stats["public_repos"], stats["followers"], stats["stars"], stats["forks"]
    langs = stats["languages"]
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         f'font-family="{FONT}" role="img" aria-label="GitHub stats">']
    s.append(f'<rect width="{W}" height="{H}" fill="{THEME["BG"]}"/>')
    s.append(f'<text x="7" y="20" font-size="11" letter-spacing="2" fill="{THEME["CYAN"]}">GITHUB.STATS</text>')
    s.append(f'<text x="140" y="20" font-size="10" fill="{THEME["DIM"]}">./stats.sh --self-hosted</text>')
    s.append(f'<line x1="5" y1="30" x2="{W-5}" y2="30" stroke="{THEME["STROKE"]}" stroke-width="1.5"/>')

    tw, th, gap, top = 265, 130, 14, 44
    s.append(tile(5,          top, tw, th, "PUBLIC REPOS", repos,    THEME["EMERALD"]))
    s.append(tile(5+ (tw+gap),top, tw, th, "STARS",        stars,    THEME["CYAN"]))
    s.append(tile(5+2*(tw+gap),top, tw, th, "FORKS",       forks,    THEME["VIOLET"]))
    s.append(tile(5+3*(tw+gap),top, tw, th, "FOLLOWERS",   followers,THEME["EMERALD"]))

    if langs:
        cx, cy, r = W - 138, top + th/2, 46
        segs, legend = donut(langs, cx, cy, r)
        s.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{THEME["RING_BG"]}" stroke-width="14"/>')
        s.append(segs)
        ly = cy - 24
        for lang, frac, col in legend[:4]:
            lx = cx - r - 150
            s.append(f'<circle cx="{lx}" cy="{ly}" r="4" fill="{col}"/>')
            s.append(f'<text x="{lx+10}" y="{ly+4}" font-size="11" fill="{THEME["MUTED"]}">{lang} {frac*100:.0f}%</text>')
            ly += 20

    s.append('</svg>')
    return "".join(s)

if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else "."
    data = fetch_stats()
    for theme, fname in (("dark", "stats.svg"), ("light", "stats-light.svg")):
        THEME = THEMES[theme]
        svg = build(data)
        path = os.path.join(outdir, fname)
        with open(path, "w") as f:
            f.write(svg)
        print(f"wrote {path}: {theme}, {len(svg)//1024}KB")
