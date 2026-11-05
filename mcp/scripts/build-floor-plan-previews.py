"""Build and verify first-page previews; no PDF renderer is needed at runtime."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

def valid_png(data):
    """Reject incomplete output before publishing; verify every PNG chunk CRC."""
    if not data.startswith(PNG_SIGNATURE):
        return False
    offset = 8
    seen_header = False
    seen_data = False
    while offset + 12 <= len(data):
        length = struct.unpack("!I", data[offset:offset + 4])[0]
        end = offset + 12 + length
        if end > len(data):
            return False
        kind = data[offset + 4:offset + 8]
        body = data[offset + 8:offset + 8 + length]
        crc = struct.unpack("!I", data[offset + 8 + length:end])[0]
        if zlib.crc32(kind + body) & 0xffffffff != crc:
            return False
        if not seen_header:
            if kind != b"IHDR" or length != 13 or not all(struct.unpack("!II", body[:8])):
                return False
            seen_header = True
        if kind == b"IDAT":
            seen_data = True
        if kind == b"IEND":
            return length == 0 and seen_data and end == len(data)
        offset = end
    return False

def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".preview-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o644)
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()

def build_previews(source, output, manifest_path, renderer, runner=subprocess.run, force=False):
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    pdfs = sorted(p for p in source.glob("*/*.pdf") if p.is_file())
    if not pdfs:
        raise ValueError("No building floor-plan PDFs found")
    def render(pdf):
        relative = pdf.relative_to(source)
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        preview = relative.with_name(relative.stem + "-" + digest[:12] + ".png")
        target = output / preview
        key = "/static/pdfs/" + relative.as_posix()
        url = "https://draw.tigerapps.org/static/previews/floor-plans/" + preview.as_posix()
        old = previous.get(key, {})
        data = target.read_bytes() if target.exists() else b""
        cached = (not force and old.get("sha256") == digest and old.get("url") == url
                  and old.get("preview_sha256") == hashlib.sha256(data).hexdigest() and valid_png(data))
        if not cached:
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=target.parent, prefix=".render-") as temporary:
                prefix = Path(temporary) / "page"
                runner([renderer, "-f", "1", "-l", "1", "-singlefile", "-scale-to", "1600", "-png", str(pdf), str(prefix)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60)
                data = prefix.with_suffix(".png").read_bytes()
                if not valid_png(data):
                    raise ValueError(f"Renderer produced an incomplete or corrupt PNG for {relative}")
                if hashlib.sha256(pdf.read_bytes()).hexdigest() != digest:
                    raise ValueError(f"PDF changed during rendering: {relative}")
                atomic_write(target, data)
        return key, {"url": url, "sha256": digest, "preview_sha256": hashlib.sha256(data).hexdigest()}
    with ThreadPoolExecutor(max_workers=4) as pool:
        manifest = dict(pool.map(render, pdfs))
    # Publish only after every preview was verified. Failed jobs preserve the old manifest.
    atomic_write(manifest_path, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())
    return manifest

def main():
    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=repo / "static/pdfs")
    parser.add_argument("--force", action="store_true", help="Regenerate verified previews too")
    args = parser.parse_args()
    renderer = shutil.which("pdftoppm")
    if not renderer:
        raise SystemExit("Install Poppler (brew install poppler / apt-get install poppler-utils), then retry.")
    source = args.source.resolve()
    if not source.is_dir():
        raise SystemExit("PDF source directory is missing; pass --source PATH_TO_TIGERDRAW/static/pdfs")
    output = repo / "static/previews/floor-plans"
    manifest = build_previews(source, output, repo / "static/previews/floor-plans.json", renderer, force=args.force)
    print(f"Verified {len(manifest)} previews ({sum(p.stat().st_size for p in output.rglob('*.png')) / 1024 / 1024:.1f} MiB)")

if __name__ == "__main__":
    main()
