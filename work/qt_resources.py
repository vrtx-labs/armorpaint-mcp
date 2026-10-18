"""Decode the QDataStream maps used by Painter 1.7 image resources."""
import struct
from pathlib import Path
import json
import sys


class QtReader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def number(self, fmt):
        value, = struct.unpack_from('>' + fmt, self.data, self.pos)
        self.pos += struct.calcsize(fmt)
        return value

    def blob(self):
        size = self.number('I')
        if size == 0xffffffff:
            return b''
        value = self.data[self.pos:self.pos + size]
        self.pos += size
        return value

    def string(self):
        return self.blob().decode('utf-16-be')

    def variant(self):
        tag, null = self.number('I'), self.number('B')
        if tag == 0:
            return None
        if tag in (2, 3, 4, 5, 6, 1):
            return self.number({1:'B', 2:'i', 3:'I', 4:'q', 5:'Q', 6:'d'}[tag])
        if tag == 10:
            return self.string()
        if tag == 11:
            return [self.string() for _ in range(self.number('I'))]
        if tag == 12:
            return self.blob()
        if tag == 8:
            return self.mapping()
        if tag == 9:
            return [self.variant() for _ in range(self.number('I'))]
        raise ValueError(f'Unknown Qt type {tag} at {self.pos - 5:x}')

    def mapping(self):
        result = {}
        for _ in range(self.number('I')):
            key = self.string()
            result[key] = self.variant()
        return result


if __name__ == '__main__':
    root = Path(sys.argv[1])
    for path in root.iterdir():
        if path.is_file() and path.suffix not in ('.json', '.sbsar', '.shader'):
            raw = path.read_bytes()
            reader = QtReader(raw)
            result = reader.mapping()
            printable = {k: ({'bytes':len(v), 'header':v[:80].hex(' ')} if isinstance(v, bytes) else v) for k,v in result.items()}
            printable['trailing'] = {'offset':reader.pos, 'size':len(raw)-reader.pos, 'header':raw[reader.pos:reader.pos+32].hex(' ')}
            print(path.name, json.dumps(printable, indent=2))
            path.with_suffix('.json').write_text(json.dumps(printable, indent=2), encoding='utf-8')
