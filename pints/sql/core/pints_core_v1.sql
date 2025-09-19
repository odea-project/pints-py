-- ============================================
-- PINTS Core Schema v1.0.0 (extended, hierarchical IDs)
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

-- ------------------------------------------------------------
-- 1b) Property Prefix Registry + Property Dictionary
-- Plugins MAY define new keys, but their prefix MUST be registered here.
-- ------------------------------------------------------------

-- Allowed property prefixes (e.g., 'qc', 'peakwidth', 'alignment', 'uncertainty')
CREATE TABLE IF NOT EXISTS prop_prefixes (
  prefix      TEXT PRIMARY KEY,   -- e.g., 'qc'
  label       TEXT,               -- human-readable group name
  description TEXT
);

-- Central registry of algorithmic property keys.
-- We store the full key AND its prefix for a hard FK to prop_prefixes.
-- Optional: base_prop_key links "uncertainty.*" keys to their base property.
CREATE TABLE IF NOT EXISTS prop_dictionary (
  prop_key      TEXT PRIMARY KEY,  -- e.g., 'qc.dqs', 'peakwidth.fwhm', 'uncertainty.peakwidth.fwhm'
  prefix        TEXT NOT NULL,     -- extracted prefix, must exist in prop_prefixes
  label         TEXT NOT NULL,     -- human-friendly label
  ontology_uri  TEXT,              -- semantic URI for the concept (if available)
  unit_code     TEXT,              -- expected/default unit (optional)
  description   TEXT,
  base_prop_key TEXT,              -- if this is an uncertainty key, reference the base key
  FOREIGN KEY (prefix) REFERENCES prop_prefixes(prefix),
  FOREIGN KEY (base_prop_key) REFERENCES prop_dictionary(prop_key),
  -- Require namespacing (at least one dot)
  CHECK (instr(prop_key, '.') > 0),
  -- Guard that 'prefix' matches the actual start of 'prop_key'
  CHECK (prefix = regexp_extract(prop_key, '^[^.]+')),
  -- Enforce that every 'uncertainty.*' declares a base key
  CHECK (
    CASE WHEN prefix = 'uncertainty'
         THEN base_prop_key IS NOT NULL AND base_prop_key <> prop_key
         ELSE TRUE
    END
  )
);

-- ------------------------------------------------------------
-- 2) Core data entities (hierarchical composite keys)
-- ------------------------------------------------------------

-- A sample is a logical entity: can be a real sample, blank, QC, or standard
CREATE TABLE IF NOT EXISTS samples (
  sample_id   TEXT PRIMARY KEY,
  sample_type TEXT,                  -- e.g., 'Sample','Blank','Standard','QC'
  description TEXT
);

-- A run is a specific measurement of a sample
-- Composite PK ensures run identity is tied to its sample
CREATE TABLE IF NOT EXISTS runs (
  sample_id    TEXT NOT NULL REFERENCES samples(sample_id),
  run_id       TEXT NOT NULL,
  acq_time_utc TIMESTAMP,            -- acquisition time
  instrument   TEXT,
  method_id    TEXT,
  batch_id     TEXT,
  PRIMARY KEY (sample_id, run_id)
);

-- A feature is a detected peak within a run
-- Composite PK (sample_id, run_id, feature_id) ensures uniqueness and tight linkage
CREATE TABLE IF NOT EXISTS features (
  sample_id  TEXT NOT NULL,
  run_id     TEXT NOT NULL,
  feature_id TEXT NOT NULL,
  mz         DOUBLE NOT NULL,       -- PSI-MS: MS:1000744 (mass/charge)
  rt         DOUBLE,                -- PSI-MS: MS:1000894 (retention time in seconds)
  area       DOUBLE,                -- PSI-MS: MS:1000040 (arbitrary units)
  PRIMARY KEY (sample_id, run_id, feature_id),
  FOREIGN KEY (sample_id, run_id) REFERENCES runs(sample_id, run_id)
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_features_mzrt ON features(mz, rt);

-- Enriched view that adds run metadata to features (and keeps sample_id in sync)
CREATE OR REPLACE VIEW v_features_enriched AS
SELECT
  f.sample_id, f.run_id, f.feature_id, f.mz, f.rt, f.area,
  r.acq_time_utc, r.instrument, r.method_id, r.batch_id
FROM features f
JOIN runs r ON r.sample_id = f.sample_id AND r.run_id = f.run_id;

-- ------------------------------------------------------------
-- 3) Algorithmic properties per level (separate tables for strong FKs)
-- ------------------------------------------------------------

-- SAMPLE-level properties
CREATE TABLE IF NOT EXISTS sample_properties (
  sample_id     TEXT NOT NULL,
  prop_key      TEXT NOT NULL,                -- FK → prop_dictionary
  prop_value    DOUBLE,
  value_text    TEXT,
  unit_code     TEXT,
  ontology_uri  TEXT,
  -- Provenance (who/how)
  algo_id       TEXT NOT NULL DEFAULT 'default',
  algo_version  TEXT,
  params_json   TEXT,
  created_utc   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (sample_id, prop_key, algo_id),
  FOREIGN KEY (sample_id) REFERENCES samples(sample_id),
  FOREIGN KEY (prop_key)  REFERENCES prop_dictionary(prop_key)
);

-- RUN-level properties
CREATE TABLE IF NOT EXISTS run_properties (
  sample_id     TEXT NOT NULL,
  run_id        TEXT NOT NULL,
  prop_key      TEXT NOT NULL,
  prop_value    DOUBLE,
  value_text    TEXT,
  unit_code     TEXT,
  ontology_uri  TEXT,
  -- Provenance (who/how)
  algo_id       TEXT NOT NULL DEFAULT 'default',
  algo_version  TEXT,
  params_json   TEXT,
  created_utc   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (sample_id, run_id, prop_key, algo_id),
  FOREIGN KEY (sample_id, run_id) REFERENCES runs(sample_id, run_id),
  FOREIGN KEY (prop_key)         REFERENCES prop_dictionary(prop_key)
);

-- FEATURE-level properties
CREATE TABLE IF NOT EXISTS feature_properties (
  sample_id     TEXT NOT NULL,
  run_id        TEXT NOT NULL,
  feature_id    TEXT NOT NULL,
  prop_key      TEXT NOT NULL,
  prop_value    DOUBLE,
  value_text    TEXT,
  unit_code     TEXT,
  ontology_uri  TEXT,
  -- Provenance (who/how)
  algo_id       TEXT NOT NULL DEFAULT 'default',
  algo_version  TEXT,
  params_json   TEXT,
  created_utc   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (sample_id, run_id, feature_id, prop_key, algo_id),
  FOREIGN KEY (sample_id, run_id, feature_id)
    REFERENCES features(sample_id, run_id, feature_id),
  FOREIGN KEY (prop_key) REFERENCES prop_dictionary(prop_key)
);

-- ------------------------------------------------------------
-- 4) Unified read layer + semantic join + resolution & diagnostics
-- ------------------------------------------------------------

-- Unified view for all levels (keeps identifiers explicit)
CREATE OR REPLACE VIEW v_algo_properties_all AS
SELECT
  'sample' AS level,
  sp.sample_id,
  NULL     AS run_id,
  NULL     AS feature_id,
  sp.prop_key, sp.prop_value, sp.value_text,
  sp.unit_code, sp.ontology_uri,
  sp.algo_id, sp.algo_version, sp.params_json, sp.created_utc
FROM sample_properties sp
UNION ALL
SELECT
  'run' AS level,
  rp.sample_id, rp.run_id,
  NULL AS feature_id,
  rp.prop_key, rp.prop_value, rp.value_text,
  rp.unit_code, rp.ontology_uri,
  rp.algo_id, rp.algo_version, rp.params_json, rp.created_utc
FROM run_properties rp
UNION ALL
SELECT
  'feature' AS level,
  fp.sample_id, fp.run_id, fp.feature_id,
  fp.prop_key, fp.prop_value, fp.value_text,
  fp.unit_code, fp.ontology_uri,
  fp.algo_id, fp.algo_version, fp.params_json, fp.created_utc
FROM feature_properties fp;

-- Semantic join view
CREATE OR REPLACE VIEW v_algo_props_semantic AS
SELECT
  ap.level, ap.sample_id, ap.run_id, ap.feature_id,
  ap.prop_key, ap.prop_value, ap.value_text,
  ap.unit_code     AS unit_code_actual,
  ap.ontology_uri  AS ontology_uri_actual,
  ap.algo_id, ap.algo_version, ap.params_json, ap.created_utc,
  pd.prefix,
  pd.label         AS prop_label,
  pd.unit_code     AS unit_code_default,
  pd.ontology_uri  AS ontology_uri_default,
  pd.description   AS prop_description,
  pd.base_prop_key
FROM v_algo_properties_all ap
LEFT JOIN prop_dictionary pd ON pd.prop_key = ap.prop_key;

-- Resolution policy: choose a single value per entity/key
CREATE TABLE IF NOT EXISTS prop_resolution_policy (
  prop_key      TEXT PRIMARY KEY,   -- the semantic key
  prefer_algo   TEXT,               -- if set, prefer this algo_id
  prefer_latest BOOLEAN,            -- else prefer newest created_utc
  prefer_max    BOOLEAN,            -- else prefer larger value (e.g., SNR)
  prefer_min    BOOLEAN             -- else prefer smaller value (e.g., uncertainty)
);

-- Resolved view: one value per (level, entity, key)
CREATE OR REPLACE VIEW v_algo_props_resolved AS
WITH ranked AS (
  SELECT
    ap.*,
    ROW_NUMBER() OVER (
      PARTITION BY ap.level, ap.sample_id, ap.run_id, ap.feature_id, ap.prop_key
      ORDER BY
        (CASE WHEN prp.prefer_algo IS NOT NULL AND ap.algo_id = prp.prefer_algo THEN 0 ELSE 1 END),
        (CASE WHEN COALESCE(prp.prefer_latest, TRUE) THEN 0 ELSE 1 END),
        ap.created_utc DESC,
        (CASE WHEN COALESCE(prp.prefer_min, FALSE) THEN ap.prop_value END) ASC NULLS LAST,
        (CASE WHEN COALESCE(prp.prefer_max, FALSE) THEN ap.prop_value END) DESC NULLS LAST
    ) AS rk
  FROM v_algo_properties_all ap
  LEFT JOIN prop_resolution_policy prp ON prp.prop_key = ap.prop_key
)
SELECT * FROM ranked WHERE rk = 1;

-- Diagnostics: uncertainty exists but base value missing on same entity
CREATE OR REPLACE VIEW v_uncertainty_missing_base AS
WITH uncertainties AS (
  SELECT ap.level, ap.sample_id, ap.run_id, ap.feature_id, ap.prop_key, pd.base_prop_key
  FROM v_algo_properties_all ap
  JOIN prop_dictionary pd ON pd.prop_key = ap.prop_key
  WHERE pd.prefix = 'uncertainty'
),
bases AS (
  SELECT level, sample_id, run_id, feature_id, prop_key
  FROM v_algo_properties_all
)
SELECT u.level, u.sample_id, u.run_id, u.feature_id,
       u.prop_key AS uncertainty_key, u.base_prop_key
FROM uncertainties u
LEFT JOIN bases b
  ON b.level = u.level
 AND COALESCE(b.sample_id,'')  = COALESCE(u.sample_id,'')
 AND COALESCE(b.run_id,'')     = COALESCE(u.run_id,'')
 AND COALESCE(b.feature_id,'') = COALESCE(u.feature_id,'')
 AND b.prop_key = u.base_prop_key
WHERE b.prop_key IS NULL;

-- ============================================
-- End of PINTS Core Schema (extended, hierarchical IDs)
-- ============================================
