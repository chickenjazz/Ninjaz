# Ninjaz Compiler / Interpreter

## Description
The Ninjaz Compiler is a custom miniature compiler and interpreter designed for a simple statically-typed language. It performs full compilation phases including lexical analysis (tokenization), syntax analysis (parsing into an Abstract Syntax Tree), semantic analysis (type checking and declaration-before-use validation), and execution (interpreting the syntax tree). It comes with a CLI as well as a GUI environment (Ninjaz IDE).

## Contributors
- Rayan Chuayap
- Justin Manuzon
- Gabrielle San Diego
- Josephine Santander

## Files
- `ninjaz_compiler.py`          -> Actual compiler backend and CLI
- `ninjaz_compiler_gui.py`      -> Ninjaz IDE front-end graphical interface
- `NinjazCompilerIDE.spec`      -> PyInstaller specification file to rebuild the standalone executable
- `dist/NinjazCompilerIDE.exe`  -> Standalone executable of the Ninjaz IDE and Compiler
- `sample_valid.min`            -> Sample valid input program
- `sample_invalid.min`          -> Sample invalid input program

## How to Run

1. Open your terminal or command prompt.
2. Run the compiler against a specific file:
   ```bash
   python ninjaz_compiler.py sample_valid.min
   ```

### Other Commands
- **Interactive Demo**: `python ninjaz_compiler.py --demo`
- **REPL (Read-Eval-Print Loop)**: `python ninjaz_compiler.py --repl`
- **Syntax & Semantic Check Only**: `python ninjaz_compiler.py sample_valid.min --check-only`
- **Launch GUI (Ninjaz IDE)**: `python ninjaz_compiler_gui.py`

### Running the Standalone Executable
For users without Python installed, you can simply double-click or run the bundled executable located at `dist/NinjazCompilerIDE.exe`. This launches the full graphical IDE directly and doesn't require any python dependencies.

### Rebuilding the Executable
If you modify the source code and want to rebuild the `.exe`, you can use the included PyInstaller specification file. With PyInstaller installed, run:
```bash
python -m PyInstaller --noconfirm NinjazCompilerIDE.spec
```

## Features & Implementation Phases
- **Lexical Analysis**: Tokenizes the raw source code.
- **Syntax Analysis**: Parses the tokens into a structured Abstract Syntax Tree (AST).
- **Semantic Analysis**: Ensures semantic validity (e.g., verifying variables are declared before they are used).
- **Execution**: Interprets and runs the AST directly.

## Language Syntax Rules
- Every statement must end with a semicolon `;`.
- Integer variables must be declared using `var <name>;` before use.
- String variables must be declared using `string <name>;` before use.
- Use `input <name>;` to read a value into a variable.
- Use `output <expr>;` to print a value.
- Arithmetic expressions support `+`, `-`, `*`, `/`, and parentheses `()`.
- String concatenation uses `+` between two `string` values.
- Types are **statically checked** — mixing `int` and `string` in an expression is a compile-time error.

### Type Conversion
Use the built-in cast functions to explicitly convert between types:

| Function | Converts | Example |
|----------|----------|---------|
| `str2int(expr)` | string → integer | `str2int("42")` → `42` |
| `int2str(expr)` | integer → string | `int2str(42)` → `"42"` |

> **Note:** `str2int(expr)` raises a runtime error if the string cannot be parsed as a valid integer (e.g. `str2int("hello")`).

### Examples

**Integer arithmetic:**
```min
var x;
input x;
x = 3 + 4 * (2 - 1);
output x;
```

**String concatenation:**
```min
string first;
string last;
input first;
input last;
output first + " " + last;
```

**Type conversion — combining an integer with a string:**
```min
var score;
string label;
label = "Score: ";
input score;
output label + int2str(score);
```
