# httpeek — Official Cheatsheet

A fast, practical HTTP recon tool. Focused on **signal**: statuses, titles, sizes, redirect chains, optional TLS info, and Cloudflare heuristics (DNS + headers).

- Author: **Bayqus** · Email: **bayqussec@gmail.com** · GitHub: **https://github.com/BAYQUS**
- Acknowledgements: Thanks to **turkhacks.com** and **cyberdark.org** for their support.
- Part of a larger recon **framework** in development — httpeek is the HTTP module.

---

## Quick Start

```bash
# One target
httpeek -u https://example.com

# Many targets from a file with higher concurrency
httpeek -l hosts.txt --threads 200

# Read from stdin and export JSON Lines
cat hosts.txt | httpeek --stdin --json > out.jsonl
```

**Default behavior**
- Follows redirects (unless `--no-redirect`).
- Prints live rows with a progress indicator.
- Columns: **URL · IP · Status · Title · Redirect**.

Use `--silent` to suppress live rows and print a single final table.  
Use `--json` or `--csv` for machine-friendly output.

---

## CLI Reference

### Target Source (choose one)
- `-u, --url <URL>` — Single URL (schema optional; auto-normalizes).
- `-l, --list <FILE>` — File with one target per line.
- `--stdin` — Read targets from STDIN.

### Core Options
- `-o, --output <FILE>` — Append plain results (`url | ip | status | raw_title`).
- `--random-agent` — Use a random User‑Agent for the request.
- `-sc, --status-code <SPEC>` — Filter by status codes. Supports:
  - Exact: `200`  · Range: `300-399`  · Class: `2xx`
  - Multiple: `2xx,301-302,404`
- `--timeout <S>` — Request timeout in seconds (default: `10`).
- `--retries <N>` — Retry count on failure (default: `3`).
- `--threads <N>` — Concurrency (default: `50`).
- `--proxy <URL>` — Proxy (e.g., `http://127.0.0.1:8080`, `socks5://127.0.0.1:9050`).
- `--headers "K: V"` — Extra header (repeatable). Example:
  - `--headers "X-Test: 1" --headers "Accept: */*"`
- `--silent` — Hide live rows; print one final table only.

### Request Behavior
- `--method {GET,HEAD}` — HTTP method (default: `GET`).
- `--no-redirect` — Do not follow redirects (show the initial response only).

### Content/Regex Filters
- `-cl, --content-length <N|A-B>` — Require response size. Examples: `512`, `1000-2000`.
- `--exclude-length <LIST>` — Exclude sizes. Examples: `0`, `0,100-300`.
- `--title-match <REGEX>` — Require `<title>` to match regex (Python syntax).
- `--body-match <REGEX>` — Require body to match regex (case-insensitive example: `(?i)admin`).

### Output Formats
- `--json` — Prints **one JSON object per line** with fields:
  - `url, ip, status, title, length, headers, redirect[, tls]`
- `--csv` — Prints: `url,ip,status,length,"title"`
- `--tls-info` — Include TLS certificate metadata (`subject`, `issuer`, `expires_utc`).
- `--only-active` — Print only targets that returned any HTTP status.

### Misc
- `--version` — Print version and exit (if available).

---

## Field Semantics

### Redirect summary
- Displayed as: `→ <count> • <final-host>`  
- Example: `→ 2 • www.example.com`

### Title rendering
- Raw HTML `<title>` is used.  
- If Cloudflare is likely and title is generic (`"Just a moment..."` etc.), shows **Cloudflare** tag and/or `[CF]` suffix.

### Cloudflare heuristic
- **DNS:** NS ending with `cloudflare.com`, or CNAME/answer chain containing `cdn.cloudflare.net`, `cloudflare.net`, `cloudflare.com`.
- **HTTP:** `Server` header contains `cloudflare`, or presence of `CF-Ray` header.
- No static IP‑range lists are used.

### TLS info (`--tls-info`)
- Extracts `subject.commonName`, `issuer.commonName`, and `notAfter` (as `expires_utc` ISO timestamp).

---

## Practical Examples

```bash
# Only 2xx + common 301/302 redirects; active only; high concurrency
httpeek -l hosts.txt -sc 2xx,301-302 --only-active --threads 200

# Head requests to check availability fast (no body)
httpeek -l hosts.txt --method HEAD --threads 300

# Look for admin/login hints in HTML and dashboards in titles
httpeek -l hosts.txt --body-match "(?i)admin|login" --title-match "(?i)dashboard"

# Strict size window (useful for fingerprinting)
httpeek -l hosts.txt -cl 4096-5120 --exclude-length 0

# Through a proxy with a custom header
httpeek -u https://target --proxy http://127.0.0.1:8080 --headers "X-Bug: 1"

# Include TLS info panels (slower)
httpeek -u https://secure.example --tls-info
```

---

## Performance Tips

- Increase `--threads` for large lists; pair with a sensible `--timeout` (e.g., `5–8` secs).
- Use `--method HEAD` when you only need reachability/redirects.
- Keep `--retries` low on flaky targets to avoid long scans.
- Combine `-sc`, `-cl`, and regex filters to reduce noise early.

---

## Troubleshooting

- **Externally managed env (PEP 668, e.g., Kali):** use `python3 -m venv venv && source venv/bin/activate` or `pipx`.  
- **Wrapper error “No module named httpeek”:** point the wrapper to the project file directly:
  ```bash
  sudo tee /usr/bin/httpeek >/dev/null <<'WRAP'
  #!/usr/bin/env bash
  exec /usr/share/httpeek/.venv/bin/python /usr/share/httpeek/httpeek.py "$@"
  WRAP
  sudo chmod +x /usr/bin/httpeek
  ```
- **Titles missing on 301/302:** that’s expected; use `--no-redirect` to view the first hop, or let httpeek follow to a 200.
- **Different results across distros:** CA bundles, resolver behavior, and HTTP stacks may differ (e.g., Fedora vs Kali). Prefer the venv created by the installer.

---

## Exit Codes

- `0` — Completed (no fatal error encountered).
- `1` — CLI/argument error or unhandled exception.

---

## JSON Line Example

```json
{
  "url": "https://example.com/",
  "ip": "93.184.216.34",
  "status": 200,
  "title": "Example Domain [CF]",
  "length": 1256,
  "headers": {"server": "cloudflare", "...": "..."},
  "redirect": "→ 1 • www.example.com",
  "tls": {
    "subject": {"commonName": "example.com"},
    "issuer": {"commonName": "Let's Encrypt Authority X3"},
    "expires_utc": "2025-12-31T23:59:59"
  }
}
```

---

### One‑liners to remember
```bash
# Quiet sweep with summary only
httpeek -l hosts.txt --silent -sc 2xx,301-302 --threads 150

# JSON export for grep/jq
httpeek -l hosts.txt --json | jq -r 'select(.status==200) | .url'

# Hunt for login/admin hints
httpeek -l hosts.txt --body-match "(?i)admin|login" --title-match "(?i)sign in|dashboard"
```
