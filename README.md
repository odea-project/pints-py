# PINTS-Py

Python wrapper for PINTS (Pipelines for Non-Target Screening).
This package provides Python APIs and a command-line interface (CLI) to manage and query PINTS databases based on the pints-core-sql schema.

## Features
- Initialize and seed a DuckDB with the PINTS Core schema
- Add samples, runs, and features programmatically
- Export tables to CSV for downstream analysis
- Query using either the Python API or the CLI (pints ...)
- Reuses the universal SQL definitions from pints-core-sql

## Installation
Clone and install in editable mode:
```bash
git clone https://github.com/odea-project/pints-py.git
cd pints-py
python -m venv .venv                # For virtual environment
.venv/Scripts/Activate.ps1          # For virtual environment on Windows PowerShell
pip install -e .
```

This will also fetch the pints-core-sql submodule.

## Quick Start
### Using Python CLI
Initialize a new PINTS feature list:
```bash
pints init --db myFeatures.duckdb
```

Seed the feature list with the core schema:
```bash
pints seed --db myFeatures.duckdb
``` 

Add a sample:
```bash
pints add-sample --db myFeatures.duckdb --id S001 --type Sample --desc "River water"
```

Add a run linked to the sample:
```bash
pints add-run --db myFeatures.duckdb --id R001 --sample S001 --time "2025-09-12 09:00:00" --instrument QTOF-XYZ --method POS_5min --batch B01
```

Add a feature linked to the run:
```bash
pints add-feature --db myFeatures.duckdb --id R001_F0001 --run R001 --mz 301.123456 --rt 312.4 --area 154321.2
```

Export the features table to CSV:
```bash
pints export features --db myFeatures.duckdb --out features.csv
```

Check schema and vocabulary versions:
```bash
pints show-version --db myFeatures.duckdb
```

List all tables in the database:
```bash
pints list-tables --db myFeatures.duckdb
```

#### Using Plugins
The CLI supports plugins for extended functionality from pints-plugins (e.g., intra_run_components).
To use plugins, install them in the same environment:
```bash
pints plugin install --db myFeatures.duckdb --name intra_run_components
```

Add data using plugin commands:
```bash
pints plugin insert --db myFeatures.duckdb --name intra_run_components --rows "R001,R001_F0001,C001" "R001,R001_F0002,C001" --materialize
``` 

Export plugin tables:
```bash
pints plugin export --db my.duckdb --name intra_run_components --out intra.csv
```

## Development
This repo depends on pints-core-sql as a Git submodule.
After cloning, make sure to initialize submodules:
```bash
git submodule update --init --recursive
```

The SQL files from pints-core-sql/sql are synced into pints/sql before packaging.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.