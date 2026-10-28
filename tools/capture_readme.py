"""Capture the application's own windows with synthetic data for the README."""
import ctypes
import sys
from pathlib import Path
import tkinter as tk
from PIL import ImageGrab

ctypes.windll.shcore.SetProcessDpiAwareness(1)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App

out = Path(__file__).resolve().parents[1] / 'docs' / 'images'
out.mkdir(parents=True, exist_ok=True)
app = App()
app.geometry('1180x820+30+30')
app.tree.delete(*app.tree.get_children())
for term, mark in [('张三', '【敏感项_A7k2M9x4Qp】'), ('秘密项目', '【敏感项_B8n3R6y5Ts】'), ('甲方公司', '【敏感项_C9p4S7z6Uv】')]:
    app.tree.insert('', 'end', values=('✓', term, mark))
app.status.set('操作示例 · 以下内容均为演示数据')


def select_page(title):
    def visit(widget):
        for child in widget.winfo_children():
            if isinstance(child, tk.Button) and title in child.cget('text'):
                child.invoke()
                return True
            if visit(child):
                return True
        return False
    visit(app)


def save(name, widget=None):
    widget = widget or app
    widget.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(widget.winfo_id())
    ImageGrab.grab(window=hwnd).save(out / name)


def step1():
    select_page('敏感词与映射')
    app.after(500, lambda: (save('01-terms.png'), step2()))


def step2():
    app.add_many()
    dialog = next(w for w in app.winfo_children() if isinstance(w, tk.Toplevel))
    box = next(w for w in dialog.winfo_children() if isinstance(w, tk.Text))
    box.insert('1.0', '张三\n秘密项目\n甲方公司')
    def capture():
        save('02-bulk-add.png', dialog)
        dialog.destroy()
        step3()
    app.after(500, capture)


def step3():
    select_page('脱敏导出')
    app.file_label.config(text=r'D:\示例文档\项目说明.docx')
    app.set_text(app.preview_box, '当前文档：项目说明.docx\n\n敏感词命中情况：\n张三：命中 3 处\n秘密项目：命中 5 处\n甲方公司：命中 2 处\n\n统计为各词独立精确匹配次数；相互包含的词可能重叠，实际替换优先长词。')
    app.after(500, lambda: (save('03-check-hits.png'), step4()))


def step4():
    app.remove_images.set(True)
    app.set_text(app.preview_box, '输出目录：D:\\输出\\ScrubDoc_示例任务\n敏感词映射文件：D:\\输出\\ScrubDoc_示例任务\\仅本地保存_含敏感信息\\敏感词映射.csv\n\n项目说明.docx：成功，替换 10 处，删除图片 2 个\n\n仅上传“可交给AI”目录内文件。\n还原时选择本次敏感词映射 CSV，勿上传映射文件。')
    app.after(500, lambda: (save('04-export.png'), step5()))


def step5():
    select_page('检查与还原')
    app.result_path.set(r'D:\示例文档\项目说明_处理后.docx')
    app.mapping_path.set(r'D:\输出\ScrubDoc_示例任务\仅本地保存_含敏感信息\敏感词映射.csv')
    app.set_text(app.report, '标记检查结果：\n【敏感项_A7k2M9x4Qp】 → 张三：命中 3 处\n【敏感项_B8n3R6y5Ts】 → 秘密项目：命中 5 处\n【敏感项_C9p4S7z6Uv】 → 甲方公司：命中 2 处\n缺失标记：无\n未知标记：无\n\n已还原 10 处。\n输出：D:\\示例文档\\项目说明_处理后_还原.docx\n请人工检查处理结果及排版。')
    app.after(500, lambda: (save('05-restore.png'), app.destroy()))


app.after(500, step1)
app.mainloop()
print(out)
