"""Pull public LeetCode and Codeforces stats into stats.json on the data branch.

    python3 sync.py <data-branch-checkout-dir>

Usernames come from log.json (profile.leetcode / profile.codeforces), which the site writes.
stats.json keeps the latest numbers plus a running history: LeetCode total per day (IST) and
every accepted problem seen in the "recent accepted" feed. The file is rewritten only when
something changed, or every 6 hours so the site can show the check is still running.
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
UA = {"User-Agent": "prep-log-sync/1.0"}


def get_json(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def leetcode(user):
    q = """query($u:String!){
      matchedUser(username:$u){ submitStatsGlobal{ acSubmissionNum{ difficulty count } } profile{ ranking } }
      recentAcSubmissionList(username:$u, limit:20){ title titleSlug timestamp }
    }"""
    body = json.dumps({"query": q, "variables": {"u": user}}).encode()
    res = get_json("https://leetcode.com/graphql", body,
                   {"Content-Type": "application/json", "Referer": "https://leetcode.com"})
    mu = (res.get("data") or {}).get("matchedUser")
    if not mu:
        raise ValueError(f"LeetCode user '{user}' not found")
    counts = {c["difficulty"]: c["count"] for c in mu["submitStatsGlobal"]["acSubmissionNum"]}
    recent = [{"slug": r["titleSlug"], "title": r["title"], "ts": int(r["timestamp"])}
              for r in (res["data"].get("recentAcSubmissionList") or [])]
    return {"username": user, "total": counts.get("All", 0), "easy": counts.get("Easy", 0),
            "medium": counts.get("Medium", 0), "hard": counts.get("Hard", 0),
            "ranking": (mu.get("profile") or {}).get("ranking")}, recent


def codeforces(handle):
    info = get_json(f"https://codeforces.com/api/user.info?handles={handle}")
    if info.get("status") != "OK":
        raise ValueError(f"Codeforces handle '{handle}' not found")
    u = info["result"][0]
    hist = get_json(f"https://codeforces.com/api/user.rating?handle={handle}").get("result", [])
    return {"handle": u["handle"], "rating": u.get("rating", 0), "maxRating": u.get("maxRating", 0),
            "rank": u.get("rank", "unrated"),
            "contests": [{"name": c["contestName"], "at": c["ratingUpdateTimeSeconds"] * 1000, "rank": c["rank"],
                          "oldRating": c["oldRating"], "newRating": c["newRating"]} for c in hist]}


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def main(data_dir):
    log = load(os.path.join(data_dir, "log.json"), {})
    profile = log.get("profile") or {}
    stats_path = os.path.join(data_dir, "stats.json")
    old = load(stats_path, {})
    new = json.loads(json.dumps(old))
    new.setdefault("lcHistory", {})
    new.setdefault("solved", {})
    errors = []

    lc_user = (profile.get("leetcode") or "").strip()
    if lc_user:
        try:
            lc, recent = leetcode(lc_user)
            if (old.get("lc") or {}).get("username") != lc_user:
                new["solved"] = {}  # username changed: start the solved set over
                new["lcHistory"] = {}
            new["lc"] = lc
            new["lcHistory"][datetime.now(IST).strftime("%Y-%m-%d")] = lc["total"]
            for r in recent:
                new["solved"].setdefault(r["slug"], {"title": r["title"], "at": r["ts"] * 1000})
        except Exception as e:  # keep going so Codeforces still updates
            errors.append(f"leetcode: {e}")
    else:
        new.pop("lc", None)

    cf_handle = (profile.get("codeforces") or "").strip()
    if cf_handle:
        try:
            new["cf"] = codeforces(cf_handle)
        except Exception as e:
            errors.append(f"codeforces: {e}")
    else:
        new.pop("cf", None)

    new["errors"] = errors
    strip = lambda d: {k: v for k, v in d.items() if k != "checkedAt"}
    stale = time.time() * 1000 - old.get("checkedAt", 0) > 6 * 3600 * 1000
    if strip(new) != strip(old) or stale:
        new["checkedAt"] = int(time.time() * 1000)
        with open(stats_path, "w") as f:
            json.dump(new, f, separators=(",", ":"))
        print("stats.json updated")
    else:
        print("no change")
    for e in errors:
        print("warning:", e, file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
