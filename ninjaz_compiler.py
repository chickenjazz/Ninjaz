#!/usr/bin/env python3
"""
Ninjaz compiler / interpreter for a simple integer-based language.

Language rules implemented from the project specification:
- Statements end with semicolons.
- Whitespace is ignored.
- Comments use /* ... */ and may span multiple lines.
- Keywords: var, input, output.
- All variables are integers.
- Operators: +, -, *, /, =.
- Parentheses are allowed.
- Variable names may contain letters, digits, and underscores, but cannot start with a digit.

Pipeline:
1. Lexical analysis
2. Syntax analysis (recursive descent parser)
3. Semantic analysis
4. Interpretation / execution

Usage:
    python ninjaz_compiler.py program.txt
    python ninjaz_compiler.py --demo
    python ninjaz_compiler.py --repl
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Union
import argparse
import sys


# =========================
# Errors
# =========================

class NinjazError(Exception):
    """Base class for language errors."""


class LexicalError(NinjazError):
    pass


class ParseError(NinjazError):
    pass


class SemanticError(NinjazError):
    pass


class RuntimeLangError(NinjazError):
    pass


# =========================
# Token definitions
# =========================

@dataclass(frozen=True)
class Token:
    type: str
    value: str
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.type:<10} {self.value!r} @ line {self.line}, col {self.column}"


KEYWORDS = {"var": "VAR", "input": "INPUT", "output": "OUTPUT", "string": "STRING_TYPE"}
SINGLE_CHAR_TOKENS = {
    ';': 'SEMICOLON',
    '+': 'PLUS',
    '-': 'MINUS',
    '*': 'MUL',
    '/': 'DIV',
    '=': 'ASSIGN',
    '(': 'LPAREN',
    ')': 'RPAREN',
}


# =========================
# Lexer
# =========================

class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1

    def current_char(self) -> Optional[str]:
        if self.pos >= len(self.text):
            return None
        return self.text[self.pos]

    def peek(self) -> Optional[str]:
        if self.pos + 1 >= len(self.text):
            return None
        return self.text[self.pos + 1]

    def advance(self) -> None:
        if self.pos < len(self.text):
            if self.text[self.pos] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1

    def skip_whitespace(self) -> None:
        while (ch := self.current_char()) is not None and ch.isspace():
            self.advance()

    def skip_comment(self) -> None:
        # Assumes current position starts at '/'.
        start_line, start_col = self.line, self.column
        self.advance()  # /
        self.advance()  # *
        while True:
            ch = self.current_char()
            if ch is None:
                raise LexicalError(
                    f"Unterminated comment starting at line {start_line}, col {start_col}."
                )
            if ch == '*' and self.peek() == '/':
                self.advance()
                self.advance()
                return
            self.advance()

    def identifier_or_keyword(self) -> Token:
        start_line, start_col = self.line, self.column
        lexeme = []
        ch = self.current_char()
        if ch is None or not (ch.isalpha() or ch == '_'):
            raise LexicalError(
                f"Invalid identifier start {ch!r} at line {start_line}, col {start_col}."
            )
        while (ch := self.current_char()) is not None and (ch.isalnum() or ch == '_'):
            lexeme.append(ch)
            self.advance()
        value = ''.join(lexeme)
        token_type = KEYWORDS.get(value, 'IDENTIFIER')
        return Token(token_type, value, start_line, start_col)

    def number(self) -> Token:
        start_line, start_col = self.line, self.column
        digits = []
        while (ch := self.current_char()) is not None and ch.isdigit():
            digits.append(ch)
            self.advance()
        value = ''.join(digits)

        # Reject names like 123abc explicitly as invalid variable names / malformed token.
        next_ch = self.current_char()
        if next_ch is not None and (next_ch.isalpha() or next_ch == '_'):
            bad = [value]
            while (ch := self.current_char()) is not None and (ch.isalnum() or ch == '_'):
                bad.append(ch)
                self.advance()
            raise LexicalError(
                f"Invalid token {''.join(bad)!r} at line {start_line}, col {start_col}. "
                f"Variable names cannot start with a number."
            )

        return Token('NUMBER', value, start_line, start_col)

    def string_literal(self) -> Token:
        start_line, start_col = self.line, self.column
        self.advance()  # opening "
        chars: List[str] = []
        while True:
            ch = self.current_char()
            if ch is None:
                raise LexicalError(
                    f"Unterminated string literal starting at line {start_line}, col {start_col}."
                )
            if ch == '"':
                self.advance()  # closing "
                break
            if ch == '\\':
                self.advance()
                esc = self.current_char()
                if esc == 'n':  chars.append('\n')
                elif esc == 't': chars.append('\t')
                elif esc == '"': chars.append('"')
                elif esc == '\\': chars.append('\\')
                else: chars.append('\\' + (esc or ''))
                self.advance()
                continue
            chars.append(ch)
            self.advance()
        return Token('STRING_LITERAL', ''.join(chars), start_line, start_col)

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

        while (ch := self.current_char()) is not None:
            if ch.isspace():
                self.skip_whitespace()
                continue

            if ch == '/' and self.peek() == '*':
                self.skip_comment()
                continue

            if ch.isalpha() or ch == '_':
                tokens.append(self.identifier_or_keyword())
                continue

            if ch.isdigit():
                tokens.append(self.number())
                continue

            if ch == '"':
                tokens.append(self.string_literal())
                continue

            if ch in SINGLE_CHAR_TOKENS:
                tokens.append(Token(SINGLE_CHAR_TOKENS[ch], ch, self.line, self.column))
                self.advance()
                continue

            raise LexicalError(f"Unexpected character {ch!r} at line {self.line}, col {self.column}.")

        tokens.append(Token('EOF', '', self.line, self.column))
        return tokens


# =========================
# AST nodes
# =========================

class ASTNode:
    pass


@dataclass
class Program(ASTNode):
    statements: List[ASTNode]


@dataclass
class VarDecl(ASTNode):
    name: str


@dataclass
class InputStmt(ASTNode):
    name: str


@dataclass
class OutputStmt(ASTNode):
    expr: ASTNode


@dataclass
class AssignStmt(ASTNode):
    name: str
    expr: ASTNode


@dataclass
class BinOp(ASTNode):
    left: ASTNode
    op: str
    right: ASTNode


@dataclass
class UnaryOp(ASTNode):
    op: str
    expr: ASTNode


@dataclass
class Num(ASTNode):
    value: int


@dataclass
class Var(ASTNode):
    name: str


@dataclass
class StringDecl(ASTNode):
    name: str


@dataclass
class StringLit(ASTNode):
    value: str


# =========================
# Parser
# =========================

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def current(self) -> Token:
        return self.tokens[self.pos]

    def eat(self, token_type: str) -> Token:
        token = self.current()
        if token.type != token_type:
            raise ParseError(
                f"Expected {token_type}, found {token.type} ({token.value!r}) "
                f"at line {token.line}, col {token.column}."
            )
        self.pos += 1
        return token

    def parse(self) -> Program:
        statements = []
        while self.current().type != 'EOF':
            statements.append(self.statement())
        return Program(statements)

    def statement(self) -> ASTNode:
        token = self.current()
        if token.type == 'VAR':
            node = self.var_decl()
            self.eat('SEMICOLON')
            return node
        if token.type == 'STRING_TYPE':
            node = self.string_decl()
            self.eat('SEMICOLON')
            return node
        if token.type == 'INPUT':
            node = self.input_stmt()
            self.eat('SEMICOLON')
            return node
        if token.type == 'OUTPUT':
            node = self.output_stmt()
            self.eat('SEMICOLON')
            return node
        if token.type == 'IDENTIFIER':
            node = self.assign_stmt()
            self.eat('SEMICOLON')
            return node
        raise ParseError(
            f"Invalid statement starting with {token.type} ({token.value!r}) "
            f"at line {token.line}, col {token.column}."
        )

    def var_decl(self) -> VarDecl:
        self.eat('VAR')
        name = self.eat('IDENTIFIER').value
        return VarDecl(name)

    def string_decl(self) -> StringDecl:
        self.eat('STRING_TYPE')
        name = self.eat('IDENTIFIER').value
        return StringDecl(name)

    def input_stmt(self) -> InputStmt:
        self.eat('INPUT')
        name = self.eat('IDENTIFIER').value
        return InputStmt(name)

    def output_stmt(self) -> OutputStmt:
        self.eat('OUTPUT')
        expr = self.expr()
        return OutputStmt(expr)

    def assign_stmt(self) -> AssignStmt:
        name = self.eat('IDENTIFIER').value
        self.eat('ASSIGN')
        expr = self.expr()
        return AssignStmt(name, expr)

    def expr(self) -> ASTNode:
        node = self.term()
        while self.current().type in ('PLUS', 'MINUS'):
            op = self.eat(self.current().type).value
            node = BinOp(node, op, self.term())
        return node

    def term(self) -> ASTNode:
        node = self.factor()
        while self.current().type in ('MUL', 'DIV'):
            op = self.eat(self.current().type).value
            node = BinOp(node, op, self.factor())
        return node

    def factor(self) -> ASTNode:
        token = self.current()
        if token.type == 'PLUS':
            self.eat('PLUS')
            return UnaryOp('+', self.factor())
        if token.type == 'MINUS':
            self.eat('MINUS')
            return UnaryOp('-', self.factor())
        if token.type == 'NUMBER':
            return Num(int(self.eat('NUMBER').value))
        if token.type == 'IDENTIFIER':
            return Var(self.eat('IDENTIFIER').value)
        if token.type == 'STRING_LITERAL':
            return StringLit(self.eat('STRING_LITERAL').value)
        if token.type == 'LPAREN':
            self.eat('LPAREN')
            node = self.expr()
            self.eat('RPAREN')
            return node
        raise ParseError(
            f"Unexpected token {token.type} ({token.value!r}) at line {token.line}, col {token.column}."
        )


# =========================
# Semantic analysis
# =========================

class SemanticAnalyzer:
    def __init__(self):
        self.symbols: Dict[str, str] = {}

    def analyze(self, node: ASTNode) -> str:
        """Recursively analyze a node and return its resolved type ('int' or 'str')."""
        method_name = f"visit_{type(node).__name__}"
        method = getattr(self, method_name, self.generic_visit)
        return method(node)

    def generic_visit(self, node: ASTNode) -> str:
        raise SemanticError(f"No semantic visitor for {type(node).__name__}.")

    def visit_Program(self, node: Program) -> None:
        for stmt in node.statements:
            self.analyze(stmt)

    def visit_VarDecl(self, node: VarDecl) -> None:
        if node.name in self.symbols:
            raise SemanticError(f"Variable '{node.name}' is already declared.")
        self.symbols[node.name] = 'int'

    def visit_StringDecl(self, node: StringDecl) -> None:
        if node.name in self.symbols:
            raise SemanticError(f"Variable '{node.name}' is already declared.")
        self.symbols[node.name] = 'str'

    def visit_InputStmt(self, node: InputStmt) -> None:
        self.ensure_declared(node.name)

    def visit_OutputStmt(self, node: OutputStmt) -> None:
        self.analyze(node.expr)

    def visit_AssignStmt(self, node: AssignStmt) -> None:
        var_type = self.ensure_declared(node.name)
        expr_type = self.analyze(node.expr)
        if expr_type != var_type:
            raise SemanticError(
                f"Type mismatch: cannot assign a '{expr_type}' expression "
                f"to variable '{node.name}' which was declared as '{var_type}'."
            )

    def visit_BinOp(self, node: BinOp) -> str:
        left_type  = self.analyze(node.left)
        right_type = self.analyze(node.right)
        if node.op == '+':
            if left_type != right_type:
                raise SemanticError(
                    f"Type mismatch: cannot use '+' between a '{left_type}' and a '{right_type}'. "
                    f"Both operands must be the same type (both 'int' for addition, or both 'str' for concatenation)."
                )
            return left_type   # 'int' + 'int' -> 'int', 'str' + 'str' -> 'str'
        else:
            # -, *, / only valid for integers
            if left_type == 'str' or right_type == 'str':
                raise SemanticError(
                    f"Operator '{node.op}' is not supported for string values."
                )
            return 'int'

    def visit_UnaryOp(self, node: UnaryOp) -> str:
        expr_type = self.analyze(node.expr)
        if expr_type == 'str':
            raise SemanticError(
                f"Unary operator '{node.op}' is not supported for string values."
            )
        return 'int'

    def visit_Num(self, node: Num) -> str:
        return 'int'

    def visit_StringLit(self, node: StringLit) -> str:
        return 'str'

    def visit_Var(self, node: Var) -> str:
        return self.ensure_declared(node.name)

    def ensure_declared(self, name: str) -> str:
        if name not in self.symbols:
            raise SemanticError(f"Variable '{name}' used before declaration.")
        return self.symbols[name]


# =========================
# Interpreter
# =========================

class Interpreter:
    def __init__(self, input_provider=None):
        self.memory: Dict[str, Union[int, str]] = {}
        self.outputs: List[Union[int, str]] = []
        self.input_provider = input_provider or input

    def execute(self, node: ASTNode) -> Optional[int]:
        method_name = f"visit_{type(node).__name__}"
        method = getattr(self, method_name, self.generic_visit)
        return method(node)

    def generic_visit(self, node: ASTNode):
        raise RuntimeLangError(f"No runtime visitor for {type(node).__name__}.")

    def visit_Program(self, node: Program) -> None:
        for stmt in node.statements:
            self.execute(stmt)

    def visit_VarDecl(self, node: VarDecl) -> None:
        self.memory[node.name] = 0

    def visit_StringDecl(self, node: StringDecl) -> None:
        self.memory[node.name] = ''

    def visit_InputStmt(self, node: InputStmt) -> None:
        is_string = isinstance(self.memory.get(node.name), str)
        prompt = f"Enter {'text' if is_string else 'integer'} for {node.name}: "
        raw = self.input_provider(prompt)
        if is_string:
            self.memory[node.name] = raw
        else:
            try:
                self.memory[node.name] = int(raw)
            except ValueError as exc:
                raise RuntimeLangError(f"Input for '{node.name}' must be an integer.") from exc

    def visit_OutputStmt(self, node: OutputStmt) -> None:
        value = self.execute(node.expr)
        self.outputs.append(value)
        print(value)

    def visit_AssignStmt(self, node: AssignStmt) -> None:
        self.memory[node.name] = self.execute(node.expr)

    def visit_BinOp(self, node: BinOp) -> Union[int, str]:
        left = self.execute(node.left)
        right = self.execute(node.right)
        # String concatenation (str + str only)
        if node.op == '+' and isinstance(left, str) and isinstance(right, str):
            return left + right
        # Mixed str+int with + is a type error (should have been caught by semantic analysis)
        if node.op == '+' and (isinstance(left, str) or isinstance(right, str)):
            raise RuntimeLangError(
                f"Type mismatch: cannot use '+' between a string and an integer."
            )
        # Arithmetic (integers only)
        if isinstance(left, str) or isinstance(right, str):
            raise RuntimeLangError(
                f"Operator '{node.op}' is not supported for string values."
            )
        if node.op == '+':
            return left + right
        if node.op == '-':
            return left - right
        if node.op == '*':
            return left * right
        if node.op == '/':
            if right == 0:
                raise RuntimeLangError('Division by zero.')
            return left // right
        raise RuntimeLangError(f"Unknown operator {node.op!r}.")

    def visit_UnaryOp(self, node: UnaryOp) -> int:
        value = self.execute(node.expr)
        if isinstance(value, str):
            raise RuntimeLangError(
                f"Unary operator '{node.op}' is not supported for string values."
            )
        return value if node.op == '+' else -value

    def visit_Num(self, node: Num) -> int:
        return node.value

    def visit_StringLit(self, node: StringLit) -> str:
        return node.value

    def visit_Var(self, node: Var) -> Union[int, str]:
        if node.name not in self.memory:
            raise RuntimeLangError(f"Variable '{node.name}' has no runtime value.")
        return self.memory[node.name]


# =========================
# AST pretty-printer
# =========================

def ast_to_lines(node: ASTNode, indent: str = "") -> List[str]:
    lines: List[str] = []

    if isinstance(node, Program):
        lines.append(f"{indent}Program")
        for stmt in node.statements:
            lines.extend(ast_to_lines(stmt, indent + "  "))
    elif isinstance(node, VarDecl):
        lines.append(f"{indent}VarDecl({node.name})")
    elif isinstance(node, StringDecl):
        lines.append(f"{indent}StringDecl({node.name})")
    elif isinstance(node, InputStmt):
        lines.append(f"{indent}Input({node.name})")
    elif isinstance(node, OutputStmt):
        lines.append(f"{indent}Output")
        lines.extend(ast_to_lines(node.expr, indent + "  "))
    elif isinstance(node, AssignStmt):
        lines.append(f"{indent}Assign({node.name})")
        lines.extend(ast_to_lines(node.expr, indent + "  "))
    elif isinstance(node, BinOp):
        lines.append(f"{indent}BinOp({node.op})")
        lines.extend(ast_to_lines(node.left, indent + "  "))
        lines.extend(ast_to_lines(node.right, indent + "  "))
    elif isinstance(node, UnaryOp):
        lines.append(f"{indent}UnaryOp({node.op})")
        lines.extend(ast_to_lines(node.expr, indent + "  "))
    elif isinstance(node, Num):
        lines.append(f"{indent}Num({node.value})")
    elif isinstance(node, StringLit):
        lines.append(f"{indent}StringLit({node.value!r})")
    elif isinstance(node, Var):
        lines.append(f"{indent}Var({node.name})")
    else:
        lines.append(f"{indent}{type(node).__name__}")

    return lines


# =========================
# Driver helpers
# =========================

def compile_source(source: str, *, show_tokens: bool = True, show_ast: bool = True, execute: bool = True) -> Dict[str, Union[List[Token], Program, Dict[str, str], Dict[str, int]]]:
    lexer = Lexer(source)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    ast = parser.parse()

    semantic = SemanticAnalyzer()
    semantic.analyze(ast)

    result: Dict[str, Union[List[Token], Program, Dict[str, str], Dict[str, int]]] = {
        'tokens': tokens,
        'ast': ast,
        'symbols': semantic.symbols,
    }

    if show_tokens:
        print("\n=== TOKENS ===")
        for token in tokens:
            print(token)

    if show_ast:
        print("\n=== SYNTAX TREE ===")
        print('\n'.join(ast_to_lines(ast)))

    print("\n=== SEMANTIC ANALYSIS ===")
    print("No semantic errors found.")
    print(f"Declared variables: {', '.join(semantic.symbols) if semantic.symbols else '(none)'}")

    if execute:
        print("\n=== PROGRAM OUTPUT ===")
        interpreter = Interpreter()
        interpreter.execute(ast)
        result['memory'] = interpreter.memory
        print("\n=== FINAL MEMORY STATE ===")
        if interpreter.memory:
            for name, value in interpreter.memory.items():
                print(f"{name} = {value}")
        else:
            print("(empty)")

    return result


DEMO_PROGRAM = """/* Sample valid program */
var x;
var y;
input x;
y = (x + 5) * 2;
output y;
"""


def repl() -> None:
    print("Ninjaz Language REPL")
    print("Enter your program. Type END on its own line to compile. Type EXIT to quit.")
    while True:
        lines = []
        while True:
            line = input("... ")
            if line.strip().upper() == 'EXIT':
                return
            if line.strip().upper() == 'END':
                break
            lines.append(line)
        source = '\n'.join(lines)
        try:
            compile_source(source)
        except NinjazError as exc:
            print(f"\nERROR: {exc}\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Ninjaz compiler / interpreter for the project specification.")
    ap.add_argument('file', nargs='?', help='Path to the source program file.')
    ap.add_argument('--demo', action='store_true', help='Run the built-in demo program.')
    ap.add_argument('--repl', action='store_true', help='Start the Ninjaz-language REPL.')
    ap.add_argument('--no-tokens', action='store_true', help='Do not print the token list.')
    ap.add_argument('--no-ast', action='store_true', help='Do not print the syntax tree.')
    ap.add_argument('--check-only', action='store_true', help='Only analyze; do not execute.')
    args = ap.parse_args()

    try:
        if args.repl:
            repl()
            return 0

        if args.demo:
            source = DEMO_PROGRAM
        elif args.file:
            with open(args.file, 'r', encoding='utf-8') as f:
                source = f.read()
        else:
            print("Provide a source file, or use --demo or --repl.")
            return 1

        compile_source(
            source,
            show_tokens=not args.no_tokens,
            show_ast=not args.no_ast,
            execute=not args.check_only,
        )
        return 0

    except NinjazError as exc:
        print(f"ERROR: {exc}")
        return 1
    except FileNotFoundError:
        print(f"ERROR: File not found: {args.file}")
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
