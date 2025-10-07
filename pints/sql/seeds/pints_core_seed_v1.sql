-- ============================================
-- PINTS Core Seed v1.0.0
-- Minimal PSI-MS vocabulary + demo dataset
-- ============================================

-- Optional: clean start (use only for demo/testing, not in production!)
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
VALUES ('pints_schema','1.0.0', CURRENT_TIMESTAMP, NULL, 'Initial release of PINTS Core schema');

INSERT OR REPLACE INTO vocabulary_info(vocab_name, vocab_version, source, notes, updated_utc)
VALUES ('pints_dictionary','1.0.0','PSI-MS/UO','Initial mapping: mz, rt, area', CURRENT_TIMESTAMP);

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

-- 5) Optional tiny demo dataset (1 sample, 1 run, 3 features)
INSERT INTO samples(sample_id, sample_type, description) VALUES
('S001','Sample','River water (Ruhr, 2025-09-12)');

INSERT INTO runs(run_id, sample_id, acq_time_utc, instrument, method_id, batch_id) VALUES
('R001','S001','2025-09-12 09:00:00','QTOF-XYZ','POS_5min','B01');

INSERT INTO features(feature_id, run_id, sample_id, mz, rt, area) VALUES
('F0001','R001','S001',301.123456,312.4,154321.2),
('F0002','R001','S001',445.234567,313.1,  53211.0),
('F0003','R001','S001',150.045678,115.8,  10342.5);

-- ============================================
-- End of PINTS Core Seed v1.0.0
-- ============================================
