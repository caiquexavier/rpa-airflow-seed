# Testing Guide for RPA API

This document provides comprehensive information about testing the RPA API project.

## Test Structure

The test structure mirrors the source code structure:

```
tests/
├── __init__.py
├── config/
│   ├── __init__.py
│   └── test_config.py
├── controllers/
│   ├── __init__.py
│   ├── test_executions_controller.py
│   └── test_request_controller.py
├── libs/
│   ├── __init__.py
│   └── test_postgres.py
├── services/
│   ├── __init__.py
│   ├── test_executions_service.py
│   └── test_rabbitmq_service.py
├── validations/
│   ├── __init__.py
│   ├── test_errors.py
│   ├── test_executions_models.py
│   └── test_request_models.py
├── test_executions_models.py
├── test_executions_service.py
└── test_integration.py
```

## Test Categories

### Unit Tests
- **Location**: Individual test files in respective modules
- **Purpose**: Test individual functions and classes in isolation
- **Markers**: `@pytest.mark.unit`
- **Coverage**: High coverage of business logic

### Integration Tests
- **Location**: `test_integration.py`
- **Purpose**: Test API endpoints and service interactions
- **Markers**: `@pytest.mark.integration`
- **Coverage**: End-to-end workflows

## Running Tests

### Prerequisites

1. Install test dependencies:
```bash
pip install -r requirements-test.txt
```

2. Set environment variables:
```bash
export PYTHONPATH=src
```

### Basic Commands

#### Run All Tests
```bash
pytest
```

#### Run with Coverage
```bash
pytest --cov=src --cov-report=term-missing
```

#### Run Specific Test Categories
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration
```

#### Run Specific Test Files
```bash
# Run specific test file
pytest tests/controllers/test_executions_controller.py

# Run specific test class
pytest tests/controllers/test_executions_controller.py::TestHandleRequestRpaExec

# Run specific test method
pytest tests/controllers/test_executions_controller.py::TestHandleRequestRpaExec::test_successful_request
```

### Using Make Commands

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Run with coverage report
make test-coverage

# Generate HTML test report
make test-html

# Run tests in parallel
make test-parallel

# Clean test artifacts
make clean
```

### Using Scripts

#### PowerShell (Windows)
```powershell
# Run all tests
.\scripts\run-tests.ps1

# Run unit tests with coverage
.\scripts\run-tests.ps1 -TestType unit -CoverageThreshold 85

# Generate HTML reports
.\scripts\run-tests.ps1 -GenerateReport -Verbose
```

#### Bash (Linux/Mac)
```bash
# Run all tests
./scripts/run-tests.sh

# Run unit tests with coverage
./scripts/run-tests.sh -t unit -c 85

# Generate HTML reports
./scripts/run-tests.sh -r -v
```

## Coverage Reporting

### Terminal Coverage
```bash
pytest --cov=src --cov-report=term-missing
```

### HTML Coverage Report
```bash
pytest --cov=src --cov-report=html:htmlcov
```
Open `htmlcov/index.html` in your browser to view detailed coverage.

### XML Coverage Report
```bash
pytest --cov=src --cov-report=xml:coverage.xml
```

### Coverage Badge
```bash
coverage run -m pytest
coverage-badge -o coverage.svg
```

## Test Configuration

### pytest.ini
- Test discovery patterns
- Coverage settings
- Markers definition
- Coverage threshold: 80%

### conftest.py
- Shared fixtures
- Test configuration
- Mock objects

## Test Data and Fixtures

### Common Fixtures
- `mock_db_connection`: Mock database connection
- `mock_rabbitmq_connection`: Mock RabbitMQ connection
- `sample_execution_payload`: Sample execution data
- `sample_execution_record`: Sample database record

### Test Data
- Use factories for complex test data
- Mock external dependencies
- Use realistic but minimal test data

## Writing Tests

### Test Naming Convention
- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

### Test Structure
```python
class TestClassName:
    """Test class description."""
    
    def test_method_name(self):
        """Test method description."""
        # Arrange
        # Act
        # Assert
```

### Best Practices
1. **Arrange-Act-Assert**: Structure tests clearly
2. **One assertion per test**: Keep tests focused
3. **Descriptive names**: Make test purpose clear
4. **Mock external dependencies**: Isolate units under test
5. **Test edge cases**: Cover error conditions
6. **Use fixtures**: Share common test data

## Mocking Guidelines

### Database Operations
```python
@patch('src.libs.postgres.execute_insert')
def test_function(mock_execute_insert):
    mock_execute_insert.return_value = 123
    # Test code
```

### RabbitMQ Operations
```python
@patch('src.services.rabbitmq_service.publish_execution_message')
def test_function(mock_publish):
    mock_publish.return_value = True
    # Test code
```

### Configuration
```python
@patch.dict('os.environ', {'RABBITMQ_HOST': 'test-host'})
def test_function():
    # Test code
```

## Continuous Integration

### GitHub Actions Example
```yaml
- name: Run Tests
  run: |
    pip install -r requirements-test.txt
    pytest --cov=src --cov-report=xml --cov-fail-under=80
```

### Coverage Threshold
- Minimum coverage: 80%
- Fails build if coverage below threshold
- Encourages comprehensive testing

## Debugging Tests

### Verbose Output
```bash
pytest -v -s
```

### Debug Specific Test
```bash
pytest -v -s tests/controllers/test_executions_controller.py::TestHandleRequestRpaExec::test_successful_request
```

### PDB Debugger
```bash
pytest --pdb
```

## Performance Testing

### Parallel Execution
```bash
pytest -n auto
```

### Slow Test Marking
```python
@pytest.mark.slow
def test_slow_operation():
    # Long-running test
```

## Test Reports

### HTML Test Report
```bash
pytest --html=reports/test-report.html --self-contained-html
```

### JUnit XML Report
```bash
pytest --junitxml=reports/junit.xml
```

## Maintenance

### Regular Tasks
1. Update test dependencies
2. Review coverage reports
3. Refactor duplicate test code
4. Add tests for new features
5. Remove obsolete tests

### Test Quality Metrics
- Coverage percentage
- Test execution time
- Test reliability
- Code maintainability

## Troubleshooting

### Common Issues
1. **Import errors**: Check PYTHONPATH
2. **Mock not working**: Verify patch target
3. **Database errors**: Use proper mocking
4. **Async test issues**: Use pytest-asyncio

### Getting Help
- Check pytest documentation
- Review test examples in the codebase
- Use debug mode for complex issues
