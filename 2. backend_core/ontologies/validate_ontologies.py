#!/usr/bin/env python3
"""Parse all Turtle files in this directory using RDFLib's rapper CLI."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ONTOLOGY_DIR = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Syntax-check each .ttl ontology in the current directory."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Turtle files to validate (defaults to all .ttl files beside this script)",
    )
    args = parser.parse_args()

    rapper = shutil.which("rapper")
    if not rapper:
        print(
            "RDF validator not found: install Raptor's rapper command to parse Turtle.",
            file=sys.stderr,
        )
        return 2

    files = args.paths or sorted(ONTOLOGY_DIR.glob("*.ttl"))
    if not files:
        print("No Turtle files found.", file=sys.stderr)
        return 2

    failed = False
    for path in files:
        result = subprocess.run(
            [rapper, "-i", "turtle", "-c", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            failed = True
            print(f"INVALID {path}:\n{result.stderr.strip()}", file=sys.stderr)
        else:
            print(f"VALID {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
