"""
PINTS-Py
--------

Python wrapper for PINTS (Pipelines for Non-Target Screening).

This package provides a thin API around the PINTS Core-SQL schema.
It allows initializing, seeding, and extending DuckDB databases that
conform to the PINTS standard.
"""

from importlib.resources import files

__all__ = ["__version__", "get_sql_path"]

# Current package version (keep in sync with pyproject.toml)
__version__ = "0.1.0"


def get_sql_path(filename: str) -> str:
    """
    Return the path to a bundled SQL file from the core schema.

    Parameters
    ----------
    filename : str
        e.g. "pints_core_v1.sql", "pints_core_seed_v1.sql"

    Returns
    -------
    str
        Path to the SQL file inside the installed package.
    """
    return str(files("pints.sql").joinpath(filename))
