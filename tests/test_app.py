import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import App


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = Path(self.temp.name)
        self.app = App()
        self.app.withdraw()
        self.app.store = self.root / 'terms.json'
        self.app.tree.delete(*self.app.tree.get_children())
        # Execute jobs immediately to test UI workflow without a running event loop.
        self.app.run_job = lambda job, done: done(job())

    def tearDown(self):
        self.app.destroy()
        self.temp.cleanup()

    def test_bulk_and_counts(self):
        self.assertEqual(self.app.insert_terms(['秘密', '张三', '秘密', '', ' 未命中 ']), (3, 1))
        self.assertEqual(len(json.loads(self.app.store.read_text(encoding='utf-8'))), 3)
        first, second = self.root / 'one.txt', self.root / 'two.txt'
        first.write_text('秘密秘密张三', encoding='utf-8')
        second.write_text('秘密', encoding='utf-8')
        with patch('app.filedialog.askopenfilename', return_value=str(first)):
            self.app.pick_files()
        self.assertEqual(self.app.files, [str(first)])
        self.app.preview()
        report = self.app.preview_box.get('1.0', 'end')
        self.assertIn('秘密：命中 2 处', report)
        self.assertIn('张三：命中 1 处', report)
        self.assertIn('未命中：命中 0 处', report)
        self.assertNotIn('上下文', report)
        self.assertNotIn('two.txt', report)

    def test_navigation_and_controls_fit_minimum_window(self):
        import tkinter as tk
        from tkinter import ttk
        self.app.geometry('1000x740')
        self.app.deiconify()
        self.app.update()
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        buttons = [w for w in descendants(self.app) if isinstance(w, tk.Button)]
        for title in ('敏感词与映射', '脱敏导出', '检查与还原'):
            next(w for w in buttons if title in w.cget('text')).invoke()
            self.app.update()
            self.assertEqual(self.app.page_title.cget('text'), title)
            for widget in descendants(self.app):
                if isinstance(widget, ttk.Button) and widget.winfo_ismapped():
                    self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(), self.app.winfo_rootx() + self.app.winfo_width())
                    self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), self.app.winfo_rooty() + self.app.winfo_height())

    def test_background_job_completes_in_real_event_loop(self):
        self.app.run_job = App.run_job.__get__(self.app)
        received = []
        def done(result):
            received.append(result)
            self.app.quit()
        self.app.after(0, lambda: self.app.run_job(lambda: 42, done))
        timeout = self.app.after(5000, self.app.quit)
        self.app.mainloop()
        self.app.after_cancel(timeout)
        self.assertEqual(received, [42])
        self.assertFalse(self.app.busy)

    def test_bulk_dialog_save_button_visible_and_persists(self):
        import tkinter as tk
        from tkinter import ttk
        self.app.deiconify()
        self.app.update()
        self.app.add_many()
        self.app.update()
        dialog = next(w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel))
        box = next(w for w in dialog.winfo_children() if isinstance(w, tk.Text))
        buttons = [w for frame in dialog.winfo_children() for w in frame.winfo_children()
                   if isinstance(w, ttk.Button) and w.cget('text') == '保存全部']
        button = buttons[0]
        self.assertTrue(button.winfo_ismapped())
        self.assertLess(button.winfo_rooty() + button.winfo_height(), dialog.winfo_rooty() + dialog.winfo_height())
        box.insert('1.0', '秘密\n张三\n秘密\n')
        button.invoke()
        self.assertFalse(dialog.winfo_exists())
        self.assertEqual(json.loads(self.app.store.read_text(encoding='utf-8')), ['秘密', '张三'])

    def test_bulk_failed_save_rolls_back_for_retry(self):
        with patch.object(self.app, 'save', side_effect=OSError('write failed')):
            with self.assertRaises(OSError):
                self.app.insert_terms(['秘密'])
        self.assertEqual(len(self.app.tree.get_children()), 0)
        self.assertEqual(self.app.insert_terms(['秘密']), (1, 0))

    def test_prompt_visible_without_copy_button(self):
        text = self.app.prompt_box.get('1.0', 'end-1c')
        self.assertIn('【敏感项_xxx】', text)
        from tkinter import ttk
        def buttons(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Button):
                    yield child.cget('text')
                yield from buttons(child)
        self.assertNotIn('复制 AI 提示词', list(buttons(self.app)))

    def test_check_directly_restores(self):
        package, source, output = [self.root / n for n in ('mapping.csv', 'ai.txt', 'restored.txt')]
        package.write_text('敏感词,替换标记\n张三,【敏感项_A1】\n', encoding='utf-8-sig')
        source.write_text('由【敏感项_A1】负责。', encoding='utf-8')
        self.app.mapping_path.set(str(package))
        self.app.result_path.set(str(source))
        with patch('app.filedialog.asksaveasfilename', return_value=str(output)):
            self.app.check()
        self.assertEqual(output.read_text(encoding='utf-8'), '由张三负责。')
        self.assertIn('已还原 1 处', self.app.report.get('1.0', 'end'))

    def test_export_csv_then_restore(self):
        self.app.insert_terms(['张三'])
        source = self.root / 'source.txt'
        source.write_text('张三负责。', encoding='utf-8')
        self.app.files = [str(source)]
        with patch('app.filedialog.askdirectory', return_value=str(self.root)):
            self.app.scrub()
        mapping = list(self.root.glob('ScrubDoc_*/仅本地保存_含敏感信息/敏感词映射.csv'))
        self.assertEqual(len(mapping), 1)
        self.assertFalse(list(self.root.glob('ScrubDoc_*/**/*.json')))
        safe = next(self.root.glob('ScrubDoc_*/可交给AI/*.txt'))
        self.app.mapping_path.set(str(mapping[0]))
        self.app.result_path.set(str(safe))
        output = self.root / 'restored.txt'
        with patch('app.filedialog.asksaveasfilename', return_value=str(output)):
            self.app.check()
        self.assertEqual(output.read_text(encoding='utf-8'), '张三负责。')

    def test_unknown_markers_do_not_restore(self):
        package, source = self.root / 'mapping.csv', self.root / 'ai.txt'
        package.write_text('敏感词,替换标记\n张三,【敏感项_A1】\n', encoding='utf-8-sig')
        source.write_text('【敏感项_B2】', encoding='utf-8')
        self.app.mapping_path.set(str(package))
        self.app.result_path.set(str(source))
        with patch('app.messagebox.showerror') as error, patch('app.filedialog.asksaveasfilename') as save:
            self.app.check()
            error.assert_called_once()
            save.assert_not_called()
