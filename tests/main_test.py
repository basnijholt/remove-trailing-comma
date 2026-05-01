from __future__ import annotations

import io
import pathlib
import sys
import tomllib
from unittest import mock

from add_trailing_comma._main import main
from add_trailing_comma._main import remove_main


def test_main_trivial():
    assert main(()) == 0


def test_remove_main_trivial():
    assert remove_main(()) == 0


def test_project_defines_remove_trailing_comma_script():
    pyproject = tomllib.loads(
        pathlib.Path('pyproject.toml').read_text(encoding='UTF-8'),
    )
    assert pyproject['project']['name'] == 'remove-trailing-comma'
    assert pyproject['project']['scripts']['remove-trailing-comma'] == (
        'add_trailing_comma._main:remove_main'
    )


def test_project_defines_remove_trailing_comma_hook():
    hooks_text = pathlib.Path('.pre-commit-hooks.yaml').read_text(
        encoding='UTF-8',
    )
    assert '-   id: remove-trailing-comma\n' in hooks_text
    assert 'entry: remove-trailing-comma\n' in hooks_text


def test_release_workflow_uses_trusted_publishing():
    workflow = pathlib.Path('.github/workflows/release.yml')
    assert workflow.is_file()
    workflow_text = workflow.read_text(encoding='UTF-8')
    assert 'environment: pypi' in workflow_text
    assert 'id-token: write' in workflow_text
    assert 'needs: checks' in workflow_text
    assert 'uv build --python 3.12' in workflow_text
    assert 'pypa/gh-action-pypi-publish@release/v1' in workflow_text


def test_main_noop(tmpdir):
    f = tmpdir.join('f.py')
    f.write('x = 5\n')
    assert main((f.strpath,)) == 0
    assert f.read() == 'x = 5\n'


def test_main_changes_a_file(tmpdir, capsys):
    f = tmpdir.join('f.py')
    f.write('x(\n    1\n)\n')
    assert main((f.strpath,)) == 1
    _, err = capsys.readouterr()
    assert err == f'Rewriting {f}\n'
    assert f.read() == 'x(\n    1,\n)\n'


def test_main_preserves_line_endings(tmpdir, capsys):
    f = tmpdir.join('f.py')
    f.write_binary(b'x(\r\n    1\r\n)\r\n')
    assert main((f.strpath,)) == 1
    _, err = capsys.readouterr()
    assert err == f'Rewriting {f}\n'
    assert f.read_binary() == b'x(\r\n    1,\r\n)\r\n'


def test_main_syntax_error(tmpdir):
    f = tmpdir.join('f.py')
    f.write('from __future__ import print_function\nprint 1\n')
    assert main((f.strpath,)) == 0


def test_main_non_utf8_bytes(tmpdir, capsys):
    f = tmpdir.join('f.py')
    f.write_binary('# -*- coding: cp1252 -*-\nx = €\n'.encode('cp1252'))
    assert main((f.strpath,)) == 1
    _, err = capsys.readouterr()
    assert err == f'{f} is non-utf-8 (not supported)\n'


def test_main_py27_syntaxerror_coding(tmpdir):
    f = tmpdir.join('f.py')
    f.write('# -*- coding: utf-8 -*-\n[1, 2,]\n')
    assert main((f.strpath,)) == 1
    assert f.read() == '# -*- coding: utf-8 -*-\n[1, 2]\n'


def test_main_py35_plus_py36_plus_deprecated(tmpdir, capsys):
    f = tmpdir.join('f.py')
    f.write('x(\n    *args\n)\n')
    assert main((f.strpath, '--py35-plus')) == 1
    assert f.read() == 'x(\n    *args,\n)\n'
    out, err = capsys.readouterr()
    assert err.startswith('WARNING: --py35-plus / --py36-plus do nothing')
    assert main((f.strpath, '--py36-plus')) == 0
    assert f.read() == 'x(\n    *args,\n)\n'
    out, err = capsys.readouterr()
    assert err.startswith('WARNING: --py35-plus / --py36-plus do nothing')


def test_main_py35_plus_argument_star_star_kwargs(tmpdir):
    f = tmpdir.join('f.py')
    f.write('x(\n    **args\n)\n')
    assert main((f.strpath,)) == 1
    assert f.read() == 'x(\n    **args,\n)\n'


def test_main_py36_plus_function_trailing_commas(tmpdir):
    f = tmpdir.join('f.py')
    f.write('def f(\n    **kwargs\n): pass\n')
    assert main((f.strpath,)) == 1
    assert f.read() == 'def f(\n    **kwargs,\n): pass\n'


def test_main_stdin_no_changes(capsys):
    stdin = io.TextIOWrapper(io.BytesIO(b'x = 5\n'), 'UTF-8')
    with mock.patch.object(sys, 'stdin', stdin):
        assert main(('-',)) == 0
    out, err = capsys.readouterr()
    assert out == 'x = 5\n'


def test_main_stdin_with_changes(capsys):
    stdin = io.TextIOWrapper(io.BytesIO(b'x(\n    1\n)\n'), 'UTF-8')
    with mock.patch.object(sys, 'stdin', stdin):
        assert main(('-',)) == 1
    out, err = capsys.readouterr()
    assert out == 'x(\n    1,\n)\n'


def test_main_exit_zero_even_if_changed(tmpdir):
    f = tmpdir.join('t.py')
    f.write('x(\n    1\n)')
    assert not main((str(f), '--exit-zero-even-if-changed'))
    assert f.read() == 'x(\n    1,\n)'
    assert not main((str(f), '--exit-zero-even-if-changed'))


def test_main_remove_comma(tmpdir, capsys):
    f = tmpdir.join('f.py')
    f.write('x(\n    1,\n    2,\n)\n')
    assert main((f.strpath, '--remove-comma')) == 1
    _, err = capsys.readouterr()
    assert err == f'Rewriting {f}\n'
    assert f.read() == 'x(\n    1,\n    2\n)\n'


def test_remove_main_removes_comma_without_flag(tmpdir, capsys):
    f = tmpdir.join('f.py')
    f.write('x(\n    1,\n    2,\n)\n')
    assert remove_main((f.strpath,)) == 1
    _, err = capsys.readouterr()
    assert err == f'Rewriting {f}\n'
    assert f.read() == 'x(\n    1,\n    2\n)\n'


def test_main_remove_comma_function_args(tmpdir):
    f = tmpdir.join('f.py')
    f.write('def f(\n    arg1,\n    arg2,\n): pass\n')
    assert main((f.strpath, '--remove-comma')) == 1
    assert f.read() == 'def f(\n    arg1,\n    arg2\n): pass\n'


def test_main_preserve_single_tuple_comma(tmpdir):
    f = tmpdir.join('f.py')
    f.write('single = (1,)\n\nmulti = (1, 2,)\n')
    assert main((f.strpath, '--remove-comma')) == 1
    assert f.read() == 'single = (1,)\n\nmulti = (1, 2)\n'


def test_main_remove_comma_imports(tmpdir):
    f = tmpdir.join('f.py')
    f.write('from math import (\n    sin,\n)\n')
    assert main((f.strpath, '--remove-comma')) == 1
    assert f.read() == 'from math import (\n    sin\n)\n'


def test_main_remove_comma_function_params(tmpdir):
    f = tmpdir.join('f.py')
    f.write('def func(\n    x,\n):\n    pass\n')
    assert main((f.strpath, '--remove-comma')) == 1
    assert f.read() == 'def func(\n    x\n):\n    pass\n'


def test_main_remove_comma_class_method(tmpdir):
    f = tmpdir.join('f.py')
    f.write('class C:\n    def method(\n        self,\n    ):\n        pass\n')
    assert main((f.strpath, '--remove-comma')) == 1
    assert f.read() == (
        'class C:\n    def method(\n        self\n    ):\n        pass\n'
    )


def test_main_remove_comma_function_call(tmpdir):
    f = tmpdir.join('f.py')
    f.write('result = func(\n    arg,\n)\n')
    assert main((f.strpath, '--remove-comma')) == 1
    assert f.read() == 'result = func(\n    arg\n)\n'


def test_main_multiple_constructs(tmpdir):
    f = tmpdir.join('f.py')
    f.write(
        '# Single-element tuple - should keep the comma\n'
        'single_tuple = (1,)\n\n'
        '# Import with parentheses - should remove the comma\n'
        'from math import (\n'
        '    sin,\n'
        ')\n\n'
        '# Function with single parameter - should remove the comma\n'
        'def func_single(\n'
        '    x,\n'
        '):\n'
        '    pass\n\n'
        '# Function call with single arg - should remove the comma\n'
        'result = func_single(\n'
        '    "arg",\n'
        ')\n',
    )
    assert main((f.strpath, '--remove-comma')) == 1
    assert f.read() == (
        '# Single-element tuple - should keep the comma\n'
        'single_tuple = (1,)\n\n'
        '# Import with parentheses - should remove the comma\n'
        'from math import (\n'
        '    sin\n'
        ')\n\n'
        '# Function with single parameter - should remove the comma\n'
        'def func_single(\n'
        '    x\n'
        '):\n'
        '    pass\n\n'
        '# Function call with single arg - should remove the comma\n'
        'result = func_single(\n'
        '    "arg"\n'
        ')\n'
    )
