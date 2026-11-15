"""Create a lossless tiled TIFF pyramid for Cantaloupe."""

from __future__ import annotations

import argparse
import json

from image_pipeline import create_pyramidal_tiff


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate an image and create a pyramidal TIFF derivative; "
            "the source master is not modified."
        )
    )
    parser.add_argument("source", help="JPEG, PNG, or TIFF master")
    parser.add_argument("output", help="New .tif/.tiff pyramid destination")
    parser.add_argument("--max-pixels", type=int, default=250_000_000)
    parser.add_argument("--timeout-seconds", type=float, default=600)
    arguments = parser.parse_args()

    inspection, pyramid = create_pyramidal_tiff(
        arguments.source,
        arguments.output,
        max_pixels=arguments.max_pixels,
        timeout_seconds=arguments.timeout_seconds,
    )
    print(
        json.dumps(
            {
                "source": {
                    "mime_type": inspection.mime_type,
                    "width": inspection.width,
                    "height": inspection.height,
                    "file_size_bytes": inspection.file_size_bytes,
                    "checksum_sha256": inspection.checksum_sha256,
                },
                "pyramid": {
                    "path": str(pyramid.path),
                    "width": pyramid.width,
                    "height": pyramid.height,
                    "file_size_bytes": pyramid.file_size_bytes,
                    "checksum_sha256": pyramid.checksum_sha256,
                },
            },
            allow_nan=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
