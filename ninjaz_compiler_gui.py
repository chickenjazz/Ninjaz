#!/usr/bin/env python3
"""
Ninjaz Compiler GUI — tkinter front-end for ninjaz_compiler.py
Run with:  python ninjaz_compiler_gui.py
Build exe: pyinstaller --onefile --windowed ninjaz_compiler_gui.py
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog

from ninjaz_compiler import (
    Lexer, Parser, SemanticAnalyzer, Interpreter,
    NinjazError, ast_to_lines,
)

# ── Colour palette ─────────────────────────────────────────────────────────────
BG_DARK    = "#1e1e2e"
BG_PANEL   = "#252535"
BG_EDITOR  = "#12121c"
BG_TAB     = "#313149"
BG_SEL     = "#4a4a72"
FG         = "#cdd6f4"
FG_DIM     = "#7f849c"
FG_GREEN   = "#a6e3a1"
FG_RED     = "#f38ba8"
FG_YELLOW  = "#f9e2af"
FG_BLUE    = "#89b4fa"
FG_PURPLE  = "#cba6f7"
ACCENT     = "#6366f1"

MONO = ("Consolas", 11)
UI   = ("Segoe UI", 10)
HD   = ("Segoe UI Semibold", 10)

# ── Sample programs ────────────────────────────────────────────────────────────
SAMPLE_VALID = """\
/* Compute b = a * 3 + 2 */
var a;
var b;
input a;
b = a * 3 + 2;
output b;
"""

SAMPLE_INVALID = """\
/* Semantic error: y not declared */
var x;
output y;\
"""

SAMPLE_ARITH = """\
/* Compute (x + y) * z */
var x;
var y;
var z;
var result;
input x;
input y;
input z;
result = (x + y) * z;
output result;
"""

SAMPLE_STRING = """\
/* String greeting */
string name;
string greeting;
input name;
greeting = "Hello, " + name;
output greeting;
"""

SAMPLE_CAST = """\
/* Type conversion: combine an int score with a string label */
var score;
string label;
label = "Your score: ";
input score;
output label + int2str(score);
"""

SAMPLE_INT_CAST = """\
/* Type conversion: parse a string input as an integer, then do math */
string raw;
var n;
var result;
input raw;
n = str2int(raw);
result = n * 2 + 10;
output result;
"""

# ── Helper: scrollable Text widget ────────────────────────────────────────────
def make_textbox(parent, **kw):
    frame = tk.Frame(parent, bg=BG_EDITOR)
    cfg = dict(bg=BG_EDITOR, fg=FG, insertbackground=FG, font=MONO,
               relief="flat", bd=0, padx=8, pady=6,
               selectbackground=ACCENT, selectforeground="#fff",
               wrap="none", undo=True)
    cfg.update(kw)
    txt = tk.Text(frame, **cfg)
    vsb = ttk.Scrollbar(frame, orient="vertical",   command=txt.yview)
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=txt.xview)
    txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    txt.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    return frame, txt


# ── Application ────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ninjaz Compiler IDE")
        self.geometry("1150x700")
        self.minsize(820, 520)
        self.configure(bg=BG_DARK)
        self._style()
        self._build()
        self._load_code(SAMPLE_VALID)

    # ── Theme ──────────────────────────────────────────────────────────────────
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG_DARK, foreground=FG,
                    borderwidth=0, focuscolor=ACCENT)
        s.configure("TNotebook", background=BG_DARK, tabmargins=[2, 5, 0, 0])
        s.configure("TNotebook.Tab", background=BG_TAB, foreground=FG_DIM,
                    font=HD, padding=[14, 6])
        s.map("TNotebook.Tab",
              background=[("selected", BG_SEL)],
              foreground=[("selected", FG)])
        s.configure("TScrollbar", background=BG_PANEL,
                    troughcolor=BG_EDITOR, arrowcolor=FG_DIM, borderwidth=0)
        s.configure("TFrame", background=BG_DARK)
        s.configure("TPanedwindow", background=BG_DARK)

    # ── Layout ─────────────────────────────────────────────────────────────────
    def _build(self):
        self._build_header()
        self._build_main()
        self._build_statusbar()

    def _build_header(self):
        hdr = tk.Frame(self, bg=BG_PANEL, height=52)
        hdr.pack(side="top", fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="🥷  Ninjaz IDE",
                 bg=BG_PANEL, fg=FG_BLUE,
                 font=("Segoe UI Semibold", 14)).pack(side="left", padx=16)

        # Sample dropdown
        self._svar = tk.StringVar(value="Show Samples")
        self._samples = {
            "Show Samples":                    None,
            "✅  Valid (A * 3 + 2)":           SAMPLE_VALID,
            "➕  Arithmetic (X+Y)*Z":          SAMPLE_ARITH,
            "🔤  String greeting":             SAMPLE_STRING,
            "🔄  int2str() — int to string":    SAMPLE_CAST,
            "🔄  str2int() — string to int":    SAMPLE_INT_CAST,
            "❌  Invalid (undecl.)":           SAMPLE_INVALID,
        }
        om = tk.OptionMenu(hdr, self._svar, *self._samples,
                           command=self._on_sample)
        self._style_menu(om)
        om.pack(side="left", padx=6, pady=10)

        # Buttons (right-aligned)
        for txt, bg, cmd in [
            ("▶  Run",         "#22c55e", self._run),
            ("🔍  Check Only", "#3b82f6", lambda: self._run(check_only=True)),
            ("📂  Open",       BG_TAB,    self._open_file),
            ("✕  Clear",       "#ef4444", self._clear),
        ]:
            b = tk.Button(hdr, text=txt, bg=bg, fg="#e2e8f0",
                          activebackground=bg, activeforeground="#fff",
                          font=UI, relief="flat", bd=0,
                          padx=12, pady=5, cursor="hand2", command=cmd)
            b.pack(side="right", padx=(0, 8), pady=10)

    def _style_menu(self, om):
        om.config(bg=BG_TAB, fg=FG, activebackground=BG_SEL,
                  activeforeground=FG, relief="flat",
                  font=UI, highlightthickness=0, bd=0, padx=8)
        om["menu"].config(bg=BG_TAB, fg=FG, font=UI,
                          activebackground=ACCENT)

    def _build_main(self):
        pw = tk.PanedWindow(self, orient="horizontal",
                            bg="#3b3b5c", bd=0,
                            sashwidth=5, sashpad=0, sashrelief="flat")
        pw.pack(fill="both", expand=True, padx=0, pady=0)

        # ── Left: code editor ──
        lf = tk.Frame(pw, bg=BG_DARK)
        pw.add(lf, minsize=320, width=460)

        tk.Label(lf, text="  SOURCE CODE", bg=BG_DARK, fg=FG_DIM,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w",
                                                     padx=6, pady=(6, 0))
        ef, self._editor = make_textbox(lf)
        ef.pack(fill="both", expand=True, padx=6, pady=(2, 6))

        # ── Right: tabbed output ──
        rf = tk.Frame(pw, bg=BG_DARK)
        pw.add(rf, minsize=320)

        tk.Label(rf, text="  COMPILER OUTPUT", bg=BG_DARK, fg=FG_DIM,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w",
                                                     padx=6, pady=(6, 0))
        nb = ttk.Notebook(rf)
        nb.pack(fill="both", expand=True, padx=6, pady=(2, 6))

        self._tabs: dict[str, tk.Text] = {}
        for label in ("Output", "Tokens", "Syntax Tree", "Semantic"):
            frame = tk.Frame(nb, bg=BG_EDITOR)
            nb.add(frame, text=f"  {label}  ")
            _, txt = make_textbox(frame, state="disabled")
            txt.frame = frame          # keep ref
            # attach to frame grid
            txt.master.pack(fill="both", expand=True)
            self._tabs[label] = txt

        # colour tags for Output tab
        out = self._tabs["Output"]
        out.tag_configure("hdr",  foreground=FG_BLUE,
                          font=("Consolas", 11, "bold"))
        out.tag_configure("val",  foreground=FG_GREEN)
        out.tag_configure("mem",  foreground=FG_YELLOW)
        out.tag_configure("warn", foreground=FG_DIM)

        # colour tags for Semantic tab
        sem = self._tabs["Semantic"]
        sem.tag_configure("ok",  foreground=FG_GREEN)
        sem.tag_configure("err", foreground=FG_RED)
        sem.tag_configure("var", foreground=FG_PURPLE)

        # colour tags for Tokens tab
        tok = self._tabs["Tokens"]
        tok.tag_configure("kw",  foreground=FG_PURPLE)
        tok.tag_configure("num", foreground=FG_YELLOW)
        tok.tag_configure("str", foreground="#fab387")   # orange for string literals
        tok.tag_configure("id",  foreground=FG_BLUE)
        tok.tag_configure("op",  foreground=FG_GREEN)
        tok.tag_configure("eof", foreground=FG_DIM)

    def _build_statusbar(self):
        self._status = tk.StringVar(value="Ready.")
        self._sbar   = tk.Label(self, textvariable=self._status,
                                bg=BG_PANEL, fg=FG_DIM,
                                font=("Segoe UI", 9), anchor="w",
                                padx=10, pady=5)
        self._sbar.pack(side="bottom", fill="x")

    # ── Tab helpers ────────────────────────────────────────────────────────────
    def _clear_tab(self, name):
        t = self._tabs[name]
        t.configure(state="normal")
        t.delete("1.0", "end")
        t.configure(state="disabled")

    def _write(self, name, text, tag=None):
        t = self._tabs[name]
        t.configure(state="normal")
        if tag:
            t.insert("end", text, tag)
        else:
            t.insert("end", text)
        t.configure(state="disabled")

    def _set_status(self, msg, colour=FG_DIM):
        self._status.set(msg)
        self._sbar.configure(foreground=colour)

    # ── Actions ────────────────────────────────────────────────────────────────
    def _load_code(self, code):
        self._editor.delete("1.0", "end")
        self._editor.insert("1.0", code.strip())

    def _on_sample(self, choice):
        code = self._samples.get(choice)
        if code:
            self._load_code(code)
            self._set_status(f"Loaded sample: {choice.strip()}")
        self._svar.set("Load sample…")

    def _open_file(self):
        path = filedialog.askopenfilename(
            title="Open source file",
            filetypes=[("Min files", "*.min"),
                       ("Text files", "*.txt"),
                       ("All files", "*.*")],
            initialdir=os.getcwd(),
        )
        if path:
            with open(path, "r", encoding="utf-8") as f:
                self._load_code(f.read())
            self._set_status(f"Opened: {path}")

    def _clear(self):
        self._editor.delete("1.0", "end")
        for name in self._tabs:
            self._clear_tab(name)
        self._set_status("Editor cleared.")

    # ── Compilation ────────────────────────────────────────────────────────────
    def _run(self, check_only=False):
        source = self._editor.get("1.0", "end-1c").strip()
        if not source:
            self._set_status("⚠  Nothing to compile.", FG_YELLOW)
            return

        for name in self._tabs:
            self._clear_tab(name)
        self._set_status("⏳  Compiling…", FG_DIM)
        self.update_idletasks()

        try:
            # ── 1. Lexer ──────────────────────────────────────────────────────
            lexer  = Lexer(source)
            tokens = lexer.tokenize()
            self._show_tokens(tokens)

            # ── 2. Parser ─────────────────────────────────────────────────────
            ast = Parser(tokens).parse()
            self._write("Syntax Tree", "\n".join(ast_to_lines(ast)))

            # ── 3. Semantic analysis ──────────────────────────────────────────
            sem = SemanticAnalyzer()
            sem.analyze(ast)
            self._show_semantic(sem.symbols)

            if check_only:
                self._set_status(
                    "✅  Check complete — no errors found.", FG_GREEN)
                return

            # ── 4. Interpreter ────────────────────────────────────────────────
            interp = Interpreter(input_provider=self._ask_input)
            interp.execute(ast)
            self._show_output(interp.outputs, interp.memory)
            self._set_status(
                "✅  Compilation and execution successful.", FG_GREEN)

        except NinjazError as exc:
            kind = type(exc).__name__
            self._set_status(f"❌  {kind}: {exc}", FG_RED)
            self._show_error(kind, str(exc))

        except Exception as exc:
            import traceback
            self._set_status(f"💥  Unexpected internal error: {exc}", FG_RED)
            self._show_error("Unexpected Python Error", traceback.format_exc())

    # ── Display helpers ────────────────────────────────────────────────────────
    def _show_tokens(self, tokens):
        TYPE_TAG = {
            "VAR": "kw", "INPUT": "kw", "OUTPUT": "kw", "STRING_TYPE": "kw",
            "INT_CAST": "kw", "STR_CAST": "kw",
            "NUMBER": "num",
            "STRING_LITERAL": "str",
            "IDENTIFIER": "id",
            "EOF": "eof",
        }
        OP_TYPES = {"PLUS", "MINUS", "MUL", "DIV",
                    "ASSIGN", "LPAREN", "RPAREN", "SEMICOLON"}
        for tok in tokens:
            if tok.type in TYPE_TAG:
                tag = TYPE_TAG[tok.type]
            elif tok.type in OP_TYPES:
                tag = "op"
            else:
                tag = None
            line = f"{tok.type:<12}{tok.value!r:<10} @ line {tok.line}, col {tok.column}\n"
            self._write("Tokens", line, tag)

    def _show_semantic(self, symbols):
        self._write("Semantic", "✅ No semantic errors found.\n\n", "ok")
        declared = ", ".join(symbols) if symbols else "(none)"
        self._write("Semantic", "Declared variables:  ", None)
        self._write("Semantic", declared + "\n", "var")

    def _show_output(self, outputs, memory):
        self._write("Output", "═══ PROGRAM OUTPUT ═══\n\n", "hdr")
        if outputs:
            for v in outputs:
                self._write("Output", f"  {v}\n", "val")
        else:
            self._write("Output", "  (no output statements)\n", "warn")
        self._write("Output", "\n═══ FINAL MEMORY STATE ═══\n\n", "hdr")
        if memory:
            for name, val in memory.items():
                self._write("Output", f"  {name}  =  {val}\n", "mem")
        else:
            self._write("Output", "  (empty)\n", "warn")

    def _show_error(self, kind, msg):
        err_text = f"❌ {kind}\n\n{msg}\n"
        # Route error to the most relevant tab based on its kind, then fill any remaining blank tabs.
        ERROR_TAB = {
            "LexicalError":          "Tokens",
            "ParseError":            "Syntax Tree",
            "SemanticError":         "Semantic",
            "RuntimeLangError":      "Output",
            "Unexpected Python Error": "Output",
        }
        primary = ERROR_TAB.get(kind)
        if primary:
            t = self._tabs[primary]
            t.configure(state="normal")
            t.insert("end", err_text)
            t.configure(state="disabled")
        # Fill any remaining blank tabs with the same message so nothing looks empty
        for name in ("Tokens", "Syntax Tree", "Semantic", "Output"):
            if name == primary:
                continue
            t = self._tabs[name]
            if not t.get("1.0", "end").strip():
                t.configure(state="normal")
                t.insert("end", err_text)
                t.configure(state="disabled")

    def _ask_input(self, prompt: str) -> str:
        """Input provider for the Interpreter — shows a modal dialog."""
        from ninjaz_compiler import RuntimeLangError
        val = simpledialog.askstring("Program Input", prompt, parent=self)
        if val is None:
            raise RuntimeLangError("Program input was cancelled by the user.")
        return val


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    App().mainloop()
