import csv
import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import scrubdoc as core

AI_PROMPT = '请处理这份脱敏文档。所有形如【敏感项_xxx】的占位标记必须原样保留，不修改大小写、不拆分、不翻译、不猜测其真实内容。尽量保留文档格式，以原文件类型返回。'


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('ScrubDoc · 离线文档脱敏')
        self.geometry('1080x760')
        self.minsize(900, 650)
        self.store = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'ScrubDoc' / 'terms.json'
        self.files = []
        self.busy = False
        self.remove_images = tk.BooleanVar()
        from ui import build
        build(self, AI_PROMPT)
        try:
            if self.store.exists():
                for term in json.loads(self.store.read_text(encoding='utf-8')):
                    self.tree.insert('', 'end', values=('✓', term, core.token()))
        except Exception:
            self.status.set('本地词库读取失败，可重新导入。')

    def save(self):
        self.store.parent.mkdir(parents=True, exist_ok=True)
        temp = self.store.with_name(f'terms_{uuid.uuid4().hex}.tmp')
        try:
            temp.write_text(json.dumps([self.tree.item(i, 'values')[1] for i in self.tree.get_children()], ensure_ascii=False), encoding='utf-8')
            temp.replace(self.store)
        finally:
            temp.unlink(missing_ok=True)

    def mapping(self):
        return {v[1]: v[2] for i in self.tree.get_children() if (v := self.tree.item(i, 'values'))[0] == '✓'}

    def toggle(self, event):
        i = self.tree.identify_row(event.y)
        if i and self.tree.identify_column(event.x) == '#1':
            v = list(self.tree.item(i, 'values'))
            v[0] = '' if v[0] else '✓'
            self.tree.item(i, values=v)

    def select_all(self, selected):
        for i in self.tree.get_children():
            v = list(self.tree.item(i, 'values'))
            v[0] = '✓' if selected else ''
            self.tree.item(i, values=v)

    def add(self):
        term = simpledialog.askstring('新增敏感词', '输入敏感词（按原文精确匹配）：', parent=self)
        if term and term.strip():
            term = term.strip()
            if term in [self.tree.item(i, 'values')[1] for i in self.tree.get_children()]:
                return messagebox.showinfo('提示', '该敏感词已存在。')
            self.tree.insert('', 'end', values=('✓', term, core.token()))
            self.save()

    def edit(self):
        selection = self.tree.selection()
        if not selection:
            return
        i = selection[0]
        v = list(self.tree.item(i, 'values'))
        term = simpledialog.askstring('修改敏感词', '敏感词：', initialvalue=v[1], parent=self)
        if not term or not term.strip():
            return
        term = term.strip()
        if any(self.tree.item(other, 'values')[1] == term for other in self.tree.get_children() if other != i):
            return messagebox.showerror('重复', '该敏感词已存在。')
        v[1] = term
        value = simpledialog.askstring('修改替换标记', f'敏感词：{v[1]}\n替换标记：', initialvalue=v[2], parent=self)
        if value and value.strip():
            v[2] = value.strip()
            self.tree.item(i, values=v)
            self.save()

    def add_many(self):
        dialog = tk.Toplevel(self)
        dialog.title('批量新增敏感词')
        dialog.geometry('540x430')
        dialog.minsize(440, 320)
        dialog.transient(self)
        ttk.Label(dialog, text='每行一个敏感词，可直接粘贴多行；空行和重复词自动跳过。', wraplength=500).pack(anchor='w', padx=16, pady=12)
        box = tk.Text(dialog, wrap='word', height=10, font=('Microsoft YaHei UI', 11))
        def submit():
            try:
                added, skipped = self.insert_terms(box.get('1.0', 'end').splitlines())
                self.status.set(f'批量新增完成：新增 {added} 个，重复 {skipped} 个；空行已忽略。')
                dialog.destroy()
            except Exception as e:
                messagebox.showerror('新增失败', str(e), parent=dialog)
        buttons = ttk.Frame(dialog)
        buttons.pack(side='bottom', fill='x', padx=16, pady=12)
        ttk.Button(buttons, text='保存全部', command=submit).pack(side='right')
        ttk.Button(buttons, text='取消', command=dialog.destroy).pack(side='right', padx=8)
        box.pack(fill='both', expand=True, padx=16)
        dialog.bind('<Control-Return>', lambda event: submit())
        dialog.grab_set()
        box.focus_set()

    def insert_terms(self, terms):
        existing = {self.tree.item(i, 'values')[1] for i in self.tree.get_children()}
        added = skipped = 0
        inserted = []
        for term in terms:
            term = term.strip()
            if not term:
                continue
            if term in existing:
                skipped += 1
                continue
            inserted.append(self.tree.insert('', 'end', values=('✓', term, core.token())))
            existing.add(term)
            added += 1
        try:
            self.save()
        except Exception:
            for item in inserted:
                self.tree.delete(item)
            raise
        return added, skipped

    def delete(self):
        for i in self.tree.selection():
            self.tree.delete(i)
        self.save()

    def regenerate(self):
        for i in self.tree.selection() or self.tree.get_children():
            v = list(self.tree.item(i, 'values'))
            v[2] = core.token()
            self.tree.item(i, values=v)

    def import_terms(self):
        path = filedialog.askopenfilename(filetypes=[('词库', '*.csv *.txt')])
        if not path:
            return
        try:
            existing = {self.tree.item(i, 'values')[1] for i in self.tree.get_children()}
            count = 0
            for term in core.import_terms(path):
                if term not in existing:
                    self.tree.insert('', 'end', values=('✓', term, core.token()))
                    existing.add(term)
                    count += 1
            self.save()
            self.status.set(f'已导入 {count} 个新词，重复词已跳过。')
        except Exception as e:
            messagebox.showerror('导入失败', str(e))

    def export_terms(self):
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV', '*.csv'), ('TXT', '*.txt')])
        if path:
            try:
                terms = [self.tree.item(i, 'values')[1] for i in self.tree.get_children()]
                with open(path, 'w', encoding='utf-8-sig', newline='') as f:
                    if path.lower().endswith('.csv'):
                        csv.writer(f).writerows([['敏感词', '替换标记']] + [list(self.tree.item(i, 'values')[1:]) for i in self.tree.get_children()])
                    else:
                        f.write('\n'.join(terms))
                self.status.set('词库已导出。')
            except Exception as e:
                messagebox.showerror('导出失败', str(e))

    def pick_files(self):
        file = filedialog.askopenfilename(title='选择一个文档', filetypes=[('流式文档', '*.docx *.txt')])
        if file:
            self.files = [file]
            self.file_label.config(text=file)
            self.set_text(self.preview_box, '已选择文档，请点击“检查命中”。')

    def run_job(self, job, done):
        if self.busy:
            return messagebox.showinfo('处理中', '请等待当前任务完成。')
        self.busy = True
        self.status.set('处理中…')
        def worker():
            try:
                result = job()
                self.after(0, lambda: finish(result, None))
            except Exception as e:
                self.after(0, lambda error=str(e): finish(None, error))
        def finish(result, error):
            self.busy = False
            self.status.set('处理失败' if error else '处理完成')
            if error:
                messagebox.showerror('处理失败', error)
            else:
                done(result)
        threading.Thread(target=worker, daemon=True).start()

    def preview(self):
        mapping, files = self.mapping(), list(self.files)
        def job():
            if not files:
                return '请先选择文档。'
            if not mapping:
                return '请先勾选需要检查的敏感词。'
            file = files[0]
            text = core.extract(file)
            lines = [f'当前文档：{Path(file).name}', '', '敏感词命中情况：']
            lines.extend(f'{term}：命中 {text.count(term)} 处' for term in mapping)
            lines.append('\n统计为各词独立精确匹配次数；相互包含的词可能重叠，实际替换优先长词。')
            return '\n'.join(lines)
        self.run_job(job, lambda result: self.set_text(self.preview_box, result))

    @staticmethod
    def set_text(widget, text):
        widget.delete('1.0', 'end')
        widget.insert('1.0', text)

    def scrub(self):
        mapping, files, images = self.mapping(), list(self.files), self.remove_images.get()
        try:
            if not files:
                raise ValueError('请先选择文档。')
            if mapping:
                core.validate(mapping)
            elif not images:
                raise ValueError('请选择敏感词或启用去除图片。')
        except Exception as e:
            return messagebox.showerror('检查', str(e))
        folder = filedialog.askdirectory(title='选择输出目录（将创建独立任务子目录）')
        if not folder:
            return
        def job():
            task = Path(folder) / ('ScrubDoc_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6])
            safe = task / '可交给AI'
            private = task / '仅本地保存_含敏感信息'
            safe.mkdir(parents=True)
            private.mkdir()
            record = private / '敏感词映射.csv'
            # Save exact mapping before processing so every output can be restored.
            with record.open('w', encoding='utf-8-sig', newline='') as f:
                csv.writer(f).writerows([['敏感词', '替换标记']] + list(mapping.items()))
            lines = []
            for index, file in enumerate(files, 1):
                try:
                    text = core.extract(file)
                    if any(value in text for value in mapping.values()):
                        raise ValueError('替换标记已存在于原文，请重新生成标记。')
                    destination = safe / f'{index:03d}_{Path(file).stem}_脱敏{Path(file).suffix.lower()}'
                    result = core.transform(file, destination, mapping, images)
                    lines.append(f'{Path(file).name}：成功，替换 {sum(result["counts"].values())} 处，删除图片 {result["removed_images"]} 个')
                except Exception as e:
                    lines.append(f'{Path(file).name}：失败 — {e}')
            return f'输出目录：{task}\n敏感词映射文件：{record}\n\n' + '\n'.join(lines) + '\n\n仅上传“可交给AI”目录内文件。还原时选择本次敏感词映射 CSV，勿上传映射文件。\n复杂对象和未配置敏感词需人工检查。'
        self.run_job(job, lambda result: self.set_text(self.preview_box, result))

    def pick_mapping(self):
        p = filedialog.askopenfilename(title='选择本次脱敏对应的敏感词映射文件', filetypes=[('敏感词映射', '*.csv')])
        if p:
            self.mapping_path.set(p)

    def pick_result(self):
        p = filedialog.askopenfilename(filetypes=[('AI 处理结果', '*.docx *.txt')])
        if p:
            self.result_path.set(p)

    def check(self):
        self.restore()

    def restore(self):
        if self.busy:
            return messagebox.showinfo('处理中', '请等待当前任务完成。')
        try:
            mapping = core.load_mapping(self.mapping_path.get())
            source = self.result_path.get()
            check = core.inspect_restore(source, {'mapping': mapping})
            lines = ['标记检查结果：']
            for term, mark in mapping.items():
                lines.append(f'{mark} → {term}：命中 {check["counts"][mark]} 处')
            lines.append('缺失标记：' + ('、'.join(check['missing']) or '无'))
            lines.append('未知标记：' + ('、'.join(check['unknown']) or '无'))
            report = '\n'.join(lines)
            self.set_text(self.report, report)
            if check['unknown']:
                return messagebox.showerror('未知标记', '发现未知标记，请先修正文档或选择对应的敏感词映射文件：\n' + '\n'.join(check['unknown']))
            if not any(check['counts'].values()):
                return messagebox.showerror('无法还原', '未找到任何对应标记，请检查文档及敏感词映射文件。')
            if check['missing'] and not messagebox.askyesno('标记缺失', '部分标记已不存在，可能被 AI 删除或改写。继续仅还原现有标记？'):
                return
            destination = filedialog.asksaveasfilename(initialfile=Path(source).stem + '_还原' + Path(source).suffix, defaultextension=Path(source).suffix, filetypes=[('同类型文档', '*' + Path(source).suffix)])
            if not destination:
                return
            if Path(destination).suffix.lower() != Path(source).suffix.lower():
                raise ValueError('输出扩展名必须与输入文件相同。')
            reverse = {v: k for k, v in mapping.items()}
            self.run_job(lambda: core.transform(source, destination, reverse, sanitize=False), lambda result: self.set_text(self.report, report + f'\n\n已还原 {sum(result["counts"].values())} 处。\n输出：{destination}\n请人工检查 AI 修改及排版。'))
        except Exception as e:
            messagebox.showerror('还原失败', str(e))


if __name__ == '__main__':
    App().mainloop()
