import json
import sys
from pathlib import Path

def compact(value):
    if isinstance(value, dict):
        return {k: compact(v) for k,v in value.items() if k not in ('perChannelBlending', 'GUIcollapsedState')}
    if isinstance(value, list):
        return [compact(v) for v in value]
    return value

path = Path(sys.argv[1])
result = compact(json.loads(path.read_text()))
path.with_suffix('.compact.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
def walk(v, stack=''):
    if isinstance(v, dict):
        if v.get('label'):
            stack += '/' + v['label']
            print(stack, v.get('_type'), 'enabled', v.get('enabled'))
        if 'identifier' in v and 'value' in v:
            print(stack, v['identifier'], v['value'])
        for item in v.values():
            walk(item, stack)
    elif isinstance(v, list):
        for item in v:
            walk(item, stack)
walk(result)
