"""Inspect a local Painter smart-material container without modifying it."""
import argparse
import hashlib
import json
import re
import zlib
from pathlib import Path


def inspect(path):
    data = path.read_bytes()
    sections = []
    # Painter stores several independent archives/serialized blocks in one file.
    for signature, kind in [(b"7z\xbc\xaf\x27\x1c", "7z"), (b"PK\x03\x04", "zip")]:
        for match in re.finditer(re.escape(signature), data):
            sections.append({"offset": match.start(), "type": kind})
    strings = [m.group().decode("utf-8", "replace") for m in re.finditer(rb"[\x20-\x7e]{5,}", data)]
    decoded = []
    for match in re.finditer(rb"\x78[\x01\x9c\xda]", data):
        try:
            block = zlib.decompress(data[match.start():])
        except zlib.error:
            continue
        if len(block) > 100:
            decoded.append((match.start(), block))
    return data, {"source": str(path), "sha256": hashlib.sha256(data).hexdigest(),
                  "bytes": len(data), "archives": sorted(sections, key=lambda x: x["offset"]),
                  "strings": strings, "zlib_blocks": [{"offset": o, "bytes": len(b)} for o, b in decoded]}, decoded


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data, report, blocks = inspect(args.source)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "inspection.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for i, entry in enumerate(report["archives"]):
        (args.output / f"archive_{i}_{entry['offset']}.{entry['type']}").write_bytes(data[entry["offset"]:])
    for offset, block in blocks:
        (args.output / f"zlib_{offset}.bin").write_bytes(block)
    import h5py
    with h5py.File(args.source, "r") as container:
        def extract(name, obj):
            if isinstance(obj, h5py.Dataset):
                print("DATASET", name, obj.shape, obj.dtype, dict(obj.attrs))
                target = args.output / "container" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(obj[()].tobytes())
                if name.startswith("preset") or name == "resources.toc":
                    raw = obj[()].tobytes()
                    print(name, "HEADER", raw[:80].hex(" "))
                    (target.parent / (target.name + ".hex.txt")).write_text("\n".join(
                        f"{i:08x}: {raw[i:i+16].hex(' '):47}  {''.join(chr(c) if 32 <= c < 127 else '.' for c in raw[i:i+16])}"
                        for i in range(0, len(raw), 16)), encoding="utf-8")
                    (target.parent / (target.name + ".strings.txt")).write_text("\n".join(
                        f"{m.start():08x}: {m.group().decode('ascii')}" for m in re.finditer(rb"[\x20-\x7e]{3,}", raw)), encoding="utf-8")
        container.visititems(extract)
    print(json.dumps({k: v for k, v in report.items() if k != "strings"}, indent=2))
    print("Header:", data[:256].hex(" "))
    print("\n".join(s for s in report["strings"] if re.search(r"machin|mask|metal|rust|dirt|preset|resource|grunge|curvature|\.sbs|\.bin", s, re.I)))
