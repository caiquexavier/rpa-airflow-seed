# Robot Framework Project Structure

This document describes the organization and layering of the Robot Framework project.

## Folder Structure

### `robot/tests/`
High-level test suites organized by business domain. Each domain has its own folder containing:
- Main test file (e.g., `protocolo_devolucao_main.robot`)
- Edge case tests (optional, e.g., `protocolo_devolucao_edge_cases.robot`)

**Example:**
```
robot/tests/protocolo_devolucao/
  protocolo_devolucao_main.robot
  protocolo_devolucao_edge_cases.robot
```

### `robot/resources/infra/`
Low-level technical keywords for infrastructure operations:
- **browser_keywords.robot**: Browser automation (start, close, navigation)
- **http_keywords.robot**: HTTP requests and API interactions
- **filesystem_keywords.robot**: File and directory operations
- **ui_keywords.robot**: Generic UI interactions (wait, click, input)
- **windows_keywords.robot**: Windows-specific operations

These keywords are reusable across all domains and should not contain business logic.

### `robot/resources/saga/`
Saga/CQRS orchestration keywords:
- **saga_context_keywords.robot**: Context initialization and variable access
  - `Initialize Saga Context From Arguments`
  - `Get Saga Exec Id`
  - `Get Saga Rpa Key Id`
  - `Get Saga Step Id`
- **saga_lifecycle_keywords.robot**: Saga lifecycle management
  - `Saga Start Step`
  - `Saga Mark Step Success`
  - `Saga Mark Step Fail With Message`
  - `Saga Finish Execution Success`
  - `Saga Finish Execution Fail`

These keywords wrap Python library calls in `robot/libs/saga_client.py`.

### `robot/resources/domain/`
Domain-specific business keywords organized by process:
- **protocolo_devolucao_keywords.robot**: Protocolo de devolução business flows (e-Cargo pod download)
- **job_002_keywords.robot**: Other process keywords (example)

Domain keywords should:
- Compose infra-layer keywords
- Wrap saga lifecycle calls where appropriate
- Represent business meaning, not low-level technical operations

### `robot/libs/`
Python libraries with pure functions (no side effects beyond HTTP/logging):
- **saga_client.py**: Saga lifecycle API calls
- **rpa_api_client.py**: Generic RPA API interactions
- **parsing_utils.py**: JSON/string parsing and transformation
- **loop_detector.py**: Loop detection and tracking utilities

All functions should be:
- Pure (input → output, no global state)
- Small and focused
- Well-documented

### `robot/variables/`
Variable files for different environments:
- **env_dev.robot**: Development environment variables
- **env_prod.robot**: Production environment variables
- **saga_defaults.robot**: Default saga-related variables

## Layering Principles

1. **Tests** → Use domain keywords
2. **Domain keywords** → Compose infra keywords + saga lifecycle
3. **Infra keywords** → Use Robot Framework libraries directly
4. **Saga keywords** → Call Python libraries in `robot/libs/`
5. **Python libs** → Pure functions, HTTP calls, no Robot Framework dependencies

## Adding a New Process/Domain

1. Create test file in `robot/tests/`:
   ```
   robot/tests/my_new_process_main.robot
   ```

   Example: `robot/tests/protocolo_devolucao_main.robot`

2. Create domain keywords file:
   ```
   robot/resources/domain/my_new_process_keywords.robot
   ```

3. In the test file, import:
   ```robot
   Resource    ${CURDIR}/../../resources/infra/browser_keywords.robot
   Resource    ${CURDIR}/../../resources/domain/my_new_process_keywords.robot
   Resource    ${CURDIR}/../../resources/saga/saga_context_keywords.robot
   ```

4. In domain keywords, import infra keywords as needed:
   ```robot
   Resource    ${CURDIR}/../infra/ui_keywords.robot
   Resource    ${CURDIR}/../infra/filesystem_keywords.robot
   ```

5. Use saga lifecycle keywords when needed:
   ```robot
   Resource    ${CURDIR}/../saga/saga_lifecycle_keywords.robot
   
   # In your keyword:
   Saga Start Step    Process Documents
   # ... do work ...
   Saga Mark Step Success    Process Documents
   ```

## Best Practices

- **DRY**: Extract reusable keywords to avoid duplication
- **Single Responsibility**: Each keyword should do one thing
- **Abstraction Levels**: Keep keywords at consistent abstraction levels
- **Pure Functions**: Python libs should be pure (no hidden dependencies)
- **Documentation**: Document all keywords with `[Documentation]`

