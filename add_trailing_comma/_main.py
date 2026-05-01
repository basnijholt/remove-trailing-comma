from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Sequence

from tokenize_rt import NON_CODING_TOKENS
from tokenize_rt import Offset
from tokenize_rt import src_to_tokens
from tokenize_rt import Token
from tokenize_rt import tokens_to_src

from add_trailing_comma._ast_helpers import ast_parse
from add_trailing_comma._ast_helpers import ast_to_offset
from add_trailing_comma._data import FUNCS
from add_trailing_comma._data import visit
from add_trailing_comma._token_helpers import find_simple
from add_trailing_comma._token_helpers import Fix
from add_trailing_comma._token_helpers import fix_brace
from add_trailing_comma._token_helpers import START_BRACES

FixCallback = Callable[[int, list[Token]], Fix | None]


def _changing_list(lst: list[Token]) -> Iterable[tuple[int, Token]]:
    i = 0
    while i < len(lst):
        yield i, lst[i]
        i += 1


def _find_tuple(i: int, tokens: list[Token]) -> Fix | None:
    i -= 1
    while tokens[i].name in NON_CODING_TOKENS:
        i -= 1

    if tokens[i].src not in '([':
        return None

    return find_simple(i, tokens)


def _find_simple(i: int, tokens: list[Token]) -> Fix | None:
    return find_simple(i, tokens)


def _find_match_sequence(i: int, tokens: list[Token]) -> Fix | None:
    if tokens[i].src == '(':
        return find_simple(i, tokens)
    else:
        return None


def _required_comma_fixes(
        ast_obj: ast.Module,
        tokens: list[Token],
) -> set[tuple[int, int]]:
    callbacks: dict[Offset, list[FixCallback]] = {}
    for node in ast.walk(ast_obj):
        if isinstance(node, ast.Tuple) and len(node.elts) == 1:
            if ast_to_offset(node) == ast_to_offset(node.elts[0]):
                func = _find_tuple
            else:
                func = _find_simple
            callbacks.setdefault(ast_to_offset(node), []).append(func)
        elif isinstance(node, ast.MatchSequence) and len(node.patterns) == 1:
            callbacks.setdefault(ast_to_offset(node), []).append(
                _find_match_sequence,
            )

    ret = set()
    for i, token in enumerate(tokens):
        for callback in callbacks.get(token.offset, ()):
            fix = callback(i, tokens)
            if fix is not None:
                ret.add(fix.braces)

    return ret


def _remove_optional_comma(tokens: list[Token], fix: Fix) -> None:
    first_brace, last_brace = fix.braces
    i = last_brace - 1
    while i > first_brace and tokens[i].name in NON_CODING_TOKENS:
        i -= 1

    if tokens[i].src != ',':
        return
    elif fix.remove_comma:
        del tokens[i:last_brace]
    else:
        del tokens[i:i + 1]


def _fix_required_comma(tokens: list[Token], fix: Fix) -> None:
    if not fix.remove_comma:
        return

    first_brace, last_brace = fix.braces
    i = last_brace - 1
    while i > first_brace and tokens[i].name in NON_CODING_TOKENS:
        i -= 1

    assert tokens[i].src == ','
    del tokens[i + 1:last_brace]


def _fix_braces(tokens: list[Token]) -> None:
    for i, token in _changing_list(tokens):
        if token.name == 'OP' and token.src in START_BRACES:
            fix_brace(
                tokens, find_simple(i, tokens),
                add_comma=False,
                remove_comma=False,
            )


def _remove_trailing_commas(contents_text: str) -> str:
    try:
        ast_obj = ast_parse(contents_text)
    except SyntaxError:
        return contents_text

    tokens = src_to_tokens(contents_text)
    required_comma_fixes = _required_comma_fixes(ast_obj, tokens)
    fixes = []
    for i, token in enumerate(tokens):
        if token.name == 'OP' and token.src in START_BRACES:
            fix_data = find_simple(i, tokens)
            if fix_data is not None and fix_data.multi_arg:
                fixes.append(fix_data)

    for fix in sorted(fixes, key=lambda fix: fix.braces[1], reverse=True):
        if fix.braces in required_comma_fixes:
            _fix_required_comma(tokens, fix)
        else:
            _remove_optional_comma(tokens, fix)

    _fix_braces(tokens)
    return tokens_to_src(tokens)


def _fix_src(contents_text: str, *, remove_comma: bool = False) -> str:
    if remove_comma:
        return _remove_trailing_commas(contents_text)

    try:
        ast_obj = ast_parse(contents_text)
    except SyntaxError:
        return contents_text

    callbacks = visit(FUNCS, ast_obj)

    tokens = src_to_tokens(contents_text)
    for i, token in _changing_list(tokens):
        # DEDENT is a zero length token
        if not token.src:
            continue

        # though this is a defaultdict, by using `.get()` this function's
        # self time is almost 50% faster
        for callback in callbacks.get(token.offset, ()):
            callback(i, tokens)

    _fix_braces(tokens)

    return tokens_to_src(tokens)


def fix_file(filename: str, args: argparse.Namespace) -> int:
    if filename == '-':
        contents_bytes = sys.stdin.buffer.read()
    else:
        with open(filename, 'rb') as fb:
            contents_bytes = fb.read()

    try:
        contents_text_orig = contents_text = contents_bytes.decode()
    except UnicodeDecodeError:
        msg = f'{filename} is non-utf-8 (not supported)'
        print(msg, file=sys.stderr)
        return 1

    contents_text = _fix_src(contents_text, remove_comma=args.remove_comma)

    if filename == '-':
        print(contents_text, end='')
    elif contents_text != contents_text_orig:
        print(f'Rewriting {filename}', file=sys.stderr)
        with open(filename, 'wb') as f:
            f.write(contents_text.encode())

    if args.exit_zero_even_if_changed:
        return 0
    else:
        return contents_text != contents_text_orig


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='*')
    parser.add_argument('--exit-zero-even-if-changed', action='store_true')
    parser.add_argument('--py35-plus', action='store_true')
    parser.add_argument('--py36-plus', action='store_true')
    parser.add_argument(
        '--remove-comma',
        action='store_true',
        help='Remove trailing commas instead of adding them',
    )
    args = parser.parse_args(argv)

    if args.py35_plus or args.py36_plus:
        print('WARNING: --py35-plus / --py36-plus do nothing', file=sys.stderr)

    ret = 0
    for filename in args.filenames:
        ret |= fix_file(filename, args)
    return ret


if __name__ == '__main__':
    raise SystemExit(main())
