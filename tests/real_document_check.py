"""Run the real local sample through the same functions used by the GUI."""
import csv
import hashlib
import json
import posixpath
import sys
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scrubdoc as core


def structure(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        names = set(z.namelist())
        for name in names:
            if name.endswith(('.xml', '.rels')):
                ET.fromstring(z.read(name))
        missing = []
        for name in names:
            if not name.endswith('.rels'):
                continue
            base = posixpath.dirname(posixpath.dirname(name)) if name != '_rels/.rels' else ''
            for rel in ET.fromstring(z.read(name)):
                if rel.get('TargetMode') == 'External':
                    continue
                target = rel.get('Target', '')
                target = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(base, target))
                if target not in names:
                    missing.append(target)
        return {'media': sum(n.startswith('word/media/') for n in names), 'missing_relationship_targets': missing}


def main():
    source = next(Path('.').glob('*原文.docx'))
    folder = Path('test-results') / time.strftime('%Y%m%d_%H%M%S')
    folder.mkdir(parents=True)
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    original_text = core.extract(source)
    terms = ['钉钉', '直播', '培训', '学习', '教育', '2021']
    mapping = {term: core.token() for term in terms}
    core.validate(mapping)
    record = folder / '敏感词映射.csv'
    with record.open('w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerows([['敏感词', '替换标记']] + list(mapping.items()))
    mapping = core.load_mapping(record)
    results = {'source': source.name, 'characters': len(original_text), 'original_structure': structure(source), 'cases': []}
    for images in (False, True):
        label = '去图片' if images else '保留图片'
        safe = folder / f'{label}_脱敏.docx'
        restored = folder / f'{label}_还原.docx'
        start = time.perf_counter()
        transformed = core.transform(source, safe, mapping, remove_images=images)
        safe_text = core.extract(safe)
        assert all(term not in safe_text for term in terms)
        inspected = core.inspect_restore(safe, {'mapping': mapping})
        assert not inspected['missing'] and not inspected['unknown']
        core.transform(safe, restored, {v: k for k, v in mapping.items()}, sanitize=False)
        assert core.extract(restored) == original_text, 'Round-trip text differs'
        parsed = structure(safe)
        assert not parsed['missing_relationship_targets'], parsed
        if images:
            assert parsed['media'] == 0
        else:
            with zipfile.ZipFile(source) as a, zipfile.ZipFile(restored) as b:
                for n in a.namelist():
                    if n.startswith('word/media/'):
                        assert a.read(n) == b.read(n)
        results['cases'].append({'case': label, 'seconds': round(time.perf_counter()-start, 3), 'counts': transformed['counts'], 'removed_images': transformed['removed_images'], 'structure': parsed, 'restored_text_identical': True, 'safe_bytes': safe.stat().st_size})
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    results['original_unchanged'] = True
    (folder / 'report.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(str(folder))
    print(json.dumps(results, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
