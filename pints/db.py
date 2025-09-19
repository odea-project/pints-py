# pints/db.py
"""
PINTS-Py core DB API

Thin Python wrapper around a DuckDB database that follows the
PINTS Core SQL schema (from pints-core-sql).

Features:
- init_schema(): create core tables/views (idempotent)
- seed_minimal_vocab(): insert PSI-MS/UO dictionary entries (+ tiny demo)
- add_sample(), add_run(), add_feature(): convenience upserts
- export_table(): export any table/view to CSV
- fetch_df(): run a SELECT and return a pandas DataFrame

The SQL files are expected to be vendored into pints/sql/
(e.g., via a sync script from the pints-core-sql repo).
"""

from __future__ import annotations

from pathlib import Path
from importlib.resources import files
from typing import Optional, Any, Dict, Iterable
import yaml
import duckdb


def _load_sql(name: str) -> str:
    """
    Load a .sql file bundled under pints/sql/.
    Example names: 'pints_core_v1.sql', 'pints_core_seed_v1.sql'
    """
    return files("pints").joinpath("sql", name).read_text(encoding="utf-8")


class PintsDB:
    """
    High-level API for interacting with a PINTS DuckDB database.

    Example:
        db = PintsDB("pints.duckdb")
        db.init_schema()
        db.seed_minimal_vocab()
        db.add_sample("S001", "Sample", "River water")
        db.add_run("R001", "S001", "2025-09-12 09:00:00", "QTOF-XYZ", "POS_5min", "B01")
        db.add_feature("R001_F0001", "R001", mz=301.123456, rt=312.4, area=154321.2)
    """

    def __init__(self, db_path: str | Path = "pints.duckdb"):
        self.db_path = Path(db_path)

    # ---------------- internal ----------------
    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.db_path))

    # ---------------- schema & seed ----------------
    def init_schema(self) -> None:
        """Create the PINTS core schema (idempotent)."""
        con = self._connect()
        con.execute(_load_sql("core/pints_core_v1.sql"))
        con.close()

    def seed_minimal_vocab(self) -> None:
        """Insert minimal PSI-MS and UO mappings + tiny demo rows."""
        con = self._connect()
        con.execute(_load_sql("seeds/pints_core_seed_v1.sql"))
        con.close()

    # ---------------- inserts (upserts) ----------------
    def add_sample(self, sample_id: str, sample_type: str | None = None, description: str | None = None) -> None:
        con = self._connect()
        con.execute(
            "INSERT OR REPLACE INTO samples (sample_id, sample_type, description) VALUES (?,?,?)",
            [sample_id, sample_type, description],
        )
        con.close()

    def add_run(
        self,
        run_id: str,
        sample_id: str,
        acq_time_utc: str | None = None,
        instrument: str | None = None,
        method_id: str | None = None,
        batch_id: str | None = None,
    ) -> None:
        con = self._connect()
        con.execute(
            """
            INSERT OR REPLACE INTO runs
              (run_id, sample_id, acq_time_utc, instrument, method_id, batch_id)
            VALUES (?,?,?,?,?,?)
            """,
            [run_id, sample_id, acq_time_utc, instrument, method_id, batch_id],
        )
        con.close()

    def add_feature(self, feature_id: str, run_id: str, sample_id: str, mz: float, rt: float | None = None, area: float | None = None) -> None:
        con = self._connect()
        con.execute(
            """
            INSERT OR REPLACE INTO features
              (feature_id, run_id, sample_id, mz, rt, area)
            VALUES (?,?,?,?,?,?)
            """,
            [feature_id, run_id, sample_id, mz, rt, area],
        )
        con.close()

    # ---------------- exports & queries ----------------
    def export_table(self, table: str, csv_path: str, header: bool = True) -> None:
        """
        Export a table or view to CSV using DuckDB COPY.
        """
        con = self._connect()
        # COPY requires a string literal for the path → quote safely
        path_lit = "'" + str(csv_path).replace("'", "''") + "'"
        header_clause = "HEADER" if header else "HEADER FALSE"
        con.execute(f"COPY (SELECT * FROM {table}) TO {path_lit} (DELIMITER ',', {header_clause});")
        con.close()

    def fetch_df(self, sql: str):
        """Run a SELECT query and return a pandas DataFrame."""
        con = self._connect()
        df = con.execute(sql).fetchdf()
        con.close()
        return df

    def get_table_df(self, table: str):
        """Convenience: SELECT * FROM <table> as pandas DataFrame."""
        con = self._connect()
        df = con.execute(f"SELECT * FROM {table}").fetchdf()
        con.close()
        return df

    # ---------------- lookups ----------------
    def get_feature(self, feature_id: str) -> Optional[Dict[str, Any]]:
        con = self._connect()
        df = con.execute("SELECT * FROM features WHERE feature_id = ?", [feature_id]).fetchdf()
        con.close()
        return None if df.empty else df.iloc[0].to_dict()
    
    # ---------------- plugin/migration support ----------------
    def migrate(self, sql_file: str | Path) -> None:
        """Apply a migration or plugin SQL file (idempotent encouraged)."""
        sql = Path(sql_file).read_text(encoding="utf-8")
        con = self._connect()
        con.execute(sql)
        con.close()

    def run_sql(self, sql: str, params: Optional[Iterable[Any]] = None):
        """Execute arbitrary SQL (useful for plugins). Returns pandas DataFrame for SELECTs."""
        con = self._connect()
        try:
            if params is None:
                res = con.execute(sql)
            else:
                res = con.execute(sql, list(params))
            try:
                df = res.fetchdf()
                return df
            except duckdb.Error:
                return None
        finally:
            con.close()

    # ---------------- generic algo properties (optional plugin table) ----------------
    def set_algo_property(self, level: str, entity_id: str, key: str,
                          value: float | None = None, value_text: str | None = None,
                          unit_code: str | None = None, ontology_uri: str | None = None) -> None:
        """Upsert an algorithm-specific property (creates table if missing)."""
        con = self._connect()
        con.execute("""
            CREATE TABLE IF NOT EXISTS algo_properties (
              level TEXT NOT NULL,
              entity_id TEXT NOT NULL,
              prop_key TEXT NOT NULL,
              prop_value DOUBLE,
              value_text TEXT,
              unit_code TEXT,
              ontology_uri TEXT,
              PRIMARY KEY (level, entity_id, prop_key)
            );
        """)
        con.execute("""
            INSERT OR REPLACE INTO algo_properties
              (level, entity_id, prop_key, prop_value, value_text, unit_code, ontology_uri)
            VALUES (?,?,?,?,?,?,?)
        """, [level, entity_id, key, value, value_text, unit_code, ontology_uri])
        con.close()

    def get_algo_properties(self, level: str, entity_id: str):
        """Return a DataFrame of algo-specific properties for the given entity (or None if table absent)."""
        con = self._connect()
        try:
            df = con.execute("""
                SELECT prop_key, prop_value, value_text, unit_code, ontology_uri
                FROM algo_properties
                WHERE level = ? AND entity_id = ?
                ORDER BY prop_key
            """, [level, entity_id]).fetchdf()
        except duckdb.Error:
            df = None
        con.close()
        return df

    # ---------------- exports ----------------
    def export_sql(self, select_sql: str, csv_path: str, header: bool = True, params: Optional[Iterable[Any]] = None):
        """Export the result of a SELECT to CSV (supports bound params)."""
        # Remove trailing semicolon to avoid DuckDB COPY syntax error
        select_sql = select_sql.rstrip().rstrip(';')
        con = self._connect()
        path_lit = "'" + str(csv_path).replace("'", "''") + "'"
        header_clause = "HEADER" if header else "HEADER FALSE"
        if params:
            con.execute(f"COPY ({select_sql}) TO {path_lit} (DELIMITER ',', {header_clause});", list(params))
        else:
            con.execute(f"COPY ({select_sql}) TO {path_lit} (DELIMITER ',', {header_clause});")
        con.close()
    
    # ---------- plugin discovery ----------
    def plugin_root(self, name: str, root: str | Path | None = None) -> Path:
        base = Path(root) if root else Path("extern") / "pints-plugins" / "sql"
        return base / name

    def plugin_manifest(self, name: str, root: str | Path | None = None) -> dict:
        plugdir = self.plugin_root(name, root)
        mpath = plugdir / "manifest.yaml"
        if not mpath.exists():
            raise FileNotFoundError(f"manifest.yaml not found for plugin '{name}' at {mpath}")
        return yaml.safe_load(mpath.read_text(encoding="utf-8"))

    # ---------- install / schema ----------
    def plugin_install(self, name: str, root: str | Path | None = None) -> None:
        manifest = self.plugin_manifest(name, root)
        plugdir = self.plugin_root(name, root)
        schema_file = plugdir / manifest.get("schema", "plugin.sql")
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema SQL not found: {schema_file}")
        self.migrate(schema_file)

    # ---------- staging ----------
    def plugin_staging_create(self, name: str, root: str | Path | None = None) -> None:
        m = self.plugin_manifest(name, root)
        st = m.get("staging") or {}
        table = st.get("table")
        cols  = st.get("columns") or []
        if not table or not cols:
            return  # plugin may not use staging
        ddl_cols = ", ".join(f"{c['name']} {c['type']}" for c in cols)
        con = self._connect()
        con.execute(f"CREATE TABLE IF NOT EXISTS {table} ({ddl_cols});")
        con.close()

    def plugin_staging_clear(self, name: str, root: str | Path | None = None) -> None:
        m = self.plugin_manifest(name, root)
        st = m.get("staging") or {}
        table = st.get("table")
        if not table:
            return
        con = self._connect()
        con.execute(f"DELETE FROM {table};")
        con.close()

    def plugin_staging_load_csv(self, name: str, csv_path: str, root: str | Path | None = None) -> None:
        m = self.plugin_manifest(name, root)
        st = m.get("staging") or {}
        table = st.get("table")
        cols  = st.get("columns") or []
        load  = (st.get("load") or {}).get("csv", {})
        if not table or not cols:
            raise ValueError(f"Plugin '{name}' does not define staging.table/columns in manifest.")
        # ensure table exists
        self.plugin_staging_create(name, root)
        # COPY options
        header     = load.get("header", True)
        autodetect = load.get("autodetect", True)
        delim      = load.get("delimiter", ",")
        path_lit = "'" + str(csv_path).replace("'", "''") + "'"
        header_opt = "HEADER" if header else "HEADER FALSE"
        autod_opt  = "AUTO_DETECT TRUE" if autodetect else ""
        delim_opt  = f"DELIMITER '{delim}'" if delim else ""
        col_list = ", ".join(c["name"] for c in cols)
        opts = ", ".join([o for o in [autod_opt, header_opt, delim_opt] if o])
        con = self._connect()
        con.execute(f"COPY {table} ({col_list}) FROM {path_lit} ({opts});")
        con.close()

    # ---------- actions (materialize/export/any) ----------
    def _plugin_action_sql(self, name: str, action: str, root: str | Path | None = None) -> str:
        m = self.plugin_manifest(name, root)
        plugdir = self.plugin_root(name, root)
        acts = {a["name"]: a for a in (m.get("actions") or [])}
        if action not in acts:
            raise KeyError(f"Plugin '{name}' has no action named '{action}'")
        f = plugdir / acts[action]["file"]
        if not f.exists():
            raise FileNotFoundError(f"SQL for action '{action}' not found: {f}")
        return f.read_text(encoding="utf-8"), acts[action]

    def plugin_action_run(self, name: str, action: str, params: Optional[dict] = None,
                          root: str | Path | None = None):
        sql, meta = self._plugin_action_sql(name, action, root)
        # Bind params in manifest order if provided
        values: Optional[list[Any]] = None
        if params and "params" in meta:
            order = [p["name"] for p in meta["params"]]
            values = [params.get(k, p.get("default")) for p, k in zip(meta["params"], order)]
        return self.run_sql(sql, values)

    def plugin_export(self, name: str, out_csv: str, action: str = "export",
                      root: str | Path | None = None, header: bool = True):
        sql, _ = self._plugin_action_sql(name, action, root)
        self.export_sql(sql, out_csv, header=header)
