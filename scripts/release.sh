#!/usr/bin/env bash
set -euo pipefail
python3 -m pip install -U build twine
python3 -m build
ls -l dist/
echo
echo "Upload with:"
echo "  python3 -m twine upload dist/*"
