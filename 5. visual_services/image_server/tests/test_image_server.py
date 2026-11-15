import hashlib
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from PIL import Image

from image_pipeline import (
    ImageIngestError,
    build_media_asset_payload,
    create_pyramidal_tiff,
    inspect_image,
)
from iiif_presentation import (
    IIIFImageAsset,
    IIIFValidationError,
    build_annotation_version_payload,
    build_manifest,
)


class ImagePipelineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def create_jpeg(self, name="source.jpg", size=(128, 64)):
        path = self.directory / name
        image = Image.new("RGB", size, color=(30, 80, 120))
        exif = Image.Exif()
        exif[271] = "PLEROMA Test Camera"
        image.save(path, format="JPEG", exif=exif)
        return path

    def test_inspection_hashes_image_and_extracts_exif(self):
        path = self.create_jpeg()
        content = path.read_bytes()

        result = inspect_image(path)

        self.assertEqual(result.mime_type, "image/jpeg")
        self.assertEqual(result.width, 128)
        self.assertEqual(result.height, 64)
        self.assertEqual(result.checksum_sha256, hashlib.sha256(content).hexdigest())
        self.assertEqual(
            result.exif_xmp_metadata["exif"]["Make"],
            "PLEROMA Test Camera",
        )

    def test_inspects_png(self):
        path = self.directory / "source.png"
        Image.new("RGB", (24, 16), color=(1, 2, 3)).save(path)

        result = inspect_image(path)

        self.assertEqual(result.mime_type, "image/png")
        self.assertEqual((result.width, result.height), (24, 16))

    def test_rejects_bad_image_and_pixel_limit(self):
        bad_path = self.directory / "broken.jpg"
        bad_path.write_bytes(b"not an image")
        with self.assertRaises(ImageIngestError):
            inspect_image(bad_path)

        path = self.create_jpeg(size=(32, 32))
        with self.assertRaisesRegex(ImageIngestError, "pixel limit"):
            inspect_image(path, max_pixels=100)

    def test_rejects_multipage_tiff(self):
        path = self.directory / "pages.tif"
        Image.new("RGB", (8, 8)).save(
            path,
            format="TIFF",
            save_all=True,
            append_images=[Image.new("RGB", (8, 8))],
        )
        with self.assertRaisesRegex(ImageIngestError, "separate assets"):
            inspect_image(path)

    def test_creates_pyramidal_tiff_without_changing_master(self):
        source = self.create_jpeg()
        source_checksum = hashlib.sha256(source.read_bytes()).hexdigest()
        output = self.directory / "pyramids" / "asset.tif"

        inspection, pyramid = create_pyramidal_tiff(source, output)

        self.assertEqual(inspection.checksum_sha256, source_checksum)
        self.assertEqual(pyramid.width, 128)
        self.assertEqual(pyramid.height, 64)
        self.assertTrue(output.is_file())
        self.assertEqual(
            pyramid.checksum_sha256,
            hashlib.sha256(output.read_bytes()).hexdigest(),
        )
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), source_checksum)
        with self.assertRaisesRegex(ImageIngestError, "already exists"):
            create_pyramidal_tiff(source, output)

    def test_pyramid_applies_exif_orientation(self):
        source = self.directory / "rotated.jpg"
        image = Image.new("RGB", (128, 64), color=(100, 30, 50))
        exif = Image.Exif()
        exif[274] = 6
        image.save(source, format="JPEG", exif=exif)

        _, pyramid = create_pyramidal_tiff(source, self.directory / "rotated.tif")

        self.assertEqual((pyramid.width, pyramid.height), (64, 128))

    def test_media_asset_payload_records_master_and_service(self):
        inspection = inspect_image(self.create_jpeg())
        payload = build_media_asset_payload(
            inspection,
            asset_id=uuid4(),
            media_gallery_id=uuid4(),
            source_object_uri="s3://pleroma-media/masters/asset.jpg",
            iiif_service_uri="https://iiif.example.test/iiif/3/asset.tif",
            iiif_manifest_uri="https://api.example.test/iiif/manifests/asset",
            rights_statement_uri="https://rights.example.test/license",
            created_by=uuid4(),
            asset_type="plan",
        )
        self.assertEqual(payload["asset_type"], "plan")
        self.assertEqual(payload["checksum_sha256"], inspection.checksum_sha256)
        self.assertEqual(payload["file_size_bytes"], inspection.file_size_bytes)
        self.assertEqual(
            payload["source_object_uri"],
            "s3://pleroma-media/masters/asset.jpg",
        )


class IIIFTests(unittest.TestCase):
    def setUp(self):
        self.asset = IIIFImageAsset(
            asset_id=uuid4(),
            service_uri="https://iiif.example.test/iiif/3/asset.tif",
            label="Inscribed pottery sherd",
            alt_text="A pottery sherd with a short inscription",
            width=1200,
            height=800,
            rights_statement_uri="https://rights.example.test/license",
        )

    def test_manifest_has_presentation_and_image_api_3_links(self):
        document = build_manifest(
            manifest_uri="https://api.example.test/iiif/manifest/1",
            label="Find 1 media",
            rights_holder="PLEROMA Research Project",
            assets=(self.asset,),
        )
        canvas = document["items"][0]
        body = canvas["items"][0]["items"][0]["body"]
        self.assertEqual(document["@context"], "http://iiif.io/api/presentation/3/context.json")
        self.assertEqual(document["type"], "Manifest")
        self.assertEqual(body["service"][0]["type"], "ImageService3")
        self.assertEqual(body["service"][0]["id"], self.asset.service_uri)
        self.assertEqual(body["width"], 1200)

    def test_manifest_rejects_mixed_rights_and_untrusted_service(self):
        other_rights = IIIFImageAsset(
            asset_id=uuid4(),
            service_uri="https://iiif.example.test/iiif/3/other.tif",
            label="Another image",
            alt_text="Another image",
            width=20,
            height=10,
            rights_statement_uri="https://rights.example.test/different",
        )
        with self.assertRaisesRegex(IIIFValidationError, "differing rights"):
            build_manifest(
                manifest_uri="https://api.example.test/manifest",
                label="Gallery",
                rights_holder="Project",
                assets=(self.asset, other_rights),
            )
        invalid = IIIFImageAsset(
            asset_id=uuid4(),
            service_uri="http://iiif.example.test/iiif/3/asset.tif",
            label="Image",
            alt_text="Image",
            width=20,
            height=10,
            rights_statement_uri=self.asset.rights_statement_uri,
        )
        with self.assertRaises(IIIFValidationError):
            build_manifest(
                manifest_uri="https://api.example.test/manifest",
                label="Gallery",
                rights_holder="Project",
                assets=(invalid,),
            )

    def test_annotation_payload_matches_append_only_version_table(self):
        payload = build_annotation_version_payload(
            media_asset_id=self.asset.asset_id,
            version_number=2,
            annotation_page_uri="https://api.example.test/annotations/asset/v2",
            annotations=(
                {
                    "id": "https://api.example.test/annotations/1",
                    "type": "Annotation",
                    "motivation": "commenting",
                    "body": {"type": "TextualBody", "value": "Inscription"},
                    "target": "https://api.example.test/canvas/1",
                },
            ),
            created_by=uuid4(),
        )
        self.assertEqual(payload["version_number"], 2)
        self.assertEqual(payload["annotation_layer"]["type"], "AnnotationPage")
        self.assertEqual(len(payload["annotation_layer"]["items"]), 1)
        with self.assertRaises(IIIFValidationError):
            build_annotation_version_payload(
                media_asset_id=self.asset.asset_id,
                version_number=0,
                annotation_page_uri="https://api.example.test/annotations/asset/v0",
                annotations=(),
                created_by=uuid4(),
            )


if __name__ == "__main__":
    unittest.main()
