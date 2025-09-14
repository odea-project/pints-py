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
Initialize a new PINTS database:
```bash
pints init --db pints.duckdb
```
Seed the database with the core schema:
```bash
pints seed --db pints.duckdb
``` 

Add a sample:
```bash
pints add-sample --db pints.duckdb --id S001 --type Sample --desc "River water"
```

Add a run linked to the sample:
```bash
pints add-run --db pints.duckdb --id R001 --sample S001 --time "2025-09-12 09:00:00" --instrument QTOF-XYZ --method POS_5min --batch B01
```

Add a feature linked to the run:
```bash
pints add-feature --db pints.duckdb --id R001_F0001 --run R001 --mz 301.123456 --rt 312.4 --area 154321.2
```

Export the features table to CSV:
```bash 
pints export features --db pints.duckdb --out features.csv
```

Check schema and vocabulary versions:
```bash 
pints show-version --db pints.duckdb
```

List all tables in the database:
```bash
pints list-tables --db pints.duckdb
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