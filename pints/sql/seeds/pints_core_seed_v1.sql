-- ============================================
-- PINTS Core Seed v1.0.0 (extended, hierarchical IDs)
-- Minimal PSI-MS vocabulary + demo dataset + property registry
-- ============================================

-- Optional: clean start (use only for demo/testing, not in production!)
DELETE FROM feature_properties;
DELETE FROM run_properties;
DELETE FROM sample_properties;
DELETE FROM prop_dictionary;
DELETE FROM prop_prefixes;
DELETE FROM features;
DELETE FROM runs;
DELETE FROM samples;
DELETE FROM field_dictionary;
DELETE FROM units;
DELETE FROM ontology_terms;
DELETE FROM ontology_sources;
DELETE FROM schema_migrations;
DELETE FROM vocabulary_info;
DELETE FROM schema_info;

-- 0) Versioning bootstrap
INSERT OR REPLACE INTO schema_info(schema_name, schema_version, created_utc, min_duckdb_version, notes)
VALUES ('pints_schema','1.0.0', CURRENT_TIMESTAMP, NULL, 'Initial release of PINTS Core schema (extended with property registry, provenance, hierarchical IDs)');

INSERT OR REPLACE INTO vocabulary_info(vocab_name, vocab_version, source, notes, updated_utc)
VALUES ('pints_dictionary','1.0.0','PSI-MS/UO','Initial mapping: mz, rt, area; plus property prefixes and keys', CURRENT_TIMESTAMP);

-- 1) Ontology sources
INSERT OR REPLACE INTO ontology_sources(prefix, name, base_uri, version, homepage) VALUES
('MS','PSI-MS Ontology','http://purl.obolibrary.org/obo/MS_', NULL, 'https://www.ebi.ac.uk/ols/ontologies/ms');

-- 2) Minimal PSI-MS terms we need for Core
INSERT OR REPLACE INTO ontology_terms(prefix, accession, uri, label, definition, synonyms) VALUES
('MS','1000744','http://purl.obolibrary.org/obo/MS_1000744','mass to charge ratio', NULL, NULL),
('MS','1000894','http://purl.obolibrary.org/obo/MS_1000894','retention time',       NULL, NULL),
('MS','1000040','http://purl.obolibrary.org/obo/MS_1000040','peak area',            NULL, NULL);

-- 3) Units
INSERT OR REPLACE INTO units(unit_code, label, uri) VALUES
('UO:0000040','dimensionless ratio','http://purl.obolibrary.org/obo/UO_0000040'),
('UO:0000010','second','http://purl.obolibrary.org/obo/UO_0000010'),
('a.u.','arbitrary unit', NULL);

-- 4) Field dictionary (maps column names -> ontology + unit)
INSERT OR REPLACE INTO field_dictionary(field_name, label, ontology_uri, unit_code, required, description) VALUES
('mz',   'mass-to-charge ratio','http://purl.obolibrary.org/obo/MS_1000744','UO:0000040', TRUE,  'Feature centroid m/z'),
('rt',   'retention time',      'http://purl.obolibrary.org/obo/MS_1000894','UO:0000010', TRUE,  'Chromatographic retention time (seconds)'),
('area', 'peak area',           'http://purl.obolibrary.org/obo/MS_1000040','a.u.',       FALSE, 'Integrated peak area (arbitrary units)');

-- 5) Property registry: allowed prefixes
INSERT OR REPLACE INTO prop_prefixes(prefix, label, description) VALUES
('qc','Quality Control','Quality metrics such as DQS, SNR, MID'),
('peakwidth','Peak Width','Peak width concepts (FWHM, width at 10%)'),
('peakshape','Peak Shape','Tailing factor, asymmetry, etc.'),
('intensity','Intensity','Intensity-derived metrics'),
('uncertainty','Uncertainty','Uncertainty of another registered property');

-- 6) Canonical property keys (dictionary)
-- Base properties
INSERT OR REPLACE INTO prop_dictionary(prop_key, prefix, label, ontology_uri, unit_code, description, base_prop_key) VALUES
('qc.dqs',             'qc',        'Data Quality Score',       'http://example.org/nts#dqsFeature', 'a.u.',       'Scaled quality score (0..1)', NULL),
('qc.snr',             'qc',        'Signal-to-Noise Ratio',    NULL,                                 NULL,         'S/N estimate',                NULL),
('peakwidth.fwhm',     'peakwidth', 'Full Width at Half Max',   NULL,                                 'UO:0000010', 'FWHM in seconds',            NULL),
('peakwidth.at10pct',  'peakwidth', 'Width at 10% height',      NULL,                                 'UO:0000010', 'Peak width at 10% height',   NULL);

-- Uncertainties (absolute uses same unit as base; relative uses dimensionless UO:0000040)
INSERT OR REPLACE INTO prop_dictionary(prop_key, prefix, label, ontology_uri, unit_code, description, base_prop_key) VALUES
('uncertainty.qc.dqs',             'uncertainty', 'Uncertainty of DQS',                NULL,          'a.u.',        'Std/SE of DQS (absolute)',     'qc.dqs'),
('uncertainty.qc.dqs.rel',         'uncertainty', 'Relative uncertainty of DQS',       NULL,          'UO:0000040',  'Relative uncertainty (0..1)',   'qc.dqs'),
('uncertainty.peakwidth.fwhm',     'uncertainty', 'Uncertainty of FWHM',               NULL,          'UO:0000010',  'Std/SE of FWHM (seconds)',      'peakwidth.fwhm'),
('uncertainty.peakwidth.fwhm.rel', 'uncertainty', 'Relative uncertainty of FWHM',      NULL,          'UO:0000040',  'Relative uncertainty (0..1)',   'peakwidth.fwhm');

-- 7) Demo dataset (1 sample, 1 run, 3 features) — hierarchical IDs
INSERT INTO samples(sample_id, sample_type, description) VALUES
('S001','Sample','River water (Ruhr, 2025-09-12)');

INSERT INTO runs(sample_id, run_id, acq_time_utc, instrument, method_id, batch_id) VALUES
('S001','R001','2025-09-12 09:00:00','QTOF-XYZ','POS_5min','B01');

INSERT INTO features(sample_id, run_id, feature_id, mz, rt, area) VALUES
('S001','R001','F0001',301.123456,312.4,154321.2),
('S001','R001','F0002',445.234567,313.1,  53211.0),
('S001','R001','F0003',150.045678,115.8,  10342.5);

-- 8) Example properties with provenance (two algos on same feature key)
-- Feature-level: DQS (absolute) + uncertainties (absolute/relative)
INSERT INTO feature_properties(sample_id, run_id, feature_id, prop_key, prop_value, unit_code, algo_id, algo_version, params_json) VALUES
('S001','R001','F0001','qc.dqs',                         0.87,   'a.u.','qAlgorithms','1.2.0','{"model":"rf","n":500}'),
('S001','R001','F0001','uncertainty.qc.dqs',             0.05,   'a.u.','qAlgorithms','1.2.0','{"method":"bootstrap","B":1000}'),
('S001','R001','F0001','uncertainty.qc.dqs.rel',         0.0575, 'UO:0000040','qAlgorithms','1.2.0','{"derived":"abs/base"}'),
('S001','R001','F0001','qc.dqs',                         0.83,   'a.u.','VendorX','0.9','{"mode":"fast"}'),
('S001','R001','F0001','uncertainty.qc.dqs',             0.04,   'a.u.','VendorX','0.9','{"method":"jackknife"}'),
('S001','R001','F0001','uncertainty.qc.dqs.rel',         0.0482, 'UO:0000040','VendorX','0.9','{"derived":"abs/base"}'),

-- Feature-level: FWHM + uncertainties from two algos
('S001','R001','F0001','peakwidth.fwhm',                 2.35,   'UO:0000010','qAlgorithms','1.2.0','{"fit":"gauss"}'),
('S001','R001','F0001','uncertainty.peakwidth.fwhm',     0.12,   'UO:0000010','qAlgorithms','1.2.0','{"se":"ols"}'),
('S001','R001','F0001','uncertainty.peakwidth.fwhm.rel', 0.0511, 'UO:0000040','qAlgorithms','1.2.0','{"derived":"abs/base"}'),
('S001','R001','F0001','peakwidth.fwhm',                 2.28,   'UO:0000010','VendorX','0.9','{"fit":"lorentz"}'),
('S001','R001','F0001','uncertainty.peakwidth.fwhm',     0.18,   'UO:0000010','VendorX','0.9','{"se":"robust"}'),
('S001','R001','F0001','uncertainty.peakwidth.fwhm.rel', 0.0789, 'UO:0000040','VendorX','0.9','{"derived":"abs/base"}');

-- (Optional) Run-level example (for completeness)
INSERT INTO run_properties(sample_id, run_id, prop_key, prop_value, unit_code, algo_id, algo_version, params_json) VALUES
('S001','R001','qc.snr', 25.0, NULL, 'qAlgorithms','1.2.0','{"method":"median-noise"}');

-- (Optional) Sample-level example
INSERT INTO sample_properties(sample_id, prop_key, prop_value, unit_code, algo_id, algo_version, params_json) VALUES
('S001','qc.snr', 30.0, NULL, 'VendorX','0.9','{"agg":"median"}');

-- 9) Optional: simple resolution policy
-- For uncertainties prefer MIN; for DQS prefer latest and higher value on tie.
INSERT OR REPLACE INTO prop_resolution_policy(prop_key, prefer_algo, prefer_latest, prefer_max, prefer_min) VALUES
('uncertainty.qc.dqs',              NULL, TRUE,  FALSE, TRUE),
('uncertainty.qc.dqs.rel',          NULL, TRUE,  FALSE, TRUE),
('uncertainty.peakwidth.fwhm',      NULL, TRUE,  FALSE, TRUE),
('uncertainty.peakwidth.fwhm.rel',  NULL, TRUE,  FALSE, TRUE),
('qc.dqs',                          NULL, TRUE,  TRUE,  FALSE),
('peakwidth.fwhm',                  NULL, TRUE,  FALSE, FALSE);

-- ============================================
-- End of PINTS Core Seed (extended, hierarchical IDs)
-- ============================================
