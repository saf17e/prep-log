# Prep Log

Personal practice tracker: arithmetic sprint drill, weekly LeetCode checklist, and LeetCode / Codeforces progress.

- Site: https://harlieislegend.github.io/prep-log/
- `main` holds the site (`index.html`) and the hourly sync (`sync.py`, `.github/workflows/sync.yml`).
- `data` holds the records: `log.json` (sprint runs, ticks, usernames, written by the site) and `stats.json` (written by the sync).
- Each device connects with a fine-grained token (Contents + Actions read/write on this repo only). The token is kept in that browser's storage, never in the repo.
