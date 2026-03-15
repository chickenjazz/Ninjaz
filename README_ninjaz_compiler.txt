Ninjaz Compiler / Interpreter

Files:
- ninjaz_compiler.py          -> actual program
- sample_valid.min          -> sample valid input program
- sample_invalid.min        -> sample invalid input program

How to run:
1. Open terminal / command prompt.
2. Run:
   python ninjaz_compiler.py sample_valid.min

Other commands:
- python ninjaz_compiler.py --demo
- python ninjaz_compiler.py --repl
- python ninjaz_compiler.py sample_valid.min --check-only

What it does:
- Lexical analysis (tokenization)
- Syntax analysis (parsing into syntax tree)
- Semantic analysis (checks declaration-before-use)
- Execution / interpretation

Language syntax:
- var x;
- input x;
- x = 3 + 4 * (2 - 1);
- output x;
