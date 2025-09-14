# tests/test_smoke.py
import duckdb
import pytest
from pathlib import Path

from pints import PintsDB, get_sql_path


def test_sql_files_packaged():
    # Ensure vendored SQL files are available in the installed package
    core = Path(get_sql_path("pints_core_v1.sql"))
    seed = Path(get_sql_path("pints_core_seed_v1.sql"))
    assert core.exists() and core.stat().st_size > 0
    assert seed.exists() and seed.stat().st_size > 0


def test_init_seed_and_basic_queries(tmp_path: Path):
    db_path = tmp_path / "pints_test.duckdb"
    db = PintsDB(db_path)

    # 1) init + seed should run without errors
    db.init_schema()
    db.seed_minimal_vocab()

    # 2) tables should exist
    con = duckdb.connect(str(db_path))
    tables = set(con.execute("SHOW TABLES").fetchdf()["name"].str.lower())
    must_have = {
        "schema_info",
        "vocabulary_info",
        "ontology_sources",
        "ontology_terms",
        "units",
        "field_dictionary",
        "samples",
        "runs",
        "features",
        "v_field_semantics",
    }
    assert must_have.issubset(tables)

    # 3) seed should have populated minimal ontology + units + dictionary
    n_terms = con.execute("SELECT COUNT(*) FROM ontology_terms").fetchone()[0]
    n_units = con.execute("SELECT COUNT(*) FROM units").fetchone()[0]
    n_dict  = con.execute("SELECT COUNT(*) FROM field_dictionary").fetchone()[0]
    assert n_terms >= 3
    assert n_units >= 3
    assert n_dict  >= 3

    # 4) insert minimal sample/run/feature via API
    db.add_sample("S001", "Sample", "Smoke test sample")
    db.add_run("R001", "S001", "2025-09-12 09:00:00", "QTOF-XYZ", "POS_5min", "B01")
    db.add_feature("R001_F0001", "R001", mz=301.123456, rt=312.4, area=154321.2)

    # 5) verify inserts
    n_samples = con.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
    n_runs    = con.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    n_feats   = con.execute("SELECT COUNT(*) FROM features").fetchone()[0]
    assert n_samples >= 1
    assert n_runs    >= 1
    assert n_feats   >= 1

    # 6) semantic view should resolve unit_uri join without error
    df_sem = con.execute("SELECT * FROM v_field_semantics ORDER BY field_name").fetchdf()
    assert {"field_name", "ontology_uri", "unit_code", "unit_uri"}.issubset(df_sem.columns)

    con.close()
