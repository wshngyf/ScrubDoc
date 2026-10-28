import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import scrubdoc as s


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_txt_ai_reorder_restore(self):
        source = self.root / 'source.txt'
        safe = self.root / 'safe.txt'
        result = self.root / 'result.txt'
        restored = self.root / 'restored.txt'
        source.write_text('张三负责秘密项目。秘密需要保护。', encoding='utf-8')
        mapping = {'张三': '【敏感项_A1】', '秘密项目': '【敏感项_B2】', '秘密': '【敏感项_C3】'}
        s.validate(mapping)
        s.transform(source, safe, mapping)
        self.assertNotIn('秘密', safe.read_text(encoding='utf-8'))
        result.write_text('【敏感项_B2】由【敏感项_A1】负责，每周汇报。', encoding='utf-8')
        self.assertEqual(s.inspect_restore(result, {'mapping': mapping})['missing'], ['【敏感项_C3】'])
        s.transform(result, restored, {v: k for k, v in mapping.items()})
        self.assertEqual(restored.read_text(encoding='utf-8'), '秘密项目由张三负责，每周汇报。')

    def test_docx_cross_runs_images_and_restore(self):
        source, safe, restored = [self.root / x for x in ('a.docx', 'b.docx', 'c.docx')]
        xml = f'<w:document xmlns:w="{s.W}" xmlns:a="urn:a"><w:body><w:p><w:r><w:t>张</w:t></w:r><w:r><w:t>三负责张三</w:t></w:r><w:r><w:drawing><a:blip/></w:drawing></w:r></w:p><w:p><w:del><w:r><w:delText>旧秘密</w:delText></w:r></w:del></w:p></w:body></w:document>'
        with zipfile.ZipFile(source, 'w') as z:
            z.writestr('word/document.xml', xml)
            z.writestr('word/media/image1.png', b'private image')
        mapping = {'张三': '【敏感项_X1】'}
        report = s.transform(source, safe, mapping, True)
        self.assertEqual(report['counts']['张三'], 2)
        self.assertEqual(report['removed_images'], 1)
        with zipfile.ZipFile(safe) as z:
            self.assertNotIn('word/media/image1.png', z.namelist())
            self.assertNotIn('旧秘密', z.read('word/document.xml').decode())
        self.assertIn('【敏感项_X1】负责【敏感项_X1】', s.extract(safe))
        s.transform(safe, restored, {'【敏感项_X1】': '张三'}, sanitize=False)
        self.assertIn('张三负责张三', s.extract(restored))

    def test_collisions_and_original_protection(self):
        with self.assertRaises(ValueError):
            s.validate({'甲': 'same', '乙': 'same'})
        source = self.root / 'a.txt'
        source.write_text('秘密', encoding='utf-8')
        with self.assertRaises(ValueError):
            s.transform(source, source, {'秘密': 'abc'})
        self.assertEqual(source.read_text(encoding='utf-8'), '秘密')

    def test_import_and_encoding(self):
        source = self.root / '词库.csv'
        source.write_text('敏感词\n秘密\n"甲,乙"\n', encoding='utf-8-sig')
        self.assertEqual(s.import_terms(source), ['秘密', '甲,乙'])
        self.assertEqual(s.read_txt('中文'.encode('gb18030'))[0], '中文')

    def test_mapping_file_validation(self):
        path = self.root / 'mapping.csv'
        path.write_text('敏感词,替换标记\n张三,mMx\n', encoding='utf-8-sig')
        self.assertEqual(s.load_mapping(path), {'张三': 'mMx'})
        for content in ('敏感词\n张三\n', '敏感词,替换标记\n张三,x\n李四,x\n', '敏感词,替换标记\n张三,x\n张三,y\n'):
            path.write_text(content, encoding='utf-8')
            with self.assertRaises(ValueError):
                s.load_mapping(path)


if __name__ == '__main__':
    unittest.main()
