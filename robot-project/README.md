## Robot Framework Minimal Project

Prerequisites

- Windows 11
- Python 3.10+ on PATH (`python --version`)

Setup

1. Create virtual environment
   - `python -m venv venv`
   - Optional activation (if available on your system):
     - PowerShell: `.\venv\Scripts\Activate.ps1`
     - CMD: `.\venv\Scripts\activate.bat`
2. Install dependencies
   - If activated: `pip install -r requirements.txt`
   - Without activation: `.\venv\Scripts\pip.exe install -r requirements.txt`

Run Tests

- From the project root (`robot-project/`), choose one of:
  - Using the venv executable (no activation required):
    - `.\venv\Scripts\robot.exe -d results tests`
  - Using Python module form (also works without activation):
    - `.\venv\Scripts\python.exe -m robot -d results tests`
  - If your PATH is set and venv is activated:
    - `robot -d results tests`

Browser (RF Browser) first-time setup:
- After installing requirements into a fresh venv, run once:
  - `.\venv\Scripts\rfbrowser.exe init`

Project Structure

- `tests/` — test suites
- `resources/` — reusable keywords
- `variables/` — shared variables (Python)
- `results/` — output: `report.html`, `log.html`, `output.xml`

