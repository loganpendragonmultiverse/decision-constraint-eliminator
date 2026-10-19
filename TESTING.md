# Testing

Requires Python 3.10 or newer. Use an isolated environment:

```sh
python -m pip install -e ".[dev]"
ruff format --check .
ruff check .
pytest
python -m build
```

Retain the existing 90% branch-aware coverage floor. CI covers Python 3.10 and 3.14 on Linux, Windows and macOS. Tests use only synthetic text and private temporary files; no policies, decisions or credentials need to be supplied.

## 1.2.1 acceptance

Exercise all eight operators, finite numeric values, malformed requirement shapes, each missing-field policy, complete matrices and original/hypothetical omission results. Preserve input bytes and unranked outcomes. Review authored HTML, punctuation and line breaks as literal evidence.

Exercise existing/source/dangling/racing destinations, ordinary write failures, complete Unicode stdout and a real consumer-closed pipe. Expect status 2 without a traceback for input/output failures. A failed new write may leave a partial report; tests must preserve every pre-existing file. Run the full configured checks and inspect wheel/source package documents and examples.
