# /test

Run the test suite with coverage and report results.

## Steps

1. Run full test suite:
```bash
poetry run pytest --cov=workflow_core --cov-report=term-missing --maxfail=5
```

2. If tests fail, report:
   - Which test failed
   - The assertion error
   - Whether it is a regression or a new failure

3. Check coverage per module. Flag any module below 85%.

4. Run quality checks:
```bash
ruff check .
mypy workflow_core/
```

5. Report summary:
   - Total tests: passed / failed / skipped
   - Coverage: overall % and any modules below threshold
   - Lint/type errors if any

## Flags

- `/test core` — run only `tests/core/`
- `/test nodes` — run only `tests/nodes/`
- `/test adapters` — run only `tests/adapters/`
- `/test watch` — run with `-f` (fail-fast, re-run on change)
