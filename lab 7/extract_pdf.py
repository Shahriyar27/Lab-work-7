"""Одноразовое извлечение текста из предоставленного PDF без библиотек."""
import pathlib
import re
import zlib
import sys

sys.stdout.reconfigure(encoding='utf-8')

source = pathlib.Path(r'C:\Users\shahk\Downloads\Lab-7.pdf').read_bytes()
objects = {int(n): s for n, s in re.findall(rb'(\d+) 0 obj\s*(.*?)endobj', source, re.S)}

def stream(obj):
    data = re.search(rb'stream\r?\n(.*?)\r?\nendstream', obj, re.S)[1]
    return zlib.decompress(data) if b'/FlateDecode' in obj else data

maps = {}
for number, obj in objects.items():
    ref = re.search(rb'/ToUnicode (\d+) 0 R', obj)
    if ref:
        cmap = stream(objects[int(ref[1])])
        mapping = {}
        for a, b, c in re.findall(rb'<([0-9a-f]+)>\s*<([0-9a-f]+)>\s*<([0-9a-f]+)>', cmap):
            for code in range(int(a, 16), int(b, 16) + 1):
                mapping[code] = chr(int(c, 16) + code - int(a, 16))
        maps[number] = mapping

pages = []
for obj in objects.values():
    if not re.search(rb'/Type /Page\s', obj):
        continue
    resources = objects[int(re.search(rb'/Resources (\d+) 0 R', obj)[1])]
    fonts = {name: maps.get(int(n), {}) for name, n in re.findall(rb'/(TT\d+) (\d+) 0 R', resources)}
    content = stream(objects[int(re.search(rb'/Contents (\d+) 0 R', obj)[1])])
    font = {}
    parts = []
    for match in re.finditer(rb'/(TT\d+)\s+[\d.]+\s+Tf|\(((?:\\.|[^\\)])*)\)|\bET\b', content, re.S):
        if match[1]:
            font = fonts.get(match[1], {})
        elif match[2] is not None:
            raw = re.sub(rb'\\([0-7]{1,3}|.)', lambda m: bytes([int(m[1],8)]) if m[1].isdigit() else {b'n':b'\n',b'r':b'\r',b't':b'\t'}.get(m[1],m[1]), match[2])
            parts.append(''.join(font.get(c, '?') for c in raw))
        else:
            parts.append('\n')
    pages.append(''.join(parts))
pathlib.Path('assignment.txt').write_text('\n\n'.join(f'PAGE {i+1}\n{p}' for i,p in enumerate(pages)), encoding='utf-8')
print(pathlib.Path('assignment.txt').read_text(encoding='utf-8'))
