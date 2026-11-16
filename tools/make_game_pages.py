#!/usr/bin/env python3
"""Writes one landing page per game, <slug>/index.html, from games.json.

Each page is a plain, fast page for search engines and for sharing (title,
description, OpenGraph and Twitter tags with a screenshot), and it holds the
"Add to SideStore / Add to AltStore" buttons that GitHub itself can't show
(it drops sidestore:// and altstore:// links from Markdown). A README can link
to https://sithewok13-dev.github.io/<slug>/#add-sidestore (or #add-altstore)
to open that app's "add source" screen straight away.

It also writes sitemap.xml. No game data, logos or official artwork: the
pictures are the ports' own screenshots, linked from their repos.

Run: python3 tools/make_game_pages.py
"""
import html
import json
import os
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://sithewok13-dev.github.io"

STYLE = """
  :root { --bg: #ffffff; --fg: #1d1d1f; --muted: #5f5f66; --accent: #8e3aa8; --on-accent: #ffffff; --line: #d9d9de; --code: #f2f2f5; --card: #f6f6f8; --note: #fff6dc; --note-line: #e8d38f; }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) { --bg: #141416; --fg: #f2f2f5; --muted: #a8a8b0; --accent: #c77ddf; --on-accent: #141416; --line: #34343a; --code: #232327; --card: #1d1d21; --note: #2c2617; --note-line: #5c4d22; }
  }
  :root[data-theme="dark"] { --bg: #141416; --fg: #f2f2f5; --muted: #a8a8b0; --accent: #c77ddf; --on-accent: #141416; --line: #34343a; --code: #232327; --card: #1d1d21; --note: #2c2617; --note-line: #5c4d22; }
  body { margin: 0; background: var(--bg); color: var(--fg); font: 17px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  main { max-width: 760px; margin: 0 auto; padding: 24px 16px 48px; }
  nav { font-size: 0.9em; margin-bottom: 12px; }
  h1 { font-size: 1.6em; line-height: 1.2; margin: 0 0 8px; }
  h2 { font-size: 1.15em; margin: 28px 0 8px; }
  .lead { color: var(--muted); margin-top: 0; }
  a { color: var(--accent); }
  .hero { width: 100%; height: auto; border-radius: 12px; display: block; margin: 16px 0; }
  .buttons { display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0; }
  .button { display: inline-block; padding: 12px 18px; border-radius: 12px; background: var(--accent); color: var(--on-accent); text-decoration: none; font-weight: 600; }
  .button.secondary { background: transparent; color: var(--accent); border: 1px solid var(--accent); }
  code { background: var(--code); border-radius: 6px; padding: 2px 5px; font-size: 0.85em; overflow-wrap: anywhere; }
  ul { padding-left: 1.2em; }
  li + li { margin-top: 4px; }
  .note { background: var(--note); border: 1px solid var(--note-line); border-radius: 12px; padding: 12px 14px; margin: 20px 0; }
  .note p { margin: 0; }
  .note p + p { margin-top: 6px; }
  .shots { display: grid; grid-template-columns: minmax(0, 1fr); gap: 8px; margin: 16px 0; }
  @media (min-width: 700px) { .shots { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  .shots figure { margin: 0; }
  .shots img { width: 100%; height: auto; border-radius: 8px; display: block; }
  .shots figcaption { color: var(--muted); font-size: 0.8em; margin-top: 3px; }
  .small { color: var(--muted); font-size: 0.85em; }
  footer { margin-top: 36px; padding-top: 16px; border-top: 1px solid var(--line); color: var(--muted); font-size: 0.85em; }
  footer p { margin: 0 0 8px; }
"""


def e(s):
    return html.escape(s, quote=True)


def inline(s):
    """Light markup for list items: [text](url) links and **bold**; the rest escaped."""
    out, i = [], 0
    while i < len(s):
        if s.startswith("**", i) and "**" in s[i + 2:]:
            j = s.index("**", i + 2)
            out.append("<b>" + e(s[i + 2:j]) + "</b>")
            i = j + 2
        elif s[i] == "[" and "](" in s[i:] and ")" in s[s.index("](", i):]:
            j = s.index("](", i)
            k = s.index(")", j)
            out.append('<a href="%s">%s</a>' % (e(s[j + 2:k]), e(s[i + 1:j])))
            i = k + 1
        else:
            j = i + 1
            while j < len(s) and not s.startswith("**", j) and s[j] != "[":
                j += 1
            out.append(e(s[i:j]))
            i = j
    return "".join(out)


def ul(items):
    return "<ul>\n" + "".join("    <li>%s</li>\n" % inline(x) for x in items) + "  </ul>"


def page(g):
    url = "%s/%s/" % (SITE, g["slug"])
    shots = g.get("screenshots", [])
    hero = shots[0] if shots else None
    parts = []
    parts.append('<nav><a href="%s/">Sithewok\'s Game Ports</a></nav>' % SITE)
    parts.append("<h1>%s</h1>" % e(g["title"]))
    parts.append('<p class="lead">%s</p>' % inline(g["lead"]))
    if hero:
        parts.append('<img class="hero" src="%s" alt="%s" width="1600" height="740">' % (e(hero["url"]), e(hero["alt"])))
    parts.append('<p><b>%s</b></p>' % inline(g["need"]))

    parts.append("<h2>Install</h2>")
    if g.get("source"):
        q = urllib.parse.quote(g["source"], safe="")
        parts.append("<p>%s</p>" % inline(g.get("install_lead", "Easiest, in SideStore or AltStore (Classic): add the source, then install the app from it. Updates come the same way.")))
        parts.append('<div class="buttons">\n    <a class="button" id="add-sidestore-button" href="sidestore://source?url=%s">Add to SideStore</a>\n    <a class="button" id="add-altstore-button" href="altstore://source?url=%s">Add to AltStore</a>\n  </div>' % (q, q))
        parts.append("<p class=\"small\">These buttons only work once SideStore or AltStore is on your phone. If a button does nothing, add the source by hand (in the app's Sources, tap +) with this address:<br><code>%s</code></p>" % e(g["source"]))
        parts.append("<p>Or download the .ipa from the releases page and install it with any sideloading tool (Feather, Sideloadly, a signing service):</p>")
    elif g.get("install_lead"):
        parts.append("<p>%s</p>" % inline(g["install_lead"]))
    btns = []
    for b in g.get("buttons", []):
        btns.append('    <a class="button%s" href="%s">%s</a>' % ("" if b.get("primary") else " secondary", e(b["url"]), e(b["text"])))
    if btns:
        parts.append('<div class="buttons">\n' + "\n".join(btns) + "\n  </div>")

    if g.get("features"):
        parts.append("<h2>Cool features</h2>")
        parts.append(ul(g["features"]))

    if len(shots) > 1:
        figs = []
        for s in shots[1:]:
            figs.append('    <figure><img src="%s" alt="%s" loading="lazy" width="1600" height="740"><figcaption>%s</figcaption></figure>' % (e(s["url"]), e(s["alt"]), e(s.get("caption", s["alt"]))))
        parts.append('<h2>Screenshots</h2>\n  <div class="shots">\n' + "\n".join(figs) + "\n  </div>")
        if g.get("shots_note"):
            parts.append('<p class="small">%s</p>' % inline(g["shots_note"]))

    if g.get("sorry"):
        parts.append('<div class="note">' + "".join("<p>%s</p>" % inline(p) for p in g["sorry"]) + "</div>")

    if g.get("thanks"):
        parts.append("<h2>Thank you</h2>")
        if g.get("thanks_lead"):
            parts.append("<p>%s</p>" % inline(g["thanks_lead"]))
        parts.append(ul(g["thanks"]))

    more = [
        "[Source code on GitHub](https://github.com/%s)" % g["repo"],
        "[Report a bug](https://github.com/%s/issues) (here, not to the upstream project)" % g["repo"],
    ] + g.get("more", [])
    parts.append("<h2>More</h2>")
    parts.append(ul(more))
    parts.append("<footer><p>%s</p></footer>" % inline(g["footer"]))

    og_image = hero["url"] if hero else g.get("icon", "")
    body = "\n  ".join(parts)
    script = ""
    if g.get("source"):
        script = """
<script>
  // #add-sidestore / #add-altstore: open that app's "add source" screen at once
  (function () {
    var id = { "#add-sidestore": "add-sidestore-button", "#add-altstore": "add-altstore-button" }[location.hash];
    if (id) location.href = document.getElementById(id).href;
  })();
</script>"""
    ld = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": g["title"],
        "operatingSystem": "iOS",
        "applicationCategory": "GameApplication",
        "description": g["description"],
        "url": url,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
    }
    if hero:
        ld["screenshot"] = [s["url"] for s in shots[:4]]
    return """<!doctype html>
<!-- Made by tools/make_game_pages.py from games.json: edit those, not this file. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="keywords" content="{kw}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Sithewok's Game Ports">
<meta property="og:title" content="{ogtitle}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{ogimg}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{ogtitle}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{ogimg}">
{icon}<script type="application/ld+json">{ld}</script>
<style>{style}</style>
</head>
<body>
<main>
  {body}
</main>{script}
</body>
</html>
""".format(
        title=e(g["page_title"]), desc=e(g["description"]), kw=e(", ".join(g.get("keywords", []))),
        url=e(url), ogtitle=e(g["title"]), ogimg=e(og_image),
        icon=('<link rel="icon" href="%s">\n<link rel="apple-touch-icon" href="%s">\n' % (e(g["icon"]), e(g["icon"]))) if g.get("icon") else "",
        ld=json.dumps(ld, ensure_ascii=False).replace("</", "<\\/"), style=STYLE, body=body, script=script)


def main():
    with open(os.path.join(ROOT, "games.json"), encoding="utf-8") as f:
        games = json.load(f)["games"]
    urls = [SITE + "/"]
    for g in games:
        d = os.path.join(ROOT, g["slug"])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(page(g))
        urls.append("%s/%s/" % (SITE, g["slug"]))
    urls.append(SITE + "/builds/")
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u in urls:
            f.write("  <url><loc>%s</loc></url>\n" % u)
        f.write("</urlset>\n")
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % SITE)
    print("wrote %d pages" % len(games))


if __name__ == "__main__":
    main()
