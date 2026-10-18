"""Inventory a local Painter project using read sharing, preserving the original."""
import json
import sys
from pathlib import Path
import h5py
import win32con
import win32file

source, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
snapshot = out / source.name
handle = win32file.CreateFile(str(source), win32con.GENERIC_READ,
    win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
    None, win32con.OPEN_EXISTING, 0, None)
try:
    with snapshot.open('wb') as target:
        while True:
            _, data = win32file.ReadFile(handle, 1024 * 1024)
            if not data:
                break
            target.write(data)
finally:
    handle.Close()
inventory = []
with h5py.File(snapshot, 'r', locking=False) as project:
    def visit(name, obj):
        if isinstance(obj, h5py.Dataset):
            entry = {'name': name, 'shape': obj.shape, 'dtype': str(obj.dtype),
                     'bytes': obj.size * obj.dtype.itemsize}
            inventory.append(entry)
            raw = obj[()].tobytes()
            if not name.startswith('texture-cache/'):
                target = out / 'datasets' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                entry['header'] = raw[:64].hex(' ')
    project.visititems(visit)
(out / 'inventory.json').write_text(json.dumps(inventory, indent=2), encoding='utf-8')
print(json.dumps(inventory, indent=2))
