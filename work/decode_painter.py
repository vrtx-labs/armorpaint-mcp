"""Read Painter 1.x typed preset data; offsets are checked against the stream."""
import json
import struct
import sys
from pathlib import Path


class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 12

    def number(self, fmt):
        result = struct.unpack_from('<' + fmt, self.data, self.pos)
        self.pos += struct.calcsize('<' + fmt)
        return result[0] if len(result) == 1 else list(result)

    def string(self):
        size = self.number('I')
        if size > len(self.data) - self.pos:
            raise ValueError(f'Invalid string at {self.pos:x}')
        result = self.data[self.pos:self.pos + size].decode('utf-8')
        self.pos += size
        return result

    def value(self):
        start = self.pos
        tag = self.number('B')
        if tag in (0x12, 0x14):
            if self.number('B') == 255:
                return None
            end = self.number('I')
            result = {'_type': self.string()}
            for _ in range(self.number('H')):
                key = self.string()
                result[key] = self.value()
            if self.pos != end:
                raise ValueError(f'Object end {self.pos:x} != {end:x}, {result}')
            return result
        if tag in (0x11, 0x13):
            end = self.number('I')
            result = [self.value() for _ in range(self.number('I'))]
            if self.pos != end:
                raise ValueError(f'Array end {self.pos:x} != {end:x}')
            return result
        if tag == 0x10:
            return self.string()
        if tag == 0x0a:
            return bool(self.number('B'))
        if tag == 9:
            return self.number('q')
        if tag == 0x0b:
            return self.number('I')
        if tag == 0x0c:
            return self.number('Q')
        if 5 <= tag <= 8:
            return self.number('i' * (tag - 4))
        if tag == 0x0f:
            return self.number('ff')
        if tag == 0x0d:
            return self.number('f' * 9)
        if tag == 0x0e:
            return self.number('f' * 16)
        if 1 <= tag <= 4:
            return self.number('f' * tag)
        raise ValueError(f'Unknown tag {tag:x} at {start:x}: {self.data[start:start+64].hex(" ")}')


if __name__ == '__main__':
    path = Path(sys.argv[1])
    reader = Reader(path.read_bytes())
    result = reader.value()
    path.with_suffix('.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('Decoded', path, reader.pos)
