import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zlib

spec = importlib.util.spec_from_file_location("preview_builder", Path(__file__).resolve().parents[1] / "scripts/build-floor-plan-previews.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

def png():
    def chunk(kind, data):
        return struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data) & 0xffffffff)
    return builder.PNG_SIGNATURE + chunk(b"IHDR", struct.pack("!IIBBBBB", 2, 2, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress((b"\x00" + b"\x00\x00\x00" * 2) * 2)) + chunk(b"IEND", b"")

class PreviewBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "pdfs"
        (self.source / "patton").mkdir(parents=True)
        self.pdf = self.source / "patton/2.pdf"
        self.pdf.write_bytes(b"fixture PDF version 1")
        self.output = self.root / "previews"
        self.manifest = self.root / "manifest.json"
        self.calls = 0
    def tearDown(self):
        self.temp.cleanup()
    def runner(self, args, **kwargs):
        self.calls += 1
        Path(args[-1]).with_suffix(".png").write_bytes(png())
    def build(self, **kwargs):
        return builder.build_previews(self.source, self.output, self.manifest, "fixture-renderer", runner=kwargs.pop("runner", self.runner), **kwargs)
    def target(self, manifest):
        return self.output / manifest["/static/pdfs/patton/2.pdf"]["url"].split("/floor-plans/", 1)[1]
    def test_checksums_allow_verified_reuse_and_repair_corruption(self):
        first = self.build()
        self.assertEqual(len(first["/static/pdfs/patton/2.pdf"]["preview_sha256"]), 64)
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.build(), first)
        self.assertEqual(self.calls, 1)
        self.target(first).write_bytes(b"truncated output")
        self.assertEqual(self.build(), first)
        self.assertEqual(self.calls, 2)
        self.assertTrue(builder.valid_png(self.target(first).read_bytes()))
    def test_partial_failed_render_does_not_replace_published_files(self):
        first = self.build()
        before_manifest = self.manifest.read_bytes()
        before_image = self.target(first).read_bytes()
        def fail(args, **kwargs):
            Path(args[-1]).with_suffix(".png").write_bytes(b"partial PNG")
            raise subprocess.CalledProcessError(1, args)
        with self.assertRaises(subprocess.CalledProcessError):
            self.build(runner=fail, force=True)
        self.assertEqual(self.manifest.read_bytes(), before_manifest)
        self.assertEqual(self.target(first).read_bytes(), before_image)
        self.assertFalse(list(self.output.rglob(".render-*")))
        self.assertFalse(list(self.output.rglob(".preview-*")))
    def test_successful_process_with_incomplete_png_is_rejected(self):
        def incomplete(args, **kwargs):
            Path(args[-1]).with_suffix(".png").write_bytes(png()[:-8])
        with self.assertRaisesRegex(ValueError, "incomplete or corrupt"):
            self.build(runner=incomplete)
        self.assertFalse(self.manifest.exists())
        self.assertFalse(list(self.output.rglob("*.png")))
    def test_pdf_update_changes_preview_url_and_keeps_previous_asset(self):
        first = self.build()
        self.pdf.write_bytes(b"fixture PDF version 2")
        second = self.build()
        self.assertNotEqual(first["/static/pdfs/patton/2.pdf"]["url"], second["/static/pdfs/patton/2.pdf"]["url"])
        self.assertTrue(self.target(first).exists())
        self.assertTrue(self.target(second).exists())
    def test_crc_corruption_is_detected(self):
        data = bytearray(png()); data[20] ^= 1
        self.assertFalse(builder.valid_png(bytes(data)))
        self.assertTrue(builder.valid_png(png()))

if __name__ == "__main__":
    unittest.main()
