"""ScrubDoc desktop appearance and layout."""
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk

BG = '#f3f6fb'
INK = '#152238'
MUTED = '#64748b'
BLUE = '#2563eb'


def build(app, prompt):
    app.geometry('1180x820')
    app.minsize(1000, 740)
    app.configure(bg=BG)
    style = ttk.Style(app)
    style.theme_use('clam')
    style.configure('.', font=('Microsoft YaHei UI', 10), background=BG, foreground=INK)
    style.configure('TFrame', background=BG)
    style.configure('Card.TFrame', background='white')
    style.configure('TLabel', background=BG)
    style.configure('Card.TLabel', background='white')
    style.configure('Muted.TLabel', foreground=MUTED)
    style.configure('Title.TLabel', font=('Microsoft YaHei UI', 23, 'bold'))
    style.configure('Sub.TLabel', font=('Microsoft YaHei UI', 12, 'bold'))
    style.configure('TButton', background='white', foreground=INK, borderwidth=1, bordercolor='#dce3ed', padding=(12, 8))
    style.map('TButton', background=[('active', '#eaf0fa')])
    style.configure('Primary.TButton', background=BLUE, foreground='white', bordercolor=BLUE)
    style.map('Primary.TButton', background=[('active', '#1d4ed8')], foreground=[('active', 'white')])
    style.configure('TEntry', fieldbackground='white', padding=9, bordercolor='#dce3ed')
    style.configure('Treeview', background='white', fieldbackground='white', rowheight=38, borderwidth=0)
    style.configure('Treeview.Heading', background='#edf2fa', foreground=MUTED, padding=10, font=('Microsoft YaHei UI', 10, 'bold'))
    style.map('Treeview', background=[('selected', '#dbeafe')], foreground=[('selected', '#1e40af')])
    style.configure('TCheckbutton', background=BG, padding=5)
    style.layout('Workspace.TNotebook.Tab', [])
    style.configure('Workspace.TNotebook', borderwidth=0, tabmargins=0, lightcolor=BG, darkcolor=BG, bordercolor=BG)

    sidebar = tk.Frame(app, bg='#12233e', width=210)
    sidebar.pack(side='left', fill='y')
    sidebar.pack_propagate(False)
    assets = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'assets'
    try:
        app.iconbitmap(str(assets / 'app.ico'))
        app.brand_image = tk.PhotoImage(file=str(assets / 'app.png')).subsample(4)
        tk.Label(sidebar, image=app.brand_image, bg='#12233e').pack(anchor='w', padx=23, pady=(30, 12))
    except tk.TclError:
        pass
    tk.Label(sidebar, text='ScrubDoc', bg='#12233e', fg='white', font=('Segoe UI', 22, 'bold')).pack(anchor='w', padx=24)
    tk.Label(sidebar, text='文档脱敏工作台', bg='#12233e', fg='#a3b6d2', font=('Microsoft YaHei UI', 10)).pack(anchor='w', padx=24, pady=(4, 35))
    tk.Label(sidebar, text='工作流程', bg='#12233e', fg='#8299b9', font=('Microsoft YaHei UI', 9)).pack(anchor='w', padx=24, pady=(0, 12))
    shell = ttk.Frame(app, padding=(28, 24))
    shell.pack(side='left', fill='both', expand=True)
    heading = ttk.Frame(shell)
    heading.pack(fill='x')
    app.page_title = ttk.Label(heading, style='Title.TLabel')
    app.page_title.pack(side='left')
    tk.Label(heading, text='●  本地离线', bg='#dcfce7', fg='#166534', padx=12, pady=6).pack(side='right')
    app.page_description = ttk.Label(shell, style='Muted.TLabel')
    app.page_description.pack(anchor='w', pady=(6, 22))
    notebook = ttk.Notebook(shell, style='Workspace.TNotebook')
    notebook.pack(fill='both', expand=True)
    app.notebook = notebook
    terms, work, restore = [ttk.Frame(notebook) for _ in range(3)]
    for frame in (terms, work, restore):
        notebook.add(frame)
    titles = ['敏感词与映射', '脱敏导出', '检查与还原']
    descriptions = ['管理敏感词，为每个词设置唯一的替换标记。', '选择一个文档，检查命中后生成脱敏副本。', '选择处理后的文档与对应 CSV，将标记恢复为原文。']
    nav = []
    def select(index):
        notebook.select(index)
        app.page_title.config(text=titles[index])
        app.page_description.config(text=descriptions[index])
        for n, button in enumerate(nav):
            button.configure(bg='#2563eb' if n == index else '#12233e', fg='white' if n == index else '#b9c9df')
    for i, title in enumerate(titles):
        button = tk.Button(sidebar, text=f'0{i+1}   {title}', anchor='w', relief='flat', bd=0, padx=16, pady=13,
                           font=('Microsoft YaHei UI', 11), activebackground='#23446e', activeforeground='white', cursor='hand2', command=lambda n=i: select(n))
        button.pack(fill='x', padx=12, pady=4)
        nav.append(button)
    tk.Label(sidebar, text='DOCX / TXT\n文件始终留在本机', justify='left', bg='#12233e', fg='#8299b9', font=('Microsoft YaHei UI', 9)).pack(side='bottom', anchor='w', padx=24, pady=28)
    select(0)

    def toolbar(parent, actions):
        frame = ttk.Frame(parent)
        frame.pack(fill='x', pady=(0, 12))
        for i, (label, command, primary) in enumerate(actions):
            ttk.Button(frame, text=label, command=command, style='Primary.TButton' if primary else 'TButton').grid(row=i//5, column=i%5, sticky='w', padx=(0, 7), pady=(0, 7))
        return frame

    def text_area(parent, height=10):
        frame = ttk.Frame(parent, style='Card.TFrame', padding=1)
        frame.pack(fill='both', expand=True, pady=(8, 12))
        text = tk.Text(frame, wrap='word', height=height, bg='white', fg=INK, relief='flat', bd=0,
                       padx=16, pady=14, insertbackground=BLUE, selectbackground='#dbeafe', font=('Microsoft YaHei UI', 10))
        scroll = ttk.Scrollbar(frame, command=text.yview)
        scroll.pack(side='right', fill='y')
        text.configure(yscrollcommand=scroll.set)
        text.pack(fill='both', expand=True)
        return text

    toolbar(terms, [('批量新增', app.add_many, True), ('新增', app.add, False), ('修改', app.edit, False), ('删除', app.delete, False), ('导入词库', app.import_terms, False), ('导出词库', app.export_terms, False), ('重新生成标记', app.regenerate, False), ('全选', lambda: app.select_all(True), False), ('全不选', lambda: app.select_all(False), False)])
    ttk.Label(terms, text='点击“启用”列勾选；双击词条修改。CSV 同时保存词语与标记。', style='Muted.TLabel').pack(anchor='w', pady=(0, 10))
    table = ttk.Frame(terms, style='Card.TFrame')
    table.pack(fill='both', expand=True)
    app.tree = ttk.Treeview(table, columns=('enabled', 'term', 'token'), show='headings', selectmode='extended')
    for name, label, width in [('enabled', '启用', 65), ('term', '敏感词', 240), ('token', '替换标记', 390)]:
        app.tree.heading(name, text=label)
        app.tree.column(name, width=width, minwidth=60, stretch=name != 'enabled', anchor='center' if name == 'enabled' else 'w')
    scroll = ttk.Scrollbar(table, command=app.tree.yview)
    scroll.pack(side='right', fill='y')
    app.tree.configure(yscrollcommand=scroll.set)
    app.tree.pack(fill='both', expand=True)
    app.tree.bind('<ButtonRelease-1>', app.toggle)
    app.tree.bind('<Double-1>', lambda e: app.edit() if app.tree.identify_column(e.x) != '#1' else None)
    toolbar(work, [('选择文档', app.pick_files, False), ('检查命中', app.preview, False), ('全部替换并导出', app.scrub, True)])
    file_card = ttk.Frame(work, style='Card.TFrame', padding=14)
    file_card.pack(fill='x')
    ttk.Label(file_card, text='当前文档', style='Card.TLabel', font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor='w')
    app.file_label = ttk.Label(file_card, text='尚未选择文件', style='Card.TLabel', foreground=MUTED, wraplength=680)
    app.file_label.pack(anchor='w', pady=(5, 0))
    ttk.Checkbutton(work, text='去除全部图片 · 删除后不可还原，原件保留', variable=app.remove_images).pack(anchor='w', pady=(10, 6))
    ttk.Label(work, text='AI 提示词', style='Sub.TLabel').pack(anchor='w')
    app.prompt_box = tk.Text(work, wrap='word', height=3, bg='#eaf0fa', fg='#475569', relief='flat', bd=0, padx=12, pady=9, font=('Microsoft YaHei UI', 9))
    app.prompt_box.insert('1.0', prompt)
    app.prompt_box.configure(state='disabled')
    app.prompt_box.pack(fill='x', pady=(6, 10))
    ttk.Label(work, text='命中检查 / 处理结果', style='Sub.TLabel').pack(anchor='w')
    app.preview_box = text_area(work, 6)
    app.preview_box.insert('1.0', '选择文档后，点击“检查命中”查看敏感词出现次数。')
    ttk.Label(work, text='导出时清除批注、修订删除内容及常见属性；复杂对象和附件需人工检查。', style='Muted.TLabel', wraplength=740).pack(anchor='w')
    app.mapping_path, app.result_path = tk.StringVar(), tk.StringVar()
    inputs = ttk.Frame(restore, style='Card.TFrame', padding=18)
    inputs.pack(fill='x', pady=(0, 16))
    for label, variable, callback in [('处理后的文档', app.result_path, app.pick_result), ('对应敏感词文件（CSV）', app.mapping_path, app.pick_mapping)]:
        ttk.Label(inputs, text=label, style='Card.TLabel', font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor='w', pady=(0, 7))
        row = ttk.Frame(inputs, style='Card.TFrame')
        row.pack(fill='x', pady=(0, 12))
        ttk.Entry(row, textvariable=variable).pack(side='left', fill='x', expand=True)
        ttk.Button(row, text='选择文件', command=callback).pack(side='left', padx=(10, 0))
    toolbar(restore, [('检查替换标记并还原', app.check, True)])
    ttk.Label(restore, text='标记检查 / 还原结果', style='Sub.TLabel').pack(anchor='w')
    app.report = text_area(restore, 6)
    app.report.insert('1.0', '选择两个对应文件后开始还原。检查通过后，将提示选择另存位置。')
    ttk.Label(restore, text='CSV 需包含“敏感词、替换标记”两列。映射文件含原文，请留在本机。', style='Muted.TLabel', wraplength=740).pack(anchor='w')
    app.status = tk.StringVar(value='就绪 · 原文件始终保留')
    ttk.Label(shell, textvariable=app.status, style='Muted.TLabel').pack(anchor='w', pady=(18, 0))
