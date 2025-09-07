#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import ssl
import httpx
import re
import random
import json
import threading
import warnings
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning, MarkupResemblesLocatorWarning
from urllib.parse import urlparse, urljoin

from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn,
    TimeElapsedColumn, TimeRemainingColumn
)
from rich.live import Live

# quiet down some noisy bs4 warnings (they're harmless here)
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

# console styling
console = Console(highlight=True, soft_wrap=False)

# default headers (pretty standard, keeps servers happy)
HEADERS_DEFAULT = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,tr;q=0.7,az;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

# rotate UA if you want to look less boring :)
USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
]

# ---------- Cloudflare (DNS hints first, then HTTP fingerprints) ----------

def _is_ip_literal(hostname):
    """Quick check: is this a raw IPv4/IPv6 string?"""
    if not hostname:
        return False
    try:
        socket.inet_aton(hostname)  # IPv4
        return True
    except Exception:
        pass
    try:
        socket.inet_pton(socket.AF_INET6, hostname)  # IPv6
        return True
    except Exception:
        return False

def dns_indicates_cloudflare(hostname, timeout=2.0):
    """
    Try to guess CF via DNS (NS/CNAME etc). No IP-range stuff, on purpose.
    If dnspython is missing or DNS fails, just return False. No hard crashes.
    """
    if not hostname or _is_ip_literal(hostname):
        return False

    try:
        import dns.resolver  # type: ignore
        resolver = dns.resolver.Resolver()
        resolver.lifetime = timeout  # don't hang forever

        # NS → *.ns.cloudflare.com is a strong sign
        try:
            ns_answers = resolver.resolve(hostname, "NS", raise_on_no_answer=False)
            if ns_answers and getattr(ns_answers, "rrset", None):
                for r in ns_answers:
                    target = str(getattr(r, "target", r)).rstrip(".").lower()
                    if target.endswith("cloudflare.com"):
                        return True
        except Exception:
            pass

        # CNAME chain → cloudflare domains show up often
        try:
            cname_answers = resolver.resolve(hostname, "CNAME", raise_on_no_answer=False)
            if cname_answers and getattr(cname_answers, "rrset", None):
                for r in cname_answers:
                    cname = str(getattr(r, "target", r)).rstrip(".").lower()
                    if any(p in cname for p in ("cdn.cloudflare.net", "cloudflare.net", "cloudflare.com")):
                        return True
        except Exception:
            pass

        # sometimes the answer section for A/AAAA carries a CNAME target
        try:
            a_answers = resolver.resolve(hostname, "A", raise_on_no_answer=False)
            resp = getattr(a_answers, "response", None)
            if resp and getattr(resp, "answer", None):
                for rrset in resp.answer:
                    for item in getattr(rrset, "items", []):
                        target = getattr(item, "target", None)
                        if target and any(p in str(target).lower() for p in ("cloudflare.net", "cloudflare.com")):
                            return True
        except Exception:
            pass

        try:
            aaaa_answers = resolver.resolve(hostname, "AAAA", raise_on_no_answer=False)
            resp = getattr(aaaa_answers, "response", None)
            if resp and getattr(resp, "answer", None):
                for rrset in resp.answer:
                    for item in getattr(rrset, "items", []):
                        target = getattr(item, "target", None)
                        if target and any(p in str(target).lower() for p in ("cloudflare.net", "cloudflare.com")):
                            return True
        except Exception:
            pass

    except Exception:
        # fallback: check canonical + aliases and see if names look CF-ish
        try:
            canonical, aliases, _ = socket.gethostbyname_ex(hostname)
            chain = [canonical] + (aliases or [])
            if any("cloudflare" in (name or "").lower() for name in chain):
                return True
        except Exception:
            pass

    return False

def detect_cloudflare(resp, hostname):
    """
    CF? first ask DNS, then peek at headers (Server/cf-ray).
    Keep it best-effort, never blow up here.
    """
    try:
        if hostname and dns_indicates_cloudflare(hostname):
            return True

        if resp is None:
            return False

        h = resp.headers
        server = (h.get("server") or h.get("Server") or "").lower()

        if "cloudflare" in server:
            return True
        if "cf-ray" in {k.lower() for k in h.keys()}:
            return True

        return False
    except Exception:
        return False

# ---------- helpers ----------

def url_normalize(raw, timeout=2):
    """
    Make an input look like a normal URL.
    If scheme exists, only add '/' for empty or root path.
    If not, probe 443→80 to pick http/https. Kinda pragmatic.
    """
    url = (raw or "").strip()
    if url.startswith(("http://", "https://")):
        parsed = urlparse(url)
        if parsed.path in ("", "/"):
            return url if url.endswith("/") else url + "/"
        return url  # don't touch non-root paths

    # no scheme → try https, then http
    host = url.split("/")[0]
    try:
        with socket.create_connection((host, 443), timeout=timeout):
            return f"https://{url}/"
    except Exception:
        pass
    try:
        with socket.create_connection((host, 80), timeout=timeout):
            return f"http://{url}/"
    except Exception:
        pass
    return f"http://{url}/"

def grab_tls_info(hostname, port=443, timeout=5.0):
    """
    Pull a tiny bit of TLS cert info. Keep the shape small, stable.
    If it fails, return an error string, not an exception. chill :)
    """
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
        subject = dict(x for x in cert.get("subject", [("commonName", "?")])[0])
        issuer = dict(x for x in cert.get("issuer", [("commonName", "?")])[0])
        not_after = cert.get("notAfter")
        exp_ts = None
        if not_after:
            exp_ts = datetime.strptime(not_after, "%b %d %H:%M:%S %Y GMT")
        return {
            "subject": subject,
            "issuer": issuer,
            "not_after": not_after,
            "expires_utc": exp_ts.isoformat() if exp_ts else None,
        }
    except Exception as e:
        return {"error": f"TLS grab failed: {type(e).__name__}: {e}"}

def ensure_regex(maybe_regex):
    """Accepts a compiled regex or plain substring; returns a predicate."""
    if maybe_regex is None:
        return None
    if isinstance(maybe_regex, re.Pattern):
        return maybe_regex.search
    return lambda text: (maybe_regex in (text or ""))

def status_style(code):
    if code is None:
        return "bright_black"
    if 200 <= code < 300: return "green"
    if 300 <= code < 400: return "yellow"
    if 400 <= code < 500: return "red"
    if 500 <= code < 600: return "bright_red"
    return "white"

def _new_live_table():
    table = Table(
        box=box.SIMPLE_HEAVY, expand=True, show_lines=False, padding=(0,1)
    )
    table.add_column("URL", style="cyan", no_wrap=True, overflow="fold")
    table.add_column("IP", style="magenta", no_wrap=True)
    table.add_column("Status", style="white", no_wrap=True, justify="right")
    table.add_column("Title", style="bold", overflow="fold")
    table.add_column("Redirect", style="blue", no_wrap=True)
    return table

def _append_row(table, res):
    status = res.get("status")
    title  = res.get("title") or "Title not found 🫤"
    table.add_row(
        res.get("url",""),
        res.get("ip","-"),
        f"[{status_style(status)}]{status if status is not None else 'ERR'}[/]",
        title,
        res.get("redirect","")
    )

def print_results_table(results, show_ip=True):
    # sort by status bucket then url, keeps the view tidy
    def key_fn(x):
        code = x.get("status")
        bucket = 9 if code is None else (code // 100)
        return (bucket, x.get("url",""))
    rows = sorted(results, key=key_fn)

    table = _new_live_table()
    for r in rows:
        if not show_ip:
            r = dict(r); r["ip"] = "-"
        _append_row(table, r)
    console.print(table)

# ---------- requester (tries auto redirects, then manual as fallback) ----------

def _safe_request(method, url, *, headers, timeout, proxies, no_redirect):
    """
    Try modern httpx (with follow_redirects). If that fails (old httpx) and
    no_redirect=False, chase 3xx manually (max 10 hops). Cheap and robust.
    Returns: (response, manual_history_hosts)
    """
    manual_hosts = []

    # Attempt 1: modern signature
    try:
        resp = httpx.request(
            method, url,
            headers=headers,
            follow_redirects=not no_redirect,
            timeout=timeout,
            proxies=proxies,
        )
        return resp, manual_hosts
    except TypeError:
        pass  # older httpx, keep going

    # Attempt 2: minimal call (no redirects here)
    try:
        resp = httpx.request(method, url, headers=headers, timeout=timeout)
    except TypeError:
        # Attempt 3: client ctx, may or may not have follow_redirects
        try:
            with httpx.Client(
                headers=headers, timeout=timeout,
                follow_redirects=not no_redirect, proxies=proxies
            ) as client:
                resp = client.request(method, url)
                return resp, manual_hosts
        except TypeError:
            with httpx.Client(headers=headers, timeout=timeout) as client:
                resp = client.request(method, url)

    # got a response without auto redirect
    if no_redirect:
        return resp, manual_hosts

    # manual follow (max 10)
    current_url = url
    current_method = method
    last_resp = resp
    for _ in range(10):
        code = last_resp.status_code or 0
        loc = last_resp.headers.get("Location") or last_resp.headers.get("location")
        if code in (301, 302, 303, 307, 308) and loc:
            try:
                next_url = urljoin(current_url, loc)
            except Exception:
                break
            try:
                h = urlparse(next_url).hostname
                if h and (not manual_hosts or manual_hosts[-1] != h):
                    manual_hosts.append(h)
            except Exception:
                pass
            if code == 303:
                current_method = "GET"
            current_url = next_url
            last_resp = httpx.request(current_method, current_url, headers=headers, timeout=timeout)
            continue
        break

    return last_resp, manual_hosts

# ---------- core ----------

def check_status(**arguments):
    """
    Run 1 HTTP check and return a dict for the table (or None if filtered).
    Keeps UI printing optional so it can be used headless too.
    """
    # inputs
    url         = arguments.get("url")
    output      = arguments.get("output")
    random_agent= arguments.get("random_agent", False)
    status_code = arguments.get("status_code")
    timeout     = arguments.get("timeout", 10.0)
    retries     = arguments.get("retries", 3)
    proxy       = arguments.get("proxy")
    req_headers = dict(arguments.get("headers") or HEADERS_DEFAULT)
    method      = arguments.get("method", "GET").upper()
    no_redirect = arguments.get("no_redirect", False)
    content_len = arguments.get("content_length")
    title_match = arguments.get("title_match")
    body_match  = arguments.get("body_match")
    excl_status = arguments.get("exclude_status")
    exclude_len = arguments.get("exclude_length")
    as_json     = arguments.get("as_json", False)
    as_csv      = arguments.get("as_csv", False)
    tls_wanted  = arguments.get("tls_info", False)
    only_active = arguments.get("only_active", False)
    print_ip    = arguments.get("print_ip", True)  # legacy compat
    # UI
    use_spinner = arguments.get("use_spinner", False)
    quiet_retries = arguments.get("quiet_retries", True)
    no_print    = arguments.get("no_print", False)

    if not url:
        if not no_print:
            console.print(Panel("[red]Error: url is missing[/red]", border_style="red"))
        return None

    if random_agent:
        req_headers["User-Agent"] = random.choice(USER_AGENTS)

    url = url_normalize(url)

    proxies = None
    if proxy:
        proxies = (
            {"http://": proxy, "https://": proxy}
            if str(proxy).startswith(("http://", "socks5://"))
            else proxy
        )

    title_search = ensure_regex(title_match)
    body_search  = ensure_regex(body_match)

    attempt = 0
    last_exc = None

    # tiny null context so we can plop a with block easily
    class _NullCtx:
        def __enter__(self): return self
        def __exit__(self, *a): return False
    nullctx = _NullCtx()

    while attempt <= retries:
        try:
            status_text = Text(f"{method} {url}", style="bold")
            ctx = console.status(status_text, spinner="dots") if use_spinner else nullctx
            with ctx:
                resp, manual_hosts = _safe_request(
                    method, url,
                    headers=req_headers,
                    timeout=timeout,
                    proxies=proxies,
                    no_redirect=no_redirect,
                )

            hostname = urlparse(url).hostname or ""
            try:
                ip = socket.gethostbyname(hostname) if hostname else "N/A"
            except socket.gaierror:
                ip = "DNS_FAIL"

            # pull a simple <title>
            soup = BeautifulSoup(resp.text or "", "html.parser")
            raw_title = (soup.title.string.strip()
                         if soup.title and soup.title.string else None)

            # CF guess (dns first, then headers). no IP-range games.
            is_cf = detect_cloudflare(resp, hostname if hostname else None)

            # final title decoration
            generic = raw_title in (None, "", "Just a moment...", "Attention Required! | Cloudflare")
            if generic and is_cf:
                title = "[bright_cyan]Cloudflare[/bright_cyan]"
            else:
                title = raw_title or "Title not found 🫤"
                if is_cf:
                    title = f"{title}  [bright_cyan][CF][/bright_cyan]"

            status = resp.status_code
            body   = resp.text or ""
            blen   = len(resp.content)

            # short redirect summary for the table
            redirect_info = ""
            if getattr(resp, "history", None):
                hosts = []
                for r in resp.history:
                    try:
                        h = urlparse(str(r.headers.get("location","") or r.url)).hostname
                    except Exception:
                        h = None
                    if h and (not hosts or hosts[-1] != h):
                        hosts.append(h)
                if hosts:
                    redirect_info = f"→ {len(resp.history)} • {hosts[-1]}"
            elif manual_hosts:
                redirect_info = f"→ {len(manual_hosts)} • {manual_hosts[-1]}"

            # filters
            if only_active and not (status and 200 <= status < 600):
                return None

            if status_code:
                allowed = []
                for chunk in str(status_code).split(","):
                    chunk = chunk.strip()
                    if not chunk: continue
                    if chunk.endswith("xx") and len(chunk) == 3:
                        base = int(chunk[0]) * 100
                        allowed.extend(range(base, base+100))
                    elif "-" in chunk:
                        a,b = chunk.split("-",1)
                        try:
                            a,b = int(a), int(b)
                            allowed.extend(range(min(a,b), max(a,b)+1))
                        except ValueError:
                            pass
                    else:
                        try:
                            allowed.append(int(chunk))
                        except ValueError:
                            pass
                if allowed and status not in set(allowed):
                    return None

            if excl_status and status in {int(s) for s in str(excl_status).split(",") if s.strip().isdigit()}:
                return None

            if content_len:
                if isinstance(content_len, tuple):
                    lo,hi = content_len
                else:
                    # supports "100-200" or "1500"
                    if "-" in str(content_len):
                        a,b = str(content_len).split("-",1)
                        lo,hi = int(a), int(b)
                    else:
                        lo,hi = int(content_len), int(content_len)
                if not (lo <= blen <= hi):
                    return None

            if exclude_len:
                excl = set()
                for part in str(exclude_len).split(","):
                    part = part.strip()
                    if not part: continue
                    if "-" in part:
                        a,b = part.split("-",1)
                        try:
                            a,b = int(a), int(b)
                            excl.update(range(min(a,b), max(a,b)+1))
                        except ValueError:
                            pass
                    elif part.isdigit():
                        excl.add(int(part))
                if blen in excl:
                    return None

            if title_search and not title_search(raw_title or ""):
                return None

            if body_search and not body_search(body):
                return None

            tls = None
            if tls_wanted and hostname and url.startswith("https://"):
                tls = grab_tls_info(hostname, 443, timeout=timeout)

            row = {
                "url": url,
                "ip": ip if print_ip else "-",
                "status": status,
                "title": title,
                "length": blen,
                "headers": dict(resp.headers),
                "redirect": redirect_info,
            }
            if tls_wanted:
                row["tls"] = tls

            # on-demand printing (live mode prints elsewhere)
            if not no_print and not (as_json or as_csv):
                tbl = _new_live_table()
                _append_row(tbl, row)
                console.print(tbl)

            if as_json and not no_print:
                console.print_json(json.dumps(row, ensure_ascii=False, indent=2))

            if as_csv and not no_print:
                safe_title = (raw_title or "").replace('"','""')
                console.print(f'{url},{ip},{status},{blen},"{safe_title}"')

            if output:
                with open(output, "a", encoding="utf-8") as f:
                    f.write(f"{url} | {ip} | {status} | {raw_title or 'Title not found'}\n")

            return row

        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError, httpx.HTTPError) as e:
            attempt += 1
            last_exc = e
            if attempt > retries:
                if only_active:
                    return None
                msg = str(e)
                row = {
                    "url": url,
                    "ip": "-",
                    "status": None,
                    "title": f"[red]ERR:[/red] {msg}",
                    "length": 0,
                    "headers": {},
                    "redirect": "",
                }
                if not no_print and not (as_json or as_csv):
                    tbl = _new_live_table(); _append_row(tbl, row); console.print(tbl)
                return row
            else:
                if not quiet_retries and not no_print:
                    console.print(Panel(f"[yellow]Retry {attempt}/{retries}…[/yellow]", title="Network", border_style="yellow"))
                continue

        except KeyboardInterrupt:
            raise

        except Exception as e:
            if only_active:
                return None
            row = {
                "url": url,
                "ip": "-",
                "status": None,
                "title": f"[red]ERR:[/red] {type(e).__name__}: {e}",
                "length": 0,
                "headers": {},
                "redirect": "",
            }
            return row

# ---------- batch runner ----------

def check_many(urls, threads=5, show_progress=True, show_final=False, show_live=True, **kwargs):
    """
    Run many checks in parallel. Progress bar & optional live table make it nice.
    JSON/CSV modes go quiet by default. simple and fast.
    """
    results = []
    total = len(urls)

    # worker calls should not print; UI is managed here
    wkwargs = dict(kwargs)
    wkwargs["use_spinner"] = False
    wkwargs["quiet_retries"] = True
    wkwargs["no_print"] = True

    if total == 0:
        return results

    # if exporting, keep the terminal clean
    if wkwargs.get("as_json") or wkwargs.get("as_csv"):
        show_progress = False
        show_final = False
        show_live = False

    if not show_progress:
        with ThreadPoolExecutor(max_workers=threads) as executor:
            fut = {executor.submit(check_status, url=u, **wkwargs): u for u in urls}
            for f in as_completed(fut):
                try:
                    r = f.result()
                    if r is not None:
                        results.append(r)
                except KeyboardInterrupt:
                    executor.shutdown(cancel_futures=True)
                    console.print("\n[yellow]Exited[/yellow]")
                    return results
                except Exception as e:
                    console.print(f"[red]Thread error:[/red] {e}")
        if show_final and results:
            print_results_table(results, show_ip=True)
        return results

    # with progress (and optional live table)
    progress = Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[bold cyan]Scanning[/]"),
        BarColumn(bar_width=None),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TextColumn("{task.completed}/{task.total}"),
        TextColumn("• elapsed:"), TimeElapsedColumn(),
        TextColumn("• eta:"), TimeRemainingColumn(),
        transient=False,
        console=console,
    )
    table = _new_live_table() if show_live else None
    lock = threading.Lock()
    group = progress if not show_live else Group(progress, table)

    try:
        with Live(group, console=console, refresh_per_second=20):
            task_id = progress.add_task("check_many", total=total)
            with ThreadPoolExecutor(max_workers=threads) as executor:
                fut = {executor.submit(check_status, url=u, **wkwargs): u for u in urls}
                for f in as_completed(fut):
                    try:
                        r = f.result()
                        if r is not None:
                            results.append(r)
                            if show_live:
                                with lock:
                                    _append_row(table, r)
                    except KeyboardInterrupt:
                        executor.shutdown(cancel_futures=True)
                        raise
                    except Exception as e:
                        console.print(f"[red]Thread error:[/red] {e}")
                    finally:
                        progress.advance(task_id, 1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Exited[/yellow]")
        return results

    if show_final and results:
        print_results_table(results, show_ip=True)

    return results
