# Integration Tests

This directory contains the integration test cases.

## Directory Layout

```
ci/
├── README.md                                 # This file
├── allowed-license.lst                       # Allowlist used by the license check workflow
├── arriveby-ondemand-scheduled-case/         # Test case
├── ondemand-oneway-generator-commuter-case/  # Test case
└── scheduled-routedeviation-historical/      # Test case
```

## How It Works

Each test case is built around the following three files.

| File                         | Purpose                                                                                                     |
|------------------------------|-------------------------------------------------------------------------------------------------------------|
| `compose.yaml`               | Defines the Docker Compose stack required for the test, such as simulators, planners, and the broker.       |
| `pyproject.toml` / `uv.lock` | Declare and lock the Python dependencies for the test script.                                               |
| `requirements.txt`           | Retained for compatibility with the previous pip-based workflow.                                            |
| `run_integration_test.py`    | The actual test runner. It calls the containers' HTTP APIs, runs the simulation, and validates the results. |

### Execution with GitHub Actions

`.github/workflows/integration.yaml` runs automatically on pushes and pull requests targeting the `main` branch.

```
┌──────────────┐         ┌──────────────────────────────────────────────────────┐
│  set-matrix  │──────▶  │  integration-test (matrix)                           │
│              │         │                                                      │
│ Automatically│         │  Runs each test case directory in parallel:          │
│ discovers    │         │    1. `docker compose up -d`                         │
│ test cases   │         │    2. `uv sync --frozen`                             │
│ under ci/    │         │    3. `uv run --no-sync python run_integration_test.py` │
└──────────────┘         └──────────────────────────────────────────────────────┘
```

The `set-matrix` job dynamically discovers directories under `ci/` that contain `run_integration_test.py`, so you do not need to modify the workflow file when adding a new test case.

### Running a Test Locally

```bash
# Move to a test case directory
cd ci/ondemand-oneway-generator-commuter-case

# Start the containers
docker compose up -d

# Install locked Python dependencies
uv sync --frozen

# Run the integration test
uv run --no-sync python run_integration_test.py
```
