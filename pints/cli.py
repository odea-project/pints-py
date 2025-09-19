# pints/cli.py
"""
PINTS CLI
---------
Command-line utilities for managing a PINTS DuckDB database.

Examples
    pints init --db pints.duckdb
    pints seed --db pints.duckdb
    pints add-sample --db pints.duckdb --id S001 --type Sample --desc "River water"
    pints add-run    --db pints.duckdb --id R001 --sample S001 --time "2025-09-12 09:00:00" --instrument QTOF-XYZ --method POS_5min --batch B01
    pints add-feature --db pints.duckdb --id R001_F0001 --run R001 --mz 301.123456 --rt 312.4 --area 154321.2
    pints show-version --db pints.duckdb
    pints list-tables --db pints.duckdb
    pints export features --db pints.duckdb --out features.csv
    pints migrate --db pints.duckdb --file path/to/plugin.sql
    pints run-sql --db pints.duckdb --query "SELECT COUNT(*) FROM features"
    pints export-sql --db pints.duckdb --query "SELECT * FROM features" --out features.csv
    pints set-prop --db pints.duckdb --level feature --id R001_F0001 --key dqs --value 0.87 --uri http://example.org/nts#dqsFeature
    pints get-props --db pints.duckdb --level feature --id R001_F0001

    # Plugins (manifest-driven)
    pints plugin install --db my.duckdb --name intra_run_components
    pints plugin staging-create --db my.duckdb --name intra_run_components
    pints plugin load-csv --db my.duckdb --name intra_run_components --csv assignments.csv
    pints plugin insert --db my.duckdb --name intra_run_components --rows "R001,R001_F0001,C001" "R001,R001_F0002,C001" --materialize
    pints plugin action --db my.duckdb --name intra_run_components --action materialize
    pints plugin export --db my.duckdb --name intra_run_components --out intra.csv
"""

import argparse
import os
from pathlib import Path
import duckdb

from .db import PintsDB


def _default_db_arg(parser: argparse.ArgumentParser):
    default_db = os.environ.get("PINTS_DB", "pints.duckdb")
    parser.add_argument("--db", default=default_db, help="Path to DuckDB file (default: %(default)s or $PINTS_DB)")


def _parse_params(kvs: list[str]) -> dict:
    out = {}
    for kv in kvs or []:
        if "=" not in kv:
            raise SystemExit(f"--param expects key=value, got: {kv}")
        k, v = kv.split("=", 1)
        # naive coercion: try float, else keep string
        try:
            v = float(v) if "." in v or v.isdigit() else v
        except Exception:
            pass
        out[k] = v
    return out


# ---------------- command handlers ----------------

def cmd_init(args):
    db = PintsDB(args.db)
    db.init_schema()
    print(f"✅ Schema initialized in {args.db}")


def cmd_seed(args):
    db = PintsDB(args.db)
    db.seed_minimal_vocab()
    print(f"✅ Seeded minimal PSI-MS dictionary in {args.db}")


def cmd_add_sample(args):
    db = PintsDB(args.db)
    db.add_sample(args.id, sample_type=args.type, description=args.desc)
    print(f"✅ Sample '{args.id}' upserted")


def cmd_add_run(args):
    db = PintsDB(args.db)
    db.add_run(
        args.id,
        sample_id=args.sample,
        acq_time_utc=args.time,
        instrument=args.instrument,
        method_id=args.method,
        batch_id=args.batch,
    )
    print(f"✅ Run '{args.id}' upserted")


def cmd_add_feature(args):
    db = PintsDB(args.db)
    db.add_feature(args.id, run_id=args.run, sample_id=args.sample, mz=args.mz, rt=args.rt, area=args.area)
    print(f"✅ Feature '{args.id}' upserted")


def cmd_show_version(args):
    con = duckdb.connect(args.db)
    try:
        schema_row = con.execute(
            "SELECT schema_version FROM schema_info WHERE schema_name='pints_schema'"
        ).fetchone()
        vocab_row = con.execute(
            "SELECT vocab_version FROM vocabulary_info WHERE vocab_name='pints_dictionary'"
        ).fetchone()
    finally:
        con.close()
    print("Schema version:", schema_row[0] if schema_row else "(not initialized)")
    print("Vocab  version:", vocab_row[0] if vocab_row else "(not seeded)")


def cmd_list_tables(args):
    con = duckdb.connect(args.db)
    try:
        df = con.execute("SHOW TABLES").fetchdf()
    finally:
        con.close()
    print(df)


def cmd_export(args):
    db = PintsDB(args.db)
    db.export_table(args.table, args.out, header=not args.no_header)
    print(f"✅ Exported '{args.table}' to {args.out} (header={'no' if args.no_header else 'yes'})")


def cmd_migrate(args):
    sql_path = Path(args.file)
    if not sql_path.exists():
        raise SystemExit(f"❌ File not found: {sql_path}")
    db = PintsDB(args.db)
    db.migrate(sql_path)
    print(f"✅ Applied SQL: {sql_path}")


def cmd_run_sql(args):
    # Accept either a literal SELECT or a path to a .sql file
    if args.query.lower().endswith(".sql") and Path(args.query).exists():
        sql = Path(args.query).read_text(encoding="utf-8")
    else:
        sql = args.query
    db = PintsDB(args.db)
    df = db.run_sql(sql)
    if df is None:
        print("✅ Statement executed (no result set).")
    else:
        print(df)


def cmd_export_sql(args):
    # Accept either a literal SELECT or a path to a .sql file
    if args.query.lower().endswith(".sql") and Path(args.query).exists():
        sql = Path(args.query).read_text(encoding="utf-8")
    else:
        sql = args.query
    db = PintsDB(args.db)
    db.export_sql(sql, args.out, header=not args.no_header)
    print(f"✅ Exported query to {args.out} (header={'no' if args.no_header else 'yes'})")


def cmd_set_prop(args):
    db = PintsDB(args.db)
    db.set_algo_property(
        args.level, args.id, args.key,
        value=args.value, value_text=args.value_text,
        unit_code=args.unit, ontology_uri=args.uri
    )
    print(f"✅ Set property '{args.key}' on {args.level}:{args.id}")


def cmd_get_props(args):
    db = PintsDB(args.db)
    df = db.get_algo_properties(args.level, args.id)
    if df is None or df.empty:
        print("(no properties or table not present)")
    else:
        print(df)


# ---------------- plugin command handlers (manifest-driven) ----------------

def cmd_plugin_install(a):
    db = PintsDB(a.db)
    db.plugin_install(a.name, root=a.root)
    print(f"✅ Installed plugin '{a.name}'")


def cmd_plugin_staging_create(a):
    db = PintsDB(a.db)
    db.plugin_staging_create(a.name, root=a.root)
    print(f"✅ Staging created for '{a.name}'")


def cmd_plugin_staging_clear(a):
    db = PintsDB(a.db)
    db.plugin_staging_clear(a.name, root=a.root)
    print(f"✅ Staging cleared for '{a.name}'")


def cmd_plugin_load_csv(a):
    db = PintsDB(a.db)
    db.plugin_staging_load_csv(a.name, a.csv, root=a.root)
    print(f"✅ CSV loaded into staging for '{a.name}': {a.csv}")


def cmd_plugin_action(a):
    db = PintsDB(a.db)
    params = _parse_params(a.param)
    df = db.plugin_action_run(a.name, a.action, params=params, root=a.root)
    print("(no result set)" if df is None else df)


def cmd_plugin_export(a):
    db = PintsDB(a.db)
    db.plugin_export(a.name, a.out, action=a.action, root=a.root, header=not a.no_header)
    print(f"✅ Exported '{a.name}:{a.action}' -> {a.out}")


def cmd_plugin_apply(a):
    db = PintsDB(a.db)
    db.plugin_install(a.name, root=a.root)         # idempotent
    db.plugin_staging_create(a.name, root=a.root)  # idempotent
    db.plugin_staging_load_csv(a.name, a.csv, root=a.root)
    db.plugin_action_run(a.name, "materialize", root=a.root)
    if a.clear_staging:
        db.plugin_staging_clear(a.name, root=a.root)
    print(f"✅ Applied plugin '{a.name}' from CSV: {a.csv}")


def cmd_plugin_insert(a):
    """
    Insert rows directly into the plugin's staging table, based on manifest 'staging.columns'.
    Example:
      pints plugin insert --db my.duckdb --name intra_run_components \\
        --rows "R001,R001_F0001,C001" "R001,R001_F0002,C001" --materialize
    """
    db = PintsDB(a.db)
    # Read manifest to get staging table & columns
    manifest = db.plugin_manifest(a.name, root=a.root)
    st = (manifest.get("staging") or {})
    table = st.get("table")
    cols = st.get("columns") or []
    if not table or not cols:
        raise SystemExit(f"Plugin '{a.name}' does not define staging.table/columns in manifest.")

    col_names = [c["name"] for c in cols]
    ncols = len(col_names)

    # Ensure staging exists
    db.plugin_staging_create(a.name, root=a.root)

    # Prepare parameterized INSERT
    placeholders = ", ".join(["?"] * ncols)
    collist = ", ".join(col_names)
    sql = f"INSERT INTO {table} ({collist}) VALUES ({placeholders})"

    # Insert rows
    con = duckdb.connect(a.db)
    try:
        total = 0
        for row_str in a.rows:
            parts = [p.strip() for p in row_str.split(a.delimiter)]
            if len(parts) != ncols:
                raise SystemExit(
                    f"Row has {len(parts)} fields but staging expects {ncols} ({col_names}). Row: {row_str}"
                )
            con.execute(sql, parts)
            total += 1
    finally:
        con.close()

    print(f"✅ Inserted {total} row(s) into staging '{table}' for plugin '{a.name}'")

    # Optional: materialize immediately
    if a.materialize:
        db.plugin_action_run(a.name, "materialize", root=a.root)
        print("✅ Materialized after insert")


# ---------------- main ----------------

def main():
    p = argparse.ArgumentParser(prog="pints", description="PINTS DuckDB utilities (Core + Plugins)")
    sub = p.add_subparsers(dest="cmd", required=True)

    # Core
    s = sub.add_parser("init", help="Create core schema (idempotent)")
    _default_db_arg(s)
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("seed", help="Seed minimal PSI-MS dictionary")
    _default_db_arg(s)
    s.set_defaults(func=cmd_seed)

    s = sub.add_parser("add-sample", help="Upsert a sample")
    _default_db_arg(s)
    s.add_argument("--id", required=True)
    s.add_argument("--type", default=None)
    s.add_argument("--desc", default=None)
    s.set_defaults(func=cmd_add_sample)

    s = sub.add_parser("add-run", help="Upsert a run (requires existing sample)")
    _default_db_arg(s)
    s.add_argument("--id", required=True)
    s.add_argument("--sample", required=True)
    s.add_argument("--time", default=None, help='e.g. "2025-09-12 09:00:00"')
    s.add_argument("--instrument", default=None)
    s.add_argument("--method", default=None)
    s.add_argument("--batch", default=None)
    s.set_defaults(func=cmd_add_run)

    s = sub.add_parser("add-feature", help="Upsert a feature (requires existing run)")
    _default_db_arg(s)
    s.add_argument("--id", required=True)
    s.add_argument("--run", required=True)
    s.add_argument("--sample", required=True)
    s.add_argument("--mz", type=float, required=True)
    s.add_argument("--rt", type=float, default=None)
    s.add_argument("--area", type=float, default=None)
    s.set_defaults(func=cmd_add_feature)

    s = sub.add_parser("show-version", help="Print schema/vocab versions")
    _default_db_arg(s)
    s.set_defaults(func=cmd_show_version)

    s = sub.add_parser("list-tables", help="Show tables in the DB")
    _default_db_arg(s)
    s.set_defaults(func=cmd_list_tables)

    s = sub.add_parser("export", help="Export a table or view to CSV")
    _default_db_arg(s)
    s.add_argument("table", help="Table or view name (e.g. features, v_field_semantics)")
    s.add_argument("--out", required=True, help="Output CSV file")
    s.add_argument("--no-header", action="store_true", help="Disable header row in CSV")
    s.set_defaults(func=cmd_export)

    # Plugins / generic SQL
    s = sub.add_parser("migrate", help="Apply a local .sql file to the DB (plugins or migrations)")
    _default_db_arg(s)
    s.add_argument("--file", required=True, help="Path to .sql file")
    s.set_defaults(func=cmd_migrate)

    s = sub.add_parser("run-sql", help="Run a SELECT or DDL/DML statement (or a .sql file) and print result")
    _default_db_arg(s)
    s.add_argument("--query", required=True, help='Either a SELECT like "SELECT 1" or a path to .sql')
    s.set_defaults(func=cmd_run_sql)

    s = sub.add_parser("export-sql", help="Export the result of a SELECT (or .sql file) to CSV")
    _default_db_arg(s)
    s.add_argument("--query", required=True, help='Either a SELECT like "SELECT * FROM features" or a path to .sql')
    s.add_argument("--out", required=True, help="Output CSV file")
    s.add_argument("--no-header", action="store_true", help="Disable header row in CSV")
    s.set_defaults(func=cmd_export_sql)

    s = sub.add_parser("set-prop", help="Set an algorithm-specific property (generic key–value store)")
    _default_db_arg(s)
    s.add_argument("--level", required=True, choices=["feature", "component_intra", "run"])
    s.add_argument("--id", required=True, help="Entity id: feature_id / intra_run_component_id / run_id")
    s.add_argument("--key", required=True, help="Property key, e.g. dqs, snr")
    s.add_argument("--value", type=float, default=None)
    s.add_argument("--value-text", default=None)
    s.add_argument("--unit", default=None)
    s.add_argument("--uri", default=None)
    s.set_defaults(func=cmd_set_prop)

    s = sub.add_parser("get-props", help="Fetch algorithm-specific properties for an entity")
    _default_db_arg(s)
    s.add_argument("--level", required=True, choices=["feature", "component_intra", "run"])
    s.add_argument("--id", required=True)
    s.set_defaults(func=cmd_get_props)

    # Plugin command group (manifest-driven)
    s = sub.add_parser("plugin", help="Generic plugin commands (manifest-driven)")
    _default_db_arg(s)
    sp = s.add_subparsers(dest="plugin_cmd", required=True)

    s1 = sp.add_parser("install", help="Apply plugin schema (plugin.sql)")
    _default_db_arg(s1)
    s1.add_argument("--name", required=True)
    s1.add_argument("--root", default=None)
    s1.set_defaults(func=cmd_plugin_install)

    s2 = sp.add_parser("staging-create", help="Create staging table (from manifest)")
    _default_db_arg(s2)
    s2.add_argument("--name", required=True)
    s2.add_argument("--root", default=None)
    s2.set_defaults(func=cmd_plugin_staging_create)

    s3 = sp.add_parser("staging-clear", help="Clear staging data")
    _default_db_arg(s3)
    s3.add_argument("--name", required=True)
    s3.add_argument("--root", default=None)
    s3.set_defaults(func=cmd_plugin_staging_clear)

    s4 = sp.add_parser("load-csv", help="Load CSV into staging (columns from manifest)")
    _default_db_arg(s4)
    s4.add_argument("--name", required=True)
    s4.add_argument("--csv", required=True)
    s4.add_argument("--root", default=None)
    s4.set_defaults(func=cmd_plugin_load_csv)

    s5 = sp.add_parser("action", help="Run a declared action (e.g., materialize, export)")
    _default_db_arg(s5)
    s5.add_argument("--name", required=True)
    s5.add_argument("--action", required=True)
    s5.add_argument("--param", action="append", help="key=value (repeatable)")
    s5.add_argument("--root", default=None)
    s5.set_defaults(func=cmd_plugin_action)

    s6 = sp.add_parser("export", help="Export action result (defaults to 'export')")
    _default_db_arg(s6)
    s6.add_argument("--name", required=True)
    s6.add_argument("--out", required=True)
    s6.add_argument("--action", default="export")
    s6.add_argument("--no-header", action="store_true")
    s6.add_argument("--root", default=None)
    s6.set_defaults(func=cmd_plugin_export)

    s7 = sp.add_parser("apply", help="One-shot: install + load CSV + materialize (+clear)")
    _default_db_arg(s7)
    s7.add_argument("--name", required=True)
    s7.add_argument("--csv", required=True)
    s7.add_argument("--clear-staging", action="store_true")
    s7.add_argument("--root", default=None)
    s7.set_defaults(func=cmd_plugin_apply)

    # NEW: insert rows directly via CLI (no CSV)
    s8 = sp.add_parser("insert", help="Insert rows directly into staging (values parsed by manifest order)")
    _default_db_arg(s8)
    s8.add_argument("--name", required=True, help="Plugin name")
    s8.add_argument("--rows", required=True, nargs="+",
                    help="One or more rows like 'R001,R001_F0001,C001' (order must match manifest staging.columns)")
    s8.add_argument("--delimiter", default=",", help="Field delimiter in --rows (default: ',')")
    s8.add_argument("--materialize", action="store_true", help="Run 'materialize' after inserting")
    s8.add_argument("--root", default=None, help="Custom plugin root")
    s8.set_defaults(func=cmd_plugin_insert)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
