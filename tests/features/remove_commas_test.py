from __future__ import annotations

import pytest

from add_trailing_comma._main import _fix_src


@pytest.mark.parametrize(
    ('src', 'expected'),
    (
        # can't rewrite 1-element tuple
        ('(1,)', '(1,)'),
        # but I do want the whitespace fixed!
        ('(1, )', '(1,)'),
        ('(1, 2,)', '(1, 2)'),
        ('[1, 2,]', '[1, 2]'),
        ('[1, 2,   ]', '[1, 2]'),
        ('{1, 2, }', '{1, 2}'),
        ('{1: 2, }', '{1: 2}'),
        ('f(1, 2,)', 'f(1, 2)'),
    ),
)
def test_remove_extra_comma(src, expected):
    assert _fix_src(src) == expected


@pytest.mark.parametrize(
    ('src', 'expected'),
    (
        ('x = (foo(),)\n', 'x = (foo(),)\n'),
        ('x = (foo.bar,)\n', 'x = (foo.bar,)\n'),
        ('x = (foo[0],)\n', 'x = (foo[0],)\n'),
        ('x = ((1, 2),)\n', 'x = ((1, 2),)\n'),
        ('x = ([1, 2],)\n', 'x = ([1, 2],)\n'),
        ('x = ( 1,)\n', 'x = ( 1,)\n'),
        ('x = (1, )\n', 'x = (1,)\n'),
        ('x = (\n    1,\n)\n', 'x = (\n    1,\n)\n'),
        ('x = 1,\n', 'x = 1,\n'),
        ('x[1,]\n', 'x[1,]\n'),
        (
            'match x:\n'
            '    case (y,):\n'
            '        pass\n',
            'match x:\n'
            '    case (y,):\n'
            '        pass\n',
        ),
        (
            'match x:\n'
            '    case [y,]:\n'
            '        pass\n',
            'match x:\n'
            '    case [y]:\n'
            '        pass\n',
        ),
    ),
)
def test_remove_comma_preserves_one_element_tuple_commas(src, expected):
    assert _fix_src(src, remove_comma=True) == expected


def test_remove_comma_removes_nested_optional_commas():
    src = (
        'x = (\n'
        '    (1, 2,),\n'
        '    [3, 4,],\n'
        ')\n'
        'def f(\n'
        '    arg,\n'
        '):\n'
        '    return g(\n'
        '        arg,\n'
        '    )\n'
    )
    expected = (
        'x = (\n'
        '    (1, 2),\n'
        '    [3, 4]\n'
        ')\n'
        'def f(\n'
        '    arg\n'
        '):\n'
        '    return g(\n'
        '        arg\n'
        '    )\n'
    )
    assert _fix_src(src, remove_comma=True) == expected


def test_remove_comma_noops_when_last_item_has_no_comma():
    src = (
        'x = (\n'
        '    1,\n'
        '    2\n'
        ')\n'
    )
    assert _fix_src(src, remove_comma=True) == src


def test_remove_comma_noops_on_syntax_error():
    src = 'print 1\n'
    assert _fix_src(src, remove_comma=True) == src


def test_remove_comma_preserves_fstring_format_spec_commas():
    src = (
        'tokens = 1234\n'
        'message = f"{tokens:,}"\n'
        'size = f"Size: {len(message):,} bytes"\n'
        'value = f"{foo(1,)}"\n'
    )
    expected = (
        'tokens = 1234\n'
        'message = f"{tokens:,}"\n'
        'size = f"Size: {len(message):,} bytes"\n'
        'value = f"{foo(1)}"\n'
    )
    assert _fix_src(src, remove_comma=True) == expected
