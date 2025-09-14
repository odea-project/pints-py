-- ============================================
-- PINTS Core Schema v1.0.0
-- Pipelines for Non-Target Screening
-- ============================================

-- 0) Versioning tables
-- Keep track of schema and vocabulary versions
CREATE TABLE IF NOT EXISTS schema_info (
  schema_name         TEXT PRIMARY KEY,              -- e.g., 'pints_schema'
  schema_version      TEXT NOT NULL,                 -- e.g., '1.0.0'
  created_utc         TIMESTAMP NOT NULL,
  min_duckdb_version  TEXT,                          -- optional, if features require a minimum DuckDB version
  notes               TEXT
);

CREATE TABLE IF NOT EXISTS schema_migrations (
  migration_id   TEXT PRIMARY KEY,                   -- e.g., '2025-09-12_001_add_rt_sigma'
  applied_utc    TIMESTAMP NOT NULL,
  from_version   TEXT NOT NULL,
  to_version     TEXT NOT NULL,
  description    TEXT NOT NULL,
  sql_up         TEXT,                               -- SQL used to migrate up
  sql_down       TEXT                                -- optional rollback
);

-- Optional: vocabulary/dictionary versioning
CREATE TABLE IF NOT EXISTS vocabulary_info (
  vocab_name     TEXT PRIMARY KEY,                   -- e.g., 'pints_dictionary'
  vocab_version  TEXT NOT NULL,                      -- e.g., '1.0.0'
  source         TEXT,                               -- e.g., 'PSI-MS','UO'
  notes          TEXT,
  updated_utc    TIMESTAMP NOT NULL
);

-- 1) Ontology & dictionary
-- These tables allow semantic mapping of fields to PSI-MS ontology terms
CREATE TABLE IF NOT EXISTS ontology_sources (
  prefix   TEXT PRIMARY KEY,         -- e.g., 'MS' for PSI-MS
  name     TEXT NOT NULL,            -- human-readable ontology name
  base_uri TEXT NOT NULL,            -- e.g., 'http://purl.obolibrary.org/obo/MS_'
  version  TEXT,                     -- optional ontology version
  homepage TEXT                      -- optional homepage link
);

CREATE TABLE IF NOT EXISTS ontology_terms (
  prefix     TEXT NOT NULL,          -- 'MS'
  accession  TEXT NOT NULL,          -- '1000744'
  uri        TEXT NOT NULL,          -- full URI: 'http://purl.obolibrary.org/obo/MS_1000744'
  label      TEXT NOT NULL,          -- human-readable label: 'mass to charge ratio'
  definition TEXT,                   -- optional definition
  synonyms   TEXT,                   -- optional JSON array (as TEXT)
  PRIMARY KEY (prefix, accession)
);

CREATE TABLE IF NOT EXISTS units (
  unit_code  TEXT PRIMARY KEY,       -- e.g., 'UO:0000010' or 'a.u.'
  label      TEXT,                   -- e.g., 'second'
  uri        TEXT                    -- e.g., 'http://purl.obolibrary.org/obo/UO_0000010'
);

CREATE TABLE IF NOT EXISTS field_dictionary (
  field_name   TEXT PRIMARY KEY,     -- e.g., 'mz', 'rt', 'area'
  label        TEXT NOT NULL,        -- human-readable label
  ontology_uri TEXT,                 -- link to PSI-MS URI
  unit_code    TEXT,                 -- link to units.unit_code
  required     BOOLEAN,              -- whether the field is mandatory in PINTS Core
  description  TEXT
);

-- Helpful semantic view
CREATE OR REPLACE VIEW v_field_semantics AS
SELECT
  f.field_name,
  f.label,
  f.ontology_uri,
  f.unit_code,
  u.uri    AS unit_uri,
  f.required,
  f.description
FROM field_dictionary f
LEFT JOIN units u ON u.unit_code = f.unit_code;

-- 2) Core data entities
-- These are the mandatory data tables in PINTS Core

-- A sample is a logical entity: can be a real sample, blank, QC, or standard
CREATE TABLE IF NOT EXISTS samples (
  sample_id   TEXT PRIMARY KEY,
  sample_type TEXT,                  -- e.g., 'Sample','Blank','Standard','QC'
  description TEXT
);

-- A run is a specific measurement of a sample
CREATE TABLE IF NOT EXISTS runs (
  run_id       TEXT PRIMARY KEY,
  sample_id    TEXT NOT NULL REFERENCES samples(sample_id),
  acq_time_utc TIMESTAMP,            -- acquisition time
  instrument   TEXT,
  method_id    TEXT,
  batch_id     TEXT
);

-- A feature is a detected peak within a run
CREATE TABLE IF NOT EXISTS features (
  feature_id  TEXT PRIMARY KEY,
  run_id      TEXT NOT NULL REFERENCES runs(run_id),
  mz          DOUBLE NOT NULL,       -- PSI-MS: MS:1000744 (mass/charge)
  rt          DOUBLE,                -- PSI-MS: MS:1000894 (retention time in seconds)
  area        DOUBLE                 -- PSI-MS: MS:1000040 (arbitrary units)
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_features_run  ON features(run_id);
CREATE INDEX IF NOT EXISTS idx_features_mzrt ON features(mz, rt);

-- ============================================
-- End of PINTS Core Schema v1.0.0
-- ============================================
