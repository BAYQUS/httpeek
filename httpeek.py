#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import argparse
from typing import List

from rich.console import Console
from rich.text import Text

from includes.http_check import (
    url_normalize,
    check_status,
    check_many,
    print_results_table,
)

APP_VERSION = "1.0.1"

# console setup (colors, nicer output)
console = Console()

# ===== Banner =====
BANNER = r"""
██╗  ██╗████████╗████████╗██████╗ ███████╗███████╗██╗  ██╗
██║  ██║╚══██╔══╝╚══██╔══╝██╔══██╗██╔════╝██╔════╝██║ ██╔╝
███████║   ██║      ██║   ██████╔╝█████╗  █████╗  █████╔╝ 
██╔══██║   ██║      ██║   ██╔═══╝ ██╔══╝  ██╔══╝  ██╔═██╗ 
██║  ██║   ██║      ██║   ██║     ███████╗███████╗██║  ██╗
╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝
"""

def stylize_banner():
    """Print the banner with minimal styling."""
    t = Text(BANNER)
    mid = len(BANNER) // 2
    t.stylize("bold blue", 0, mid)
    t.stylize("bold red", mid)
    console.print(t)
    console.print(
        f"[bold cyan]Coded by[/bold cyan] [bold yellow]Bayqus 🦉[/bold yellow]   "
        f"[bold green]                       version {APP_VERSION}[/bold green]"
    )
    console.print("[bold red]__________________________________________________________[/bold red]")

# ===== Help text =====
HELP_DESC = """\
Fast HTTP checker with filtering, progress, and pretty output.

- By default uses GET and prints IP, status, title, redirect info.
- Use --silent to suppress live rows and show a single final table at the end.
- Use --json or --csv for machine-friendly output (no progress/live UI).
- Supports single URL, file input, or stdin.
- special thanks : turkhacks.com, cyberdark.org
"""

HELP_EPILOG = """\
Examples:
  # single target
  python httpeek.py -u https://example.com

  # from file with concurrency
  python httpeek.py -l hosts.txt --threads 50

  # read from stdin
  cat hosts.txt | python httpeek.py --stdin

  # filter only 2xx and 301-302
  python httpeek.py -l hosts.txt -sc 2xx,301-302

  # show only active targets (any HTTP response)
  python httpeek.py -l hosts.txt --only-active

  # include TLS info panels (slower)
  python httpeek.py -l hosts.txt --tls-info

  # send custom headers
  python httpeek.py -u https://target --headers "X-Test: 1" --headers "Accept: */*"
"""

# ---- Custom parser to show banner on help/usage/errors ----
class BannerArgumentParser(argparse.ArgumentParser):
    def print_help(self, file=None):
        stylize_banner()
        super().print_help(file)

    def error(self, message):
        # Show banner + usage + error (matches argparse style, with banner first)
        stylize_banner()
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")

def make_parser() -> argparse.ArgumentParser:
    """arg parser with sane defaults; shows banner on -h and on errors."""
    parser = BannerArgumentParser(
        description=HELP_DESC,
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=False,  # we'll add our own '-h/--help' so print_help() runs with banner
    )

    # standard help option (will call print_help -> prints banner first)
    parser.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    # where targets come from (pick one)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("-u", "--url", help="Single target URL")
    src.add_argument("-l", "--list", help="Path to a file with targets")
    src.add_argument("--stdin", action="store_true", help="Read targets from STDIN")

    # basics
    parser.add_argument("-o", "--output", help="Append plain results to a file")
    parser.add_argument("--random-agent", action="store_true", default=False, help="Use a random User-Agent")
    parser.add_argument(
        "-sc", "--status-code",
        default="All",
        help="Status filter, e.g. 200,301-302,2xx or 'All'"
    )
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout (seconds)")
    parser.add_argument("--retries", type=int, default=3, help="Retry count on failure")
    parser.add_argument("--threads", type=int, default=50, help="Concurrency level")
    parser.add_argument("--proxy", default=None, help="Proxy, e.g. http://127.0.0.1:8080")
    parser.add_argument(
        "--headers",
        action="append",
        default=None,
        help="Custom header 'Key: Value' (can be used multiple times)",
    )
    parser.add_argument("--silent", action="store_true", default=False, help="Hide live rows; show final table only")

    # request behavior
    parser.add_argument(
        "--method",
        choices=["HEAD", "GET"],
        default="GET",
        help="HTTP method to use (default: GET)",
    )
    parser.add_argument("--no-redirect", action="store_true", default=False, help="Do not follow redirects")

    # filters (quick-and-dirty but handy)
    parser.add_argument(
        "-cl", "--content-length",
        default=None,
        help="Filter by content-length: 512 or 1000-2000"
    )
    parser.add_argument("--title-match", default=None, help="Regex to match in <title>")
    parser.add_argument("--body-match", default=None, help="Regex to match in body")
    parser.add_argument("--exclude-status", default=None, help="Exclude status codes, e.g. 404,400-499")
    parser.add_argument("--exclude-length", default=None, help="Exclude lengths: 0,100-300")

    # output formats (good for piping)
    parser.add_argument("--json", action="store_true", default=False, help="Print JSON per row")
    parser.add_argument("--csv", action="store_true", default=False, help="Print CSV rows")

    # extras (because why not)
    parser.add_argument("--tls-info", action="store_true", default=False, help="Print TLS certificate info")
    parser.add_argument("--only-active", action="store_true", default=False, help="Print only active domains")

    # convenience
    parser.add_argument("--version", action="version", version=f"%(prog)s {APP_VERSION}")

    return parser

def parse_headers(header_items: List[str] | None):
    """turn ['K: V','X: 1'] into a dict; ignore wonky lines without ':'."""
    if not header_items:
        return None
    out = {}
    for h in header_items:
        if ":" not in h:
            continue
        k, v = h.split(":", 1)
        out[k.strip()] = v.strip()
    return out or None

def read_list_file(path: str) -> List[str]:
    """read targets from a file; bails if file is missing (better early than sorry)."""
    if not os.path.exists(path):
        console.print(f"⚠️ [bold red]Target list not found:[/bold red] {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return [line.strip() for line in f if line.strip()]

def main():
    parser = make_parser()
    params = parser.parse_args()

    # For normal runs (valid args), also show the banner before scanning.
    # If user invoked -h or provided no args, the program would have already exited
    # from BannerArgumentParser.print_help/error, so this line runs only for valid runs.
    stylize_banner()

    # shared knobs for workers; keeps CLI plumbing tidy
    common_kwargs = {
        "output": params.output,
        "random_agent": params.random_agent,
        "status_code": params.status_code if params.status_code != "All" else None,
        "timeout": params.timeout,
        "retries": params.retries,
        "proxy": params.proxy,
        "headers": parse_headers(params.headers),
        "method": params.method,               # GET by default
        "no_redirect": params.no_redirect,
        "content_length": params.content_length,
        "title_match": re.compile(params.title_match) if params.title_match else None,
        "body_match": re.compile(params.body_match) if params.body_match else None,
        "exclude_status": params.exclude_status,
        "exclude_length": params.exclude_length,
        "as_json": params.json,
        "as_csv": params.csv,
        "tls_info": params.tls_info,
        "only_active": params.only_active,
        "print_ip": True,                      # always show IP
    }

    # pick UI mode (live vs silent vs export)
    show_progress = not (params.json or params.csv)
    show_live = not params.silent and not (params.json or params.csv)
    show_final = params.silent and not (params.json or params.csv)

    try:
        if params.url:
            console.print(f"🎯 Target: [bold]{params.url}[/bold]", style="cyan")
            row = check_status(
                url=params.url,
                use_spinner=show_progress and not params.silent,
                no_print=params.silent or params.json or params.csv,
                **common_kwargs,
            )
            if params.silent and not (params.json or params.csv) and row:
                print_results_table([row], show_ip=True)

        elif params.list:
            console.print(f"📄 Target list: [bold]{params.list}[/bold]", style="cyan")
            urls = read_list_file(params.list)
            urls = [u.strip() for u in urls if u.strip()]
            _ = check_many(
                urls,
                threads=params.threads,
                show_progress=show_progress,
                show_final=show_final,
                show_live=show_live,
                **common_kwargs,
            )

        elif params.stdin:
            console.print("Reading targets from STDIN...")
            urls = [line.strip() for line in sys.stdin if line.strip()]
            _ = check_many(
                urls,
                threads=params.threads,
                show_progress=show_progress,
                show_final=show_final,
                show_live=show_live,
                **common_kwargs,
            )

    except KeyboardInterrupt:
        console.print("\n[yellow]Exited[/yellow]")

if __name__ == "__main__":
    main()
