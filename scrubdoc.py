"""Offline document transformations. No third-party dependencies."""
import csv
import hashlib
import io
import json
import re
import secrets
import string
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}
TOKEN = re.compile(r'【敏感项_[A-Za-z0-9]+】')


def parse_xml(data):
    # Keep namespace prefixes used by Word compatibility attributes.
    namespaces = dict(ET.iterparse(io.BytesIO(data), events=['start-ns']))
    for prefix, uri in namespaces.items():
        if not re.fullmatch(r'ns\d+', prefix):
            ET.register_namespace(prefix, uri)
    return ET.fromstring(data)


def serialize_xml(root):
    # Ignorable prefix lists can refer to namespaces not present in element names.
    # Removing this advisory attribute avoids dangling prefix references after ET serialization.
    for element in root.iter():
        for key in list(element.attrib):
            if key.endswith('}Ignorable'):
                del element.attrib[key]
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def token():
    return '【敏感项_' + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10)) + '】'


def validate(mapping):
    if not mapping or any(not a or not b or a == b for a, b in mapping.items()):
        raise ValueError('请选择敏感词，并填写不同于原文的非空替换词。')
    values = list(mapping.values())
    if len(values) != len(set(values)):
        raise ValueError('替换词不能重复。')
    if any(a in b for a in values for b in values if a != b):
        raise ValueError('替换词之间不能相互包含。')
    if any(a in b for a in mapping for b in values):
        raise ValueError('替换词不能包含任何敏感词。')


def replace(text, mapping, counts):
    if not mapping:
        return text
    pattern = re.compile('|'.join(re.escape(x) for x in sorted(mapping, key=len, reverse=True)))
    def sub(m):
        counts[m[0]] += 1
        return mapping[m[0]]
    return pattern.sub(sub, text)


def read_txt(data):
    for encoding in ('utf-8-sig', 'gb18030'):
        try:
            return data.decode(encoding), ('utf-8-sig' if data.startswith(b'\xef\xbb\xbf') else ('utf-8' if encoding == 'utf-8-sig' else encoding))
        except UnicodeDecodeError:
            pass
    raise ValueError('无法识别文本编码，请转换为 UTF-8。')


def word_parts(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            if name.startswith('word/') and name.endswith('.xml'):
                yield name, parse_xml(z.read(name))


def extract(path):
    path = Path(path)
    data = path.read_bytes()
    if path.suffix.lower() == '.txt':
        return read_txt(data)[0]
    if path.suffix.lower() != '.docx':
        raise ValueError('仅支持 DOCX 和 TXT。')
    return '\n'.join(''.join(t.text or '' for t in p.iter(f'{{{W}}}t'))
                     for _, root in word_parts(data) for p in root.iter(f'{{{W}}}p'))


def transform(source, destination, mapping, remove_images=False, sanitize=True):
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve() or destination.exists():
        raise ValueError('输出文件已存在或与原文件相同，请更换输出名称。')
    data = source.read_bytes()
    counts, removed = Counter(), 0
    if source.suffix.lower() == '.txt':
        text, encoding = read_txt(data)
        result = replace(text, mapping, counts).encode(encoding)
    elif source.suffix.lower() == '.docx':
        output = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(data)) as zin, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                name, content = item.filename, zin.read(item.filename)
                if name.startswith('word/') and name.endswith('.xml'):
                    root = parse_xml(content)
                    for parent in list(root.iter()):
                        for child in list(parent):
                            local = child.tag.split('}')[-1]
                            if sanitize and local in ('del', 'moveFrom', 'commentRangeStart', 'commentRangeEnd', 'commentReference'):
                                parent.remove(child)
                            elif remove_images and local in ('drawing', 'pict') and any(e.tag.split('}')[-1] in ('pic', 'imagedata', 'blip') for e in child.iter()):
                                parent.remove(child)
                                removed += 1
                    for p in root.iter(f'{{{W}}}p'):
                        # Limit to direct paragraph text, excluding nested text-box paragraphs.
                        nodes = []
                        def collect(el):
                            for ch in el:
                                if ch.tag == f'{{{W}}}p':
                                    continue
                                if ch.tag == f'{{{W}}}t':
                                    nodes.append(ch)
                                else:
                                    collect(ch)
                        collect(p)
                        original = ''.join(t.text or '' for t in nodes)
                        if not original or not mapping:
                            continue
                        pattern = re.compile('|'.join(re.escape(k) for k in sorted(mapping, key=len, reverse=True)))
                        spans, offset = [], 0
                        for node in nodes:
                            value = node.text or ''
                            spans.append((node, offset, offset + len(value)))
                            offset += len(value)
                        for match in reversed(list(pattern.finditer(original))):
                            counts[match[0]] += 1
                            first = True
                            for node, start, end in spans:
                                if start < match.end() and end > match.start():
                                    left, right = max(0, match.start()-start), min(end-start, match.end()-start)
                                    node.text = (node.text or '')[:left] + (mapping[match[0]] if first else '') + (node.text or '')[right:]
                                    node.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                                    first = False
                    if sanitize and ('comments' in name.lower()):
                        for child in list(root):
                            root.remove(child)
                    content = serialize_xml(root)
                elif remove_images and name.endswith('.rels'):
                    root = parse_xml(content)
                    for child in list(root):
                        if child.get('Type', '').endswith('/image') or child.get('Type', '').endswith('/thumbnail'):
                            root.remove(child)
                    content = serialize_xml(root)
                elif sanitize and name in ('docProps/core.xml', 'docProps/custom.xml', 'docProps/app.xml'):
                    root = parse_xml(content)
                    for child in list(root):
                        root.remove(child)
                    content = serialize_xml(root)
                # Remove bytes too: hidden/unreferenced images otherwise remain recoverable.
                if remove_images and (name.startswith('word/media/') or name.startswith('docProps/thumbnail.')):
                    continue
                zout.writestr(item, content)
        result = output.getvalue()
    else:
        raise ValueError('仅支持 DOCX 和 TXT。')
    with destination.open('xb') as f:
        f.write(result)
    return {'counts': dict(counts), 'removed_images': removed, 'sha256': hashlib.sha256(result).hexdigest()}


def inspect_restore(path, package):
    text = extract(path)
    mapping = package['mapping']
    current = {v: text.count(v) for v in mapping.values()}
    known = set(mapping.values())
    return {'counts': current, 'missing': [v for v, n in current.items() if not n],
            'unknown': sorted(set(TOKEN.findall(text)) - known)}


def load_package(path):
    obj = json.loads(Path(path).read_text(encoding='utf-8'))
    if obj.get('version') != 1 or not isinstance(obj.get('mapping'), dict):
        raise ValueError('不支持的还原包。')
    validate(obj['mapping'])
    return obj


def load_mapping(path):
    """Read a two-column CSV; a vocabulary without markers cannot restore text."""
    text, _ = read_txt(Path(path).read_bytes())
    rows = list(csv.reader(io.StringIO(text)))
    if rows and rows[0] and rows[0][0].strip().lower() in ('敏感词', 'term'):
        rows = rows[1:]
    mapping = {}
    for number, row in enumerate(rows, 2):
        if not row or not any(value.strip() for value in row):
            continue
        if len(row) != 2 or not all(value.strip() for value in row):
            raise ValueError(f'第 {number} 行需要两列：敏感词、替换标记。仅含敏感词的词库不能用于还原。')
        term, mark = (value.strip() for value in row)
        if term in mapping and mapping[term] != mark:
            raise ValueError(f'同一敏感词存在不同标记：{term}')
        mapping[term] = mark
    validate(mapping)
    return mapping


def import_terms(path):
    path = Path(path)
    text, _ = read_txt(path.read_bytes())
    if path.suffix.lower() == '.csv':
        rows = list(csv.reader(io.StringIO(text)))
        if rows and rows[0] and rows[0][0].lower() in ('敏感词', 'term'):
            rows = rows[1:]
        return [r[0].strip() for r in rows if r and r[0].strip()]
    return [x.strip() for x in text.splitlines() if x.strip()]
