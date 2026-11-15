"""Command-line GLB structural inspector."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

if __package__:
    from .gltf_asset import inspect_glb
else:
    from gltf_asset import inspect_glb


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect and SHA-256 hash a glTF 2.0 binary model without uploading it."
    )
    parser.add_argument("model", type=Path, help="Local .glb file to inspect")
    parser.add_argument(
        "--max-json-bytes",
        type=int,
        default=16_000_000,
        help="Maximum embedded JSON chunk size",
    )
    arguments = parser.parse_args()
    print(
        json.dumps(
            asdict(
                inspect_glb(
                    arguments.model,
                    max_json_chunk_bytes=arguments.max_json_bytes,
                )
            ),
            allow_nan=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
