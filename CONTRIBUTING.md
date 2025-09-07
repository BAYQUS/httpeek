# Contributing

Thanks for considering a contribution!

## Dev setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
pip install -e .
```

## Branch & PR
- Branch off `main`.
- Keep PRs small and focused.
- If you change flags or behavior, update README/cheatsheet.

## Style
- Python 3.9+; keep deps minimal.
- Avoid breaking the CLI unless necessary—document clearly when you must.

## Tests
- Keep tests deterministic (mock HTTP if possible).
- At minimum, ensure `httpeek --help` prints without crashing.

## Security
See `SECURITY.md` — avoid public disclosure of vulnerabilities.
