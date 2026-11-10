#!/usr/bin/env python3
"""Fill builds/builds.json (the builds page) and builds/source.json (a Feather /
AltStore source) from each app's GitHub release, as listed in builds/apps.json.

Tokens (environment): GITHUB_TOKEN for public repos; for private ones
RELEASES_TOKEN_<OWNER> (e.g. RELEASES_TOKEN_RELITH_DEV), else RELEASES_TOKEN. Without RELEASES_TOKEN private apps show "no access".
Writes the files only when something about the builds changed.
"""
import json, os, re, sys, urllib.request, urllib.error
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SITE = "https://sithewok13-dev.github.io/builds/"
STAMP = re.compile(r"Build\s+(\d+)\s*·\s*(\d{4}-\d{2}-\d{2})")


def get(url, token):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "builds-page"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def releases(repo, token, cache):
    if repo not in cache:
        try:
            cache[repo] = get("https://api.github.com/repos/%s/releases?per_page=30" % repo, token)
        except urllib.error.HTTPError as e:
            cache[repo] = e.code
        except Exception:
            cache[repo] = 0
    return cache[repo]


def pick(rels, tags):
    for t in tags:
        if t == "*":
            real = [r for r in rels if not r.get("draft") and r["tag_name"] != "ios-latest"]
            real.sort(key=lambda r: r.get("published_at") or "", reverse=True)
            if real:
                return real[0]
        else:
            for r in rels:
                if r["tag_name"] == t and not r.get("draft"):
                    return r
    return None


def one(app, cache):
    priv = bool(app.get("private"))
    owner_token = os.environ.get("RELEASES_TOKEN_" + app["repo"].split("/")[0].upper().replace("-", "_"))
    token = (owner_token or os.environ.get("RELEASES_TOKEN")) if priv else os.environ.get("GITHUB_TOKEN")
    out = {k: app.get(k) for k in ("id", "name", "about", "repo", "bundle")}
    out["private"] = priv
    if app.get("description"):
        out["description"] = app["description"]
    if priv and not token:
        out["status"] = "no access"
        return out
    rels = releases(app["repo"], token, cache)
    if not isinstance(rels, list):
        out["status"] = "no access" if rels in (401, 403, 404) else "error"
        return out
    rel = pick(rels, app["tags"])
    if not rel:
        out["status"] = "no release"
        return out
    asset = next((a for a in rel.get("assets", []) if re.search(app["asset"], a["name"])), None)
    if not asset:
        out["status"] = "no download"
        out["release"] = rel["html_url"]
        return out
    m = STAMP.search(rel.get("body") or "")
    out.update({
        "status": "ok",
        "build": int(m.group(1)) if m else None,
        "date": m.group(2) if m else asset["updated_at"][:10],
        "built": asset["updated_at"],
        "size": asset["size"],
        "tag": rel["tag_name"],
        "download": asset["browser_download_url"],
        "release": rel["html_url"],
    })
    return out


def source(apps):
    entries = []
    for a in apps:
        if a.get("private") or a.get("status") != "ok":
            continue
        version = "build %d" % a["build"] if a["build"] else a["built"].replace("T", " ").rstrip("Z")
        v = {"version": version, "date": a["built"], "size": a["size"], "downloadURL": a["download"]}
        e = {
            "name": a["name"], "bundleIdentifier": a["bundle"], "developerName": "sithewok",
            "subtitle": a.get("about") or "", "localizedDescription": a.get("description") or ((a.get("about") or a["name"]) + ". Test build; bring your own game files."),
            "iconURL": SITE + "icons/" + a["id"] + ".png", "tintColor": "8e3aa8",
            "versions": [v], "version": version, "versionDate": a["built"],
            "size": a["size"], "downloadURL": a["download"], "appPermissions": {},
        }
        entries.append(e)
    return {
        "name": "Sithewok's Builds", "identifier": "io.github.sithewok13.builds",
        "website": SITE, "iconURL": SITE + "icons/source.png", "tintColor": "8e3aa8",
        "apps": entries, "news": [],
    }


def main():
    cfg = json.load(open(os.path.join(ROOT, "builds", "apps.json")))
    cache = {}
    apps = [one(a, cache) for a in cfg["apps"]]
    path = os.path.join(ROOT, "builds", "builds.json")
    try:
        old = json.load(open(path))
    except Exception:
        old = {}
    if old.get("apps") == apps and "--force" not in sys.argv:
        print("no change")
        return
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(path, "w") as f:
        json.dump({"updated": now, "apps": apps}, f, indent=1, ensure_ascii=False)
        f.write("\n")
    with open(os.path.join(ROOT, "builds", "source.json"), "w") as f:
        json.dump(source(apps), f, indent=1, ensure_ascii=False)
        f.write("\n")
    for a in apps:
        print("%-12s %-11s build %s %s" % (a["id"], a["status"], a.get("build"), a.get("date")))


if __name__ == "__main__":
    main()
