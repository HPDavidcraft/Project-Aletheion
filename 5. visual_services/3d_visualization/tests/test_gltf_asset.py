import base64
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from gltf_asset import GltfValidationError, ModelAsset3D, inspect_glb
from viewer_config import build_viewer_config


JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942


def make_glb(document, binary=None):
    json_bytes = json.dumps(document, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * (-len(json_bytes) % 4)
    chunks = [struct.pack("<II", len(json_bytes), JSON_CHUNK) + json_bytes]
    if binary is not None:
        binary += b"\0" * (-len(binary) % 4)
        chunks.append(struct.pack("<II", len(binary), BIN_CHUNK) + binary)
    body = b"".join(chunks)
    return struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body


class GltfAssetTests(unittest.TestCase):
    def write_model(self, content):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "model.glb"
        path.write_bytes(content)
        return path

    def test_inspection_reports_file_hash_and_embedded_bin(self):
        payload = make_glb(
            {
                "asset": {"version": "2.0", "generator": "test"},
                "buffers": [{"byteLength": 4}],
                "scenes": [{}],
                "scene": 0,
            },
            b"mesh",
        )
        path = self.write_model(payload)

        result = inspect_glb(path)

        self.assertEqual(result.file_size_bytes, len(payload))
        self.assertEqual(result.checksum_sha256, hashlib.sha256(payload).hexdigest())
        self.assertEqual(result.generator, "test")
        self.assertEqual(result.scene_count, 1)

    def test_rejects_bad_header_version_and_declared_length(self):
        valid = make_glb({"asset": {"version": "2.0"}})
        cases = (
            b"nope" + valid[4:],
            struct.pack("<4sII", b"glTF", 1, len(valid)) + valid[12:],
            struct.pack("<4sII", b"glTF", 2, len(valid) + 4) + valid[12:],
        )
        for content in cases:
            with self.subTest(content=content[:12]):
                with self.assertRaises(GltfValidationError):
                    inspect_glb(self.write_model(content))

    def test_rejects_invalid_chunk_order_and_alignment(self):
        valid = make_glb({"asset": {"version": "2.0"}})
        first_chunk_not_json = bytearray(valid)
        struct.pack_into("<I", first_chunk_not_json, 16, BIN_CHUNK)
        invalid_alignment = bytearray(valid)
        struct.pack_into("<I", invalid_alignment, 12, 3)
        for content in (bytes(first_chunk_not_json), bytes(invalid_alignment)):
            with self.assertRaises(GltfValidationError):
                inspect_glb(self.write_model(content))

    def test_rejects_external_resources_and_invalid_embedded_base64(self):
        external = {
            "asset": {"version": "2.0"},
            "buffers": [{"byteLength": 4, "uri": "https://example.test/data.bin"}],
        }
        invalid_base64 = {
            "asset": {"version": "2.0"},
            "buffers": [
                {
                    "byteLength": 4,
                    "uri": "data:application/octet-stream;base64,!!!!",
                }
            ],
        }
        for document in (external, invalid_base64):
            with self.subTest(document=document):
                with self.assertRaises(GltfValidationError):
                    inspect_glb(self.write_model(make_glb(document)))

    def test_embedded_buffer_must_match_declared_length(self):
        encoded = base64.b64encode(b"abc").decode("ascii")
        document = {
            "asset": {"version": "2.0"},
            "buffers": [
                {
                    "byteLength": 4,
                    "uri": f"data:application/octet-stream;base64,{encoded}",
                }
            ],
        }
        with self.assertRaisesRegex(GltfValidationError, "does not match"):
            inspect_glb(self.write_model(make_glb(document)))

    def test_rejects_duplicate_json_keys_and_invalid_scene_index(self):
        duplicate = b'{"asset":{"version":"2.0"},"asset":{"version":"2.0"}}'
        duplicate += b" " * (-len(duplicate) % 4)
        duplicate_glb = struct.pack("<4sII", b"glTF", 2, 20 + len(duplicate))
        duplicate_glb += struct.pack("<II", len(duplicate), JSON_CHUNK) + duplicate
        out_of_range = make_glb(
            {"asset": {"version": "2.0"}, "scenes": [{}], "scene": 1}
        )
        for content in (duplicate_glb, out_of_range):
            with self.assertRaises(GltfValidationError):
                inspect_glb(self.write_model(content))

    def test_media_asset_payload_obeys_shared_schema(self):
        inspection = inspect_glb(
            self.write_model(make_glb({"asset": {"version": "2.0"}}))
        )
        asset = ModelAsset3D(
            id=uuid4(),
            media_gallery_id=uuid4(),
            source_object_uri="s3://pleroma-models/model.glb",
            rights_statement_uri="https://rights.example.test/model",
            created_by=uuid4(),
            inspection=inspection,
            is_archival_master=True,
            is_lossless=True,
            resolution_description="  2 mm  ",
        )

        payload = asset.writeback_payload()

        self.assertEqual(payload["asset_type"], "3d_model")
        self.assertEqual(payload["mime_type"], "model/gltf-binary")
        self.assertEqual(payload["checksum_sha256"], inspection.checksum_sha256)
        self.assertIsNone(payload["iiif_service_uri"])
        self.assertEqual(payload["resolution_description"], "2 mm")

    def test_archival_asset_requires_lossless_and_resolution(self):
        inspection = inspect_glb(
            self.write_model(make_glb({"asset": {"version": "2.0"}}))
        )
        arguments = {
            "id": uuid4(),
            "media_gallery_id": uuid4(),
            "source_object_uri": "minio://models/model.glb",
            "rights_statement_uri": "https://rights.example.test/model",
            "created_by": uuid4(),
            "inspection": inspection,
            "is_archival_master": True,
        }
        for changes in ({"is_lossless": False}, {"is_lossless": True}):
            with self.subTest(changes=changes):
                with self.assertRaises(GltfValidationError):
                    ModelAsset3D(**(arguments | changes))

    def test_viewer_config_requires_allowlisted_https_without_query(self):
        config = build_viewer_config(
            asset_id=uuid4(),
            delivery_url="https://models.example.test/assets/abc.glb",
            checksum_sha256="a" * 64,
            alt_text="A reconstructed ceramic vessel",
            allowed_hosts=("models.example.test",),
        )
        self.assertFalse(config["controls"]["autoplay"])
        self.assertTrue(config["controls"]["immersive_mode_requires_user_action"])
        for url in (
            "http://models.example.test/assets/model.glb",
            "https://evil.example.test/assets/model.glb",
            "https://models.example.test/assets/model.glb?signature=secret",
            "https://user@models.example.test/assets/model.glb",
        ):
            with self.subTest(url=url):
                with self.assertRaises(GltfValidationError):
                    build_viewer_config(
                        asset_id=uuid4(),
                        delivery_url=url,
                        checksum_sha256="a" * 64,
                        alt_text="Model",
                        allowed_hosts=("models.example.test",),
                    )


if __name__ == "__main__":
    unittest.main()
