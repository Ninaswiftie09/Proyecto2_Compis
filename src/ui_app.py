"""Interfaz gráfica estética e intuitiva para el generador YALex/YAPar."""
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from generator.pipeline import run


COLORS = {
    'bg': '#080b12',
    'panel': '#111827',
    'panel2': '#162033',
    'blue': '#2563eb',
    'blue2': '#60a5fa',
    'red': '#ef4444',
    'red2': '#fecaca',
    'text': '#f9fafb',
    'muted': '#a7b0c0',
    'ok': '#22c55e',
    'border': '#334155',
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Generador de analizadores SLR - YALex + YAPar')
        self.geometry('1180x760')
        self.minsize(1050, 680)
        self.configure(bg=COLORS['bg'])
        self.paths = {}
        self.last_result = None
        self._photos = {}
        self._configure_style()
        self._build()

    def _configure_style(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TFrame', background=COLORS['bg'])
        style.configure('Panel.TFrame', background=COLORS['panel'], relief='flat')
        style.configure('TLabel', background=COLORS['bg'], foreground=COLORS['text'], font=('Segoe UI', 10))
        style.configure('Muted.TLabel', background=COLORS['bg'], foreground=COLORS['muted'], font=('Segoe UI', 9))
        style.configure('Panel.TLabel', background=COLORS['panel'], foreground=COLORS['text'], font=('Segoe UI', 10))
        style.configure('Title.TLabel', background=COLORS['bg'], foreground=COLORS['text'], font=('Segoe UI', 22, 'bold'))
        style.configure('Subtitle.TLabel', background=COLORS['bg'], foreground=COLORS['muted'], font=('Segoe UI', 11))
        style.configure('Accent.TButton', background=COLORS['blue'], foreground='white', font=('Segoe UI', 10, 'bold'), padding=8)
        style.map('Accent.TButton', background=[('active', '#1d4ed8')])
        style.configure('Danger.TButton', background=COLORS['red'], foreground='white', font=('Segoe UI', 10, 'bold'), padding=8)
        style.configure('TButton', background=COLORS['panel2'], foreground=COLORS['text'], padding=7)
        style.map('TButton', background=[('active', COLORS['blue'])])
        style.configure('TEntry', fieldbackground='#0f172a', foreground=COLORS['text'], insertcolor=COLORS['text'])
        style.configure('TNotebook', background=COLORS['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', background=COLORS['panel2'], foreground=COLORS['text'], padding=(14, 8), font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', COLORS['blue'])])
        style.configure('Treeview', background='#0f172a', fieldbackground='#0f172a', foreground=COLORS['text'], rowheight=26, bordercolor=COLORS['border'])
        style.configure('Treeview.Heading', background=COLORS['panel2'], foreground=COLORS['text'], font=('Segoe UI', 10, 'bold'))

    def _build(self):
        root = ttk.Frame(self, padding=18)
        root.pack(fill='both', expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        ttk.Label(root, text='Generador de analizadores SLR', style='Title.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(
            root,
            text='Carga YALex, YAPar y una entrada. La herramienta genera lexer/parser independientes, AFD, LR(0), tabla SLR y traza de parsing.',
            style='Subtitle.TLabel',
        ).grid(row=1, column=0, sticky='w', pady=(2, 14))

        body = ttk.Frame(root)
        body.grid(row=2, column=0, sticky='nsew')
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_left_panel(body)
        self._build_results_panel(body)

    def _build_left_panel(self, parent):
        left = tk.Frame(parent, bg=COLORS['panel'], padx=16, pady=16, highlightbackground=COLORS['border'], highlightthickness=1)
        left.grid(row=0, column=0, sticky='ns', padx=(0, 16))

        tk.Label(left, text='Flujo de trabajo', bg=COLORS['panel'], fg=COLORS['text'], font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        tk.Label(left, text='Sigue estos 4 pasos para generar y probar.', bg=COLORS['panel'], fg=COLORS['muted'], font=('Segoe UI', 9)).pack(anchor='w', pady=(0, 14))

        fields = [
            ('yal', '1. Especificación léxica (.yal)', 'Archivo con reglas TOKEN / IGNORE'),
            ('yalp', '2. Especificación sintáctica (.yalp)', 'Archivo YAPar con %token, IGNORE, %% y producciones'),
            ('input', '3. Entrada de prueba (.txt)', 'Texto plano que será tokenizado y parseado'),
            ('out', '4. Carpeta de salida', 'Aquí se guardan los analizadores y diagramas'),
        ]
        for key, title, hint in fields:
            self._path_row(left, key, title, hint)

        tk.Label(left, text='Ejemplos rápidos', bg=COLORS['panel'], fg=COLORS['text'], font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(12, 6))
        examples = tk.Frame(left, bg=COLORS['panel'])
        examples.pack(fill='x')
        for name in ['low', 'medium', 'high']:
            ttk.Button(examples, text=name.capitalize(), command=lambda n=name: self.load_example(n)).pack(side='left', expand=True, fill='x', padx=2)

        ttk.Button(left, text='Generar y analizar', style='Accent.TButton', command=self.execute).pack(fill='x', pady=(18, 8))
        ttk.Button(left, text='Limpiar resultados', style='Danger.TButton', command=self.clear_results).pack(fill='x')

        self.status = tk.Label(left, text='Listo para ejecutar', bg=COLORS['panel'], fg=COLORS['muted'], wraplength=310, justify='left')
        self.status.pack(anchor='w', pady=(16, 0))

    def _path_row(self, parent, key, title, hint):
        box = tk.Frame(parent, bg=COLORS['panel'])
        box.pack(fill='x', pady=7)
        tk.Label(box, text=title, bg=COLORS['panel'], fg=COLORS['text'], font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        tk.Label(box, text=hint, bg=COLORS['panel'], fg=COLORS['muted'], font=('Segoe UI', 8)).pack(anchor='w')
        line = tk.Frame(box, bg=COLORS['panel'])
        line.pack(fill='x', pady=(4, 0))
        entry = ttk.Entry(line, width=42)
        entry.pack(side='left', fill='x', expand=True)
        self.paths[key] = entry
        ttk.Button(line, text='Buscar', command=lambda k=key: self.pick(k)).pack(side='left', padx=(6, 0))

    def _build_results_panel(self, parent):
        panel = tk.Frame(parent, bg=COLORS['panel'], padx=12, pady=12, highlightbackground=COLORS['border'], highlightthickness=1)
        panel.grid(row=0, column=1, sticky='nsew')
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        header = tk.Frame(panel, bg=COLORS['panel'])
        header.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        tk.Label(header, text='Resultados del análisis', bg=COLORS['panel'], fg=COLORS['text'], font=('Segoe UI', 15, 'bold')).pack(side='left')
        self.badge = tk.Label(header, text='SIN EJECUTAR', bg=COLORS['panel2'], fg=COLORS['muted'], padx=10, pady=4, font=('Segoe UI', 9, 'bold'))
        self.badge.pack(side='right')

        self.notebook = ttk.Notebook(panel)
        self.notebook.grid(row=1, column=0, sticky='nsew')

        self.tokens_tree = self._tree_tab('Tokens', ('Token', 'Lexema'))
        self.trace_tree = self._tree_tab('Traza SLR', ('Pila', 'Entrada', 'Acción'))
        self.errors_text = self._text_tab('Errores')
        self.files_text = self._text_tab('Archivos generados')
        self.dfa_canvas, self.dfa_text = self._combo_tab('AFD')
        self.lr0_canvas, self.lr0_text = self._combo_tab('LR(0)')
        self.table_text = self._text_tab('Tabla SLR')

    def _tree_tab(self, title, columns):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=title)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=columns, show='headings')
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor='w', width=180)
        tree.grid(row=0, column=0, sticky='nsew')
        ybar = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        ybar.grid(row=0, column=1, sticky='ns')
        tree.configure(yscrollcommand=ybar.set)
        return tree

    def _text_tab(self, title):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=title)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        text = tk.Text(frame, bg='#0f172a', fg=COLORS['text'], insertbackground=COLORS['text'], relief='flat', wrap='none', font=('Consolas', 10))
        text.grid(row=0, column=0, sticky='nsew')
        ybar = ttk.Scrollbar(frame, orient='vertical', command=text.yview)
        ybar.grid(row=0, column=1, sticky='ns')
        xbar = ttk.Scrollbar(frame, orient='horizontal', command=text.xview)
        xbar.grid(row=1, column=0, sticky='ew')
        text.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        return text

    def _combo_tab(self, title):
        """Tab con canvas scrollable para imagen (arriba) y texto (abajo)."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=title)
        frame.rowconfigure(0, weight=3)
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        img_frame = tk.Frame(frame, bg='#0f172a')
        img_frame.grid(row=0, column=0, sticky='nsew')
        img_frame.rowconfigure(0, weight=1)
        img_frame.columnconfigure(0, weight=1)
        canvas = tk.Canvas(img_frame, bg='#0f172a', highlightthickness=0)
        canvas.grid(row=0, column=0, sticky='nsew')
        cy = ttk.Scrollbar(img_frame, orient='vertical', command=canvas.yview)
        cy.grid(row=0, column=1, sticky='ns')
        cx = ttk.Scrollbar(img_frame, orient='horizontal', command=canvas.xview)
        cx.grid(row=1, column=0, sticky='ew')
        canvas.configure(yscrollcommand=cy.set, xscrollcommand=cx.set)

        txt_frame = tk.Frame(frame, bg='#0f172a')
        txt_frame.grid(row=1, column=0, sticky='nsew')
        txt_frame.rowconfigure(0, weight=1)
        txt_frame.columnconfigure(0, weight=1)
        text = tk.Text(txt_frame, bg='#0f172a', fg=COLORS['text'], insertbackground=COLORS['text'],
                       relief='flat', wrap='none', font=('Consolas', 9), height=8)
        text.grid(row=0, column=0, sticky='nsew')
        ybar = ttk.Scrollbar(txt_frame, orient='vertical', command=text.yview)
        ybar.grid(row=0, column=1, sticky='ns')
        text.configure(yscrollcommand=ybar.set)
        return canvas, text

    def _show_image(self, canvas, png_path):
        """Carga un PNG en el canvas; muestra mensaje si no está disponible."""
        canvas.delete('all')
        if png_path and os.path.exists(png_path):
            try:
                img = tk.PhotoImage(file=png_path)
                key = str(id(canvas))
                self._photos[key] = img
                canvas.create_image(0, 0, anchor='nw', image=img)
                canvas.configure(scrollregion=canvas.bbox('all'))
                return
            except Exception:
                pass
        msg = 'Imagen no disponible. Instala Graphviz para generar el diagrama visual.'
        canvas.create_text(12, 12, text=msg, fill=COLORS['muted'], anchor='nw',
                           font=('Segoe UI', 10))

    def pick(self, key):
        if key == 'out':
            selected = filedialog.askdirectory(title='Selecciona carpeta de salida')
        else:
            selected = filedialog.askopenfilename(title='Selecciona archivo')
        if selected:
            self.paths[key].delete(0, tk.END)
            self.paths[key].insert(0, selected)

    def load_example(self, name):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tests_data', name))
        out = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outputs', f'{name}_ui'))
        values = {
            'yal': os.path.join(base, f'lexer_{name}.yal'),
            'yalp': os.path.join(base, f'parser_{name}.yalp'),
            'input': os.path.join(base, f'input_{name}.txt'),
            'out': out,
        }
        for key, value in values.items():
            self.paths[key].delete(0, tk.END)
            self.paths[key].insert(0, value)
        self.status.config(text=f'Ejemplo {name} cargado. Presiona “Generar y analizar”.', fg=COLORS['blue2'])

    def clear_results(self):
        for tree in [self.tokens_tree, self.trace_tree]:
            for item in tree.get_children():
                tree.delete(item)
        for text in [self.errors_text, self.files_text, self.dfa_text, self.lr0_text, self.table_text]:
            text.delete('1.0', tk.END)
        for canvas in [self.dfa_canvas, self.lr0_canvas]:
            canvas.delete('all')
        self._photos.clear()
        self.badge.config(text='SIN EJECUTAR', bg=COLORS['panel2'], fg=COLORS['muted'])
        self.status.config(text='Resultados limpiados.', fg=COLORS['muted'])

    def _read_file_if_exists(self, path):
        if path and os.path.exists(path):
            return open(path, 'r', encoding='utf-8').read()
        return 'No disponible.'

    def execute(self):
        try:
            yal = self.paths['yal'].get().strip()
            yalp = self.paths['yalp'].get().strip()
            input_file = self.paths['input'].get().strip()
            out = self.paths['out'].get().strip()
            result = run(yal, yalp, input_file, out)
            self.last_result = result
            self._render_result(result)
            if result['lex_errors'] or result['syn_error']:
                self.badge.config(text='CON ERRORES', bg=COLORS['red'], fg='white')
                self.status.config(text='Proceso completado, pero se detectaron errores. Revisa la pestaña Errores.', fg=COLORS['red2'])
            else:
                self.badge.config(text='ACEPTADO', bg=COLORS['ok'], fg='#052e16')
                self.status.config(text='Cadena aceptada. Lexer/parser y diagramas generados correctamente.', fg='#bbf7d0')
            messagebox.showinfo('Proceso finalizado', 'Se completó la generación y el análisis.')
        except Exception as ex:
            self.badge.config(text='ERROR', bg=COLORS['red'], fg='white')
            self.status.config(text=str(ex), fg=COLORS['red2'])
            messagebox.showerror('Error', str(ex))

    def _render_result(self, result):
        self.clear_results()
        for token, lexeme in result['tokens']:
            self.tokens_tree.insert('', 'end', values=(token, repr(lexeme)))
        for row in result['trace']:
            self.trace_tree.insert('', 'end', values=(row['stack'], row['input'], row['action']))

        errors = []
        if result['lex_errors']:
            errors.append('Errores léxicos:')
            errors.extend('  ' + e for e in result['lex_errors'])
        else:
            errors.append('Errores léxicos: ninguno')
        errors.append('')
        errors.append('Error sintáctico: ' + str(result['syn_error'] or 'ninguno'))
        if result['warnings']:
            errors.append('')
            errors.append('Advertencias:')
            errors.extend('  ' + w for w in result['warnings'])
        self.errors_text.insert(tk.END, '\n'.join(errors))

        files = result['files']
        file_lines = []
        for name, path in files.items():
            file_lines.append(f'{name}: {path or "No generado"}')
        self.files_text.insert(tk.END, '\n'.join(file_lines))
        self._show_image(self.dfa_canvas, files.get('dfa_png'))
        self.dfa_text.insert(tk.END, self._read_file_if_exists(files.get('dfa_txt')))
        self._show_image(self.lr0_canvas, files.get('lr0_png'))
        self.lr0_text.insert(tk.END, self._read_file_if_exists(files.get('lr0_txt')))
        self.table_text.insert(tk.END, self._read_file_if_exists(files.get('slr_table')))
