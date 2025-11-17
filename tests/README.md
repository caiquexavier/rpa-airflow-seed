# Test Suite for rpa-airflow-seed

This directory contains the comprehensive unit test suite for the rpa-airflow-seed project.

## Structure

The test directory mirrors the project structure:

```
tests/
├── rpa_api/              # Tests for rpa-api service
│   ├── domain/           # Domain entity tests
│   ├── application/      # Use case tests
│   ├── infrastructure/   # Repository and adapter tests
│   └── presentation/     # Controller tests
├── rpa_listener/         # Tests for rpa-listener service
│   └── services/         # Service tests
├── airflow/              # Tests for airflow services
│   └── services/         # Service tests
├── conftest.py           # Shared fixtures
├── pytest.ini            # Pytest configuration
├── .coveragerc           # Coverage configuration
├── requirements.txt      # Test dependencies
├── run-tests.ps1         # PowerShell script (Windows)
└── run-tests.bat         # Batch script (Windows)
```

## Setup

### Windows (PowerShell)
```powershell
# Install test dependencies (run this first!)
.\tests\run-tests.ps1 install

# Or using batch file
tests\run-tests.bat install
```

**Note:** If you get an error that `pytest` is not recognized, make sure you've run the install command first. The scripts use `python -m pytest` which is more reliable than calling `pytest` directly.

### Windows (Command Prompt)
```cmd
tests\run-tests.bat install
```

### Linux/Mac (Make)
```bash
make install-test-deps
```

Or manually:
```bash
pip install -r tests/requirements.txt
```

## Running Tests

### Windows (PowerShell)
```powershell
# Run all tests
.\tests\run-tests.ps1 all
# or
.\tests\run-tests.ps1

# Run only unit tests
.\tests\run-tests.ps1 unit

# Run tests with coverage
.\tests\run-tests.ps1 cov

# Generate HTML coverage report
.\tests\run-tests.ps1 html
```

### Windows (Command Prompt)
```cmd
# Run all tests
tests\run-tests.bat

# Run only unit tests
tests\run-tests.bat unit

# Run tests with coverage
tests\run-tests.bat cov

# Generate HTML coverage report
tests\run-tests.bat html
```

### Linux/Mac (Make)
```bash
# Run all tests
make test

# Run only unit tests
make test-unit

# Run tests with coverage
make test-cov

# Generate HTML coverage report
make test-html
```

### Direct Python Commands (All Platforms)
```bash
# Set Python path (Windows PowerShell)
$env:PYTHONPATH = ".;rpa-api/src;rpa-listener/src;airflow/src"

# Set Python path (Windows CMD)
set PYTHONPATH=.;rpa-api/src;rpa-listener/src;airflow/src

# Set Python path (Linux/Mac)
export PYTHONPATH=.:rpa-api/src:rpa-listener/src:airflow/src

# Then run pytest
pytest tests -v                    # All tests
pytest tests -v -m unit            # Unit tests only
pytest tests --cov --cov-report=term-missing  # With coverage
pytest tests --cov --cov-report=html          # HTML coverage report
```

The HTML report will be available at `htmlcov/index.html`.

## Test Principles

### Clean Code
- Tests are organized by feature/domain
- Each test class focuses on a single unit
- Test names are descriptive and follow the pattern: `test_<what>_<condition>_<expected_result>`

### Functional Programming
- Use cases are tested as pure functions
- Dependencies are injected via function parameters
- No side effects in test functions
- Immutable data structures where possible

### Coverage Goals
- Minimum coverage: 70%
- Focus on business logic and domain entities
- Infrastructure adapters are mocked
- External services (database, RabbitMQ, S3) are not tested directly

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- Domain entities and value objects
- Use cases (business logic)
- Pure functions and utilities

### Integration Tests (`@pytest.mark.integration`)
- Repository implementations (with test database)
- End-to-end flows (when needed)

## Writing New Tests

1. **Follow the structure**: Place tests in the corresponding directory matching the source code structure.

2. **Use fixtures**: Leverage shared fixtures from `conftest.py` to avoid duplication.

3. **Mock external dependencies**: Use `unittest.mock` or `pytest-mock` to mock:
   - Database connections
   - HTTP requests
   - File system operations
   - External APIs

4. **Test naming**: Use descriptive names:
   ```python
   def test_create_execution_success(self):
       """Test successful execution creation."""
   ```

5. **Arrange-Act-Assert**: Structure tests clearly:
   ```python
   def test_example(self):
       # Arrange
       command = CreateExecutionCommand(...)
       
       # Act
       result = create_execution(...)
       
       # Assert
       assert result.exec_id > 0
   ```

## Coverage Reports

Coverage reports are generated in multiple formats:
- **Terminal**: Shows missing lines inline
- **HTML**: Interactive report in `htmlcov/`
- **XML**: For CI/CD integration in `coverage.xml`

## Continuous Integration

Tests should be run in CI/CD pipelines:
```bash
# Windows PowerShell
$env:PYTHONPATH = ".;rpa-api/src;rpa-listener/src;airflow/src"
pytest tests --cov --cov-report=xml --cov-fail-under=70

# Linux/Mac
export PYTHONPATH=.:rpa-api/src:rpa-listener/src:airflow/src
pytest tests --cov --cov-report=xml --cov-fail-under=70
```

## Troubleshooting

### Import Errors
If you encounter import errors, ensure the Python path includes the source directories:

**Windows PowerShell:**
```powershell
$env:PYTHONPATH = ".;rpa-api/src;rpa-listener/src;airflow/src"
```

**Windows CMD:**
```cmd
set PYTHONPATH=.;rpa-api/src;rpa-listener/src;airflow/src
```

**Linux/Mac:**
```bash
export PYTHONPATH=.:rpa-api/src:rpa-listener/src:airflow/src
```

### Missing Dependencies
Install all test dependencies:
```bash
pip install -r tests/requirements.txt
```

### Database Tests
Database tests use mocks by default. For integration tests, set up a test database and configure connection strings in test configuration.
