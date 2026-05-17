"""Interfaz gráfica para ejecutar el flujo del generador."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from generator.pipeline import run

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Generador SLR - YALex/YAPar')
        self.geometry('920x650')
        self._build()

    def _build(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill='both', expand=True)
        self.paths = {}
        for i, key in enumerate(['yal', 'yalp', 'input', 'out']):
            ttk.Label(frm, text=key.upper()).grid(row=i, column=0, sticky='w')
            e = ttk.Entry(frm, width=90)
            e.grid(row=i, column=1, padx=6, pady=4)
            self.paths[key] = e
            ttk.Button(frm, text='Seleccionar', command=lambda k=key: self.pick(k)).grid(row=i, column=2)
        ttk.Button(frm, text='Generar y analizar', command=self.execute).grid(row=4, column=1, pady=10)
        self.output = tk.Text(frm, height=26)
        self.output.grid(row=5, column=0, columnspan=3, sticky='nsew')
        frm.rowconfigure(5, weight=1)
        frm.columnconfigure(1, weight=1)

    def pick(self, key):
        if key == 'out':
            p = filedialog.askdirectory()
        else:
            p = filedialog.askopenfilename()
        if p:
            self.paths[key].delete(0, tk.END)
            self.paths[key].insert(0, p)

    def execute(self):
        try:
            r = run(*(self.paths[k].get() for k in ['yal', 'yalp', 'input', 'out']))
            self.output.delete('1.0', tk.END)
            self.output.insert(tk.END, '=== TOKENS ===\n' + str(r['tokens']) + '\n\n')
            self.output.insert(tk.END, '=== ERRORES LÉXICOS ===\n' + '\n'.join(r['lex_errors']) + '\n\n')
            self.output.insert(tk.END, '=== TRAZA SINTÁCTICA ===\n' + '\n'.join(r['trace']) + '\n\n')
            self.output.insert(tk.END, '=== ERROR SINTÁCTICO ===\n' + str(r['syn_error']) + '\n')
            messagebox.showinfo('Proceso finalizado', 'Se completó la generación y el análisis.')
        except Exception as ex:
            messagebox.showerror('Error', str(ex))

