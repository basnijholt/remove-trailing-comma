[![build status](https://github.com/basnijholt/remove-trailing-comma/actions/workflows/main.yml/badge.svg)](https://github.com/basnijholt/remove-trailing-comma/actions/workflows/main.yml)

add-trailing-comma
==================

A tool (and pre-commit hook) to automatically add trailing commas to calls and
literals.  This fork also supports removing optional trailing commas with
`--remove-comma`.

## Installation

Python 3.12 or newer is required.

```bash
pip install git+https://github.com/basnijholt/remove-trailing-comma
```

## As a pre-commit hook

See [pre-commit](https://github.com/pre-commit/pre-commit) for instructions

Sample `.pre-commit-config.yaml`:

```yaml
-   repo: https://github.com/basnijholt/remove-trailing-comma
    rev: main
    hooks:
    -   id: add-trailing-comma
```

### With the `--remove-comma` option

To remove optional trailing commas instead of adding them, use
`--remove-comma`:

```yaml
-   repo: https://github.com/basnijholt/remove-trailing-comma
    rev: main
    hooks:
    -   id: add-trailing-comma
        args: [--remove-comma]
```

From the command line:

```bash
add-trailing-comma --remove-comma path/to/file.py
```

The remove mode preserves commas that are required for Python semantics, such
as one-element tuples:

```diff
 x = (1,)
-y = [1, 2,]
+y = [1, 2]
```

## multi-line method invocation style -- why?

```python
# Sample of *ideal* syntax
function_call(
    argument,
    5 ** 5,
    kwarg=foo,
)
```

- the initial paren is at the end of the line
- each argument is indented one level further than the function name
- the last parameter (unless the call contains an unpacking
  (`*args` / `**kwargs`)) has a trailing comma

This has the following benefits:

- arbitrary indentation is avoided:

    ```python
    # I hear you like 15 space indents
    # oh your function name changed? guess you get to reindent :)
    very_long_call(arg,
                   arg,
                   arg)
    ```
- adding / removing a parameter preserves `git blame` and is a minimal diff:

    ```diff
     # with no trailing commas
     x(
    -    arg
    +    arg,
    +    arg2
     )
    ```

    ```diff
     # with trailing commas
     x(
         arg,
    +    arg2,
     )
    ```


## Implemented features

### trailing commas for function calls

```diff
 x(
     arg,
-    arg
+    arg,
 )
```

### trailing commas for tuple / list / dict / set literals

```diff
 x = [
-    1, 2, 3
+    1, 2, 3,
 ]
```

### trailing commas for function definitions

```diff
 def func(
         arg1,
-        arg2
+        arg2,
 ):
```

```diff
 async def func(
         arg1,
-        arg2
+        arg2,
 ):
```

### trailing commas for `from` imports

```diff
 from os import (
     path,
-    makedirs
+    makedirs,
 )
```

### trailing comma for class definitions

```diff
 class C(
     Base1,
-    Base2
+    Base2,
 ):
     pass
```

### trailing comma for with statement

```diff
 with (
         open('f1', 'r') as f1,
-        open('f2', 'w') as f2
+        open('f2', 'w') as f2,
 ):
     pass
```

### trailing comma for match statement

```diff
 match x:
     case A(
        1,
-       2
+       2,
     ):
        pass
     case (
        1,
-       2
+       2,
     ):
        pass
     case [
        1,
-       2
+       2,
     ]:
        pass
     case {
        'x': 1,
-       'y': 2
+       'y': 2,
     }:
        pass
```


### trailing comma for PEP-695 type aliases

```diff
 def f[
-    T
+    T,
 ](x: T) -> T:
     return x
```

```diff
 class A[
-    K
+    K,
 ]:
     def __init__(self, x: T) -> None:
         self.x = x
```

```diff
 type ListOrSet[
-     T
+     T,
] = list[T] | set[T]
```

### unhug trailing paren

```diff
 x(
     arg1,
-    arg2)
+    arg2,
+)
```

### unhug leading paren

```diff
-function_name(arg1,
-              arg2)
+function_name(
+    arg1,
+    arg2,
+)
```

### match closing brace indentation

```diff
 x = [
     1,
     2,
     3,
-    ]
+]
```

### remove unnecessary commas

yes yes, I realize the tool is called `add-trailing-comma` :laughing:

```diff
-[1, 2, 3,]
-[1, 2, 3, ]
+[1, 2, 3]
+[1, 2, 3]
```

## Development

This project uses [uv](https://docs.astral.sh/uv/) for dependency management
and CI.

```bash
uv sync --dev
uv run coverage run -m pytest tests
uv run coverage report
uv run pre-commit run --all-files
```
