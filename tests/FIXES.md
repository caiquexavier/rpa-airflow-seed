# Test Import Fixes

## Issue
The source code uses relative imports (e.g., `from ...domain.entities.execution`), which requires a proper package structure.

## Solution
1. Updated `conftest.py` to add parent directories (`rpa-api`, `rpa-listener`, `airflow`) to Python path instead of `src` subdirectories
2. Updated all test imports to use `src.` prefix (e.g., `from src.domain.entities.execution`)
3. Updated all patch decorators to use `src.` prefix
4. Updated `run-tests.ps1` and `run-tests.bat` to set PYTHONPATH correctly

## Remaining Issue
The `create_execution` use case imports `get_saga_by_exec_id` inside the function. To patch it, you need to patch it in the repository module before calling the function:

```python
with patch('src.infrastructure.repositories.saga_repository.get_saga_by_exec_id', return_value=None):
    # call function
```

However, if this doesn't work because the import happens inside the function, you may need to refactor the test to mock at a different level or refactor the source code to import at module level.

