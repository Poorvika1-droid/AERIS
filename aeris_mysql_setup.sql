CREATE DATABASE IF NOT EXISTS aeris CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'aeris'@'localhost' IDENTIFIED BY 'aeris';
GRANT ALL PRIVILEGES ON aeris.* TO 'aeris'@'localhost';
FLUSH PRIVILEGES;
USE aeris;

CREATE TABLE IF NOT EXISTS forecast_sources (
    id VARCHAR(64) PRIMARY KEY,
    model_name VARCHAR(128) NOT NULL,
    provider VARCHAR(64) NOT NULL,
    model_type VARCHAR(32) NOT NULL,
    spatial_resolution VARCHAR(64) NOT NULL,
    status VARCHAR(32) DEFAULT 'ACTIVE',
    coverage VARCHAR(64) DEFAULT 'India (demo grid)',
    variables JSON,
    metadata_json JSON
);

CREATE TABLE IF NOT EXISTS locations (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    region VARCHAR(64) NOT NULL,
    elevation_m FLOAT,
    admin_level VARCHAR(32) DEFAULT 'city',
    INDEX ix_locations_region (region),
    INDEX ix_locations_lat_lon (latitude, longitude)
);

CREATE TABLE IF NOT EXISTS forecast_runs (
    id VARCHAR(64) PRIMARY KEY,
    model_id VARCHAR(64) NOT NULL,
    initialization_time DATETIME NOT NULL,
    lead_time_hours INT NOT NULL,
    variable VARCHAR(32) NOT NULL,
    valid_time DATETIME NOT NULL,
    units VARCHAR(32) NOT NULL,
    data_mode VARCHAR(32) DEFAULT 'demonstration',
    INDEX ix_fr_model (model_id),
    INDEX ix_fr_init (initialization_time),
    INDEX ix_fr_var (variable),
    INDEX ix_fr_valid (valid_time),
    FOREIGN KEY (model_id) REFERENCES forecast_sources(id)
);

CREATE TABLE IF NOT EXISTS forecast_values (
    id INT PRIMARY KEY AUTO_INCREMENT,
    run_id VARCHAR(64) NOT NULL,
    location_id VARCHAR(64) NOT NULL,
    value FLOAT NOT NULL,
    qc_flags JSON,
    INDEX ix_fv_run (run_id),
    INDEX ix_fv_loc (location_id),
    FOREIGN KEY (run_id) REFERENCES forecast_runs(id),
    FOREIGN KEY (location_id) REFERENCES locations(id)
);

CREATE TABLE IF NOT EXISTS observations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    location_id VARCHAR(64) NOT NULL,
    valid_time DATETIME NOT NULL,
    variable VARCHAR(32) NOT NULL,
    value FLOAT NOT NULL,
    source VARCHAR(64) DEFAULT 'demo-station',
    data_mode VARCHAR(32) DEFAULT 'demonstration',
    INDEX ix_obs_loc (location_id),
    INDEX ix_obs_time (valid_time),
    INDEX ix_obs_var (variable),
    FOREIGN KEY (location_id) REFERENCES locations(id)
);

CREATE TABLE IF NOT EXISTS model_skill (
    id INT PRIMARY KEY AUTO_INCREMENT,
    model_id VARCHAR(64) NOT NULL,
    region VARCHAR(64) NOT NULL,
    variable VARCHAR(32) NOT NULL,
    lead_time_bin INT NOT NULL,
    season VARCHAR(16) NOT NULL,
    regime VARCHAR(32) NOT NULL,
    window VARCHAR(16) DEFAULT '30d',
    mae FLOAT NOT NULL,
    rmse FLOAT NOT NULL,
    bias FLOAT NOT NULL,
    correlation FLOAT,
    brier FLOAT,
    crps FLOAT,
    csi FLOAT,
    precision FLOAT,
    recall FLOAT,
    sample_count INT NOT NULL,
    computed_at DATETIME NOT NULL,
    INDEX ix_ms_model (model_id),
    INDEX ix_ms_region (region),
    INDEX ix_ms_var (variable),
    INDEX ix_ms_regime (regime)
);

CREATE TABLE IF NOT EXISTS model_health (
    id INT PRIMARY KEY AUTO_INCREMENT,
    model_id VARCHAR(64) NOT NULL,
    health_score FLOAT NOT NULL,
    health_status VARCHAR(32) NOT NULL,
    health_reasons JSON NOT NULL,
    recommended_weight_adjustment FLOAT NOT NULL,
    checked_at DATETIME NOT NULL,
    INDEX ix_mh_model (model_id)
);

CREATE TABLE IF NOT EXISTS weather_regimes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    location_id VARCHAR(64) NOT NULL,
    valid_time DATETIME NOT NULL,
    current_regime VARCHAR(32) NOT NULL,
    previous_regime VARCHAR(32),
    cluster_id INT,
    features JSON,
    INDEX ix_wr_loc (location_id),
    INDEX ix_wr_time (valid_time)
);

CREATE TABLE IF NOT EXISTS regime_transitions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    location_id VARCHAR(64) NOT NULL,
    valid_time DATETIME NOT NULL,
    from_regime VARCHAR(32) NOT NULL,
    to_regime VARCHAR(32) NOT NULL,
    transition_probability FLOAT NOT NULL,
    transition_confidence FLOAT NOT NULL,
    INDEX ix_rt_loc (location_id)
);

CREATE TABLE IF NOT EXISTS dynamic_weights (
    id INT PRIMARY KEY AUTO_INCREMENT,
    forecast_id VARCHAR(64) NOT NULL,
    location_id VARCHAR(64) NOT NULL,
    variable VARCHAR(32) NOT NULL,
    lead_time_hours INT NOT NULL,
    weights JSON NOT NULL,
    strategy VARCHAR(32) NOT NULL,
    regime VARCHAR(32) NOT NULL,
    INDEX ix_dw_fid (forecast_id),
    INDEX ix_dw_loc (location_id),
    INDEX ix_dw_var (variable)
);

CREATE TABLE IF NOT EXISTS trust_weights (
    id INT PRIMARY KEY AUTO_INCREMENT,
    forecast_id VARCHAR(64) NOT NULL,
    location_id VARCHAR(64) NOT NULL,
    variable VARCHAR(32) NOT NULL,
    lead_time_hours INT NOT NULL,
    model_name VARCHAR(64) NOT NULL,
    weight FLOAT NOT NULL,
    strategy VARCHAR(32) DEFAULT 'real_IMD',
    computed_at DATETIME NOT NULL,
    INDEX ix_tw_fid (forecast_id),
    INDEX ix_tw_loc (location_id),
    INDEX ix_tw_var (variable),
    INDEX ix_tw_model (model_name)
);

CREATE TABLE IF NOT EXISTS blended_forecasts (
    id VARCHAR(64) PRIMARY KEY,
    location_id VARCHAR(64) NOT NULL,
    variable VARCHAR(32) NOT NULL,
    lead_time_hours INT NOT NULL,
    valid_time DATETIME NOT NULL,
    initialization_time DATETIME NOT NULL,
    value FLOAT NOT NULL,
    units VARCHAR(32) NOT NULL,
    dominant_model VARCHAR(64) NOT NULL,
    data_mode VARCHAR(32) DEFAULT 'demonstration',
    INDEX ix_bf_loc (location_id),
    INDEX ix_bf_var (variable),
    INDEX ix_bf_lt (lead_time_hours),
    INDEX ix_bf_valid (valid_time)
);

CREATE TABLE IF NOT EXISTS uncertainty_metrics (
    id INT PRIMARY KEY AUTO_INCREMENT,
    forecast_id VARCHAR(64) NOT NULL,
    ensemble_spread FLOAT NOT NULL,
    inter_model_spread FLOAT NOT NULL,
    interval_low FLOAT NOT NULL,
    interval_high FLOAT NOT NULL,
    confidence VARCHAR(16) NOT NULL,
    uncertainty_score FLOAT NOT NULL,
    disagreement_score FLOAT NOT NULL,
    disagreement_label VARCHAR(16) NOT NULL,
    frs FLOAT NOT NULL,
    frs_label VARCHAR(32) NOT NULL,
    frs_components JSON NOT NULL,
    failure_risk VARCHAR(16) NOT NULL,
    failure_explanation TEXT NOT NULL,
    INDEX ix_um_fid (forecast_id)
);

CREATE TABLE IF NOT EXISTS extreme_events (
    id VARCHAR(64) PRIMARY KEY,
    event_type VARCHAR(32) NOT NULL,
    location_id VARCHAR(64) NOT NULL,
    location_name VARCHAR(128) NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    probability FLOAT NOT NULL,
    intensity_low FLOAT NOT NULL,
    intensity_high FLOAT NOT NULL,
    confidence VARCHAR(16) NOT NULL,
    affected_grid_area FLOAT NOT NULL,
    primary_model VARCHAR(64) NOT NULL,
    supporting_models JSON NOT NULL,
    disagreement FLOAT NOT NULL,
    forecast_failure_risk VARCHAR(16) NOT NULL,
    variable VARCHAR(32) NOT NULL,
    lead_time_hours INT NOT NULL,
    payload JSON,
    INDEX ix_ee_type (event_type),
    INDEX ix_ee_loc (location_id)
);

CREATE TABLE IF NOT EXISTS verification_results (
    id INT PRIMARY KEY AUTO_INCREMENT,
    model_id VARCHAR(64) NOT NULL,
    variable VARCHAR(32) NOT NULL,
    region VARCHAR(64) DEFAULT 'ALL',
    lead_time_hours INT DEFAULT 0,
    regime VARCHAR(32) DEFAULT 'ALL',
    mae FLOAT NOT NULL,
    rmse FLOAT NOT NULL,
    bias FLOAT NOT NULL,
    crps FLOAT,
    brier FLOAT,
    csi FLOAT,
    f1 FLOAT,
    precision FLOAT,
    recall FLOAT,
    sample_count INT NOT NULL,
    data_mode VARCHAR(32) DEFAULT 'demonstration',
    note TEXT,
    INDEX ix_vr_model (model_id),
    INDEX ix_vr_var (variable)
);

CREATE TABLE IF NOT EXISTS forecast_explanations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    forecast_id VARCHAR(64) NOT NULL,
    summary TEXT NOT NULL,
    reasons JSON NOT NULL,
    shap_like JSON,
    INDEX ix_fe_fid (forecast_id)
);

CREATE TABLE IF NOT EXISTS forecast_provenance (
    id INT PRIMARY KEY AUTO_INCREMENT,
    forecast_id VARCHAR(64) NOT NULL UNIQUE,
    input_models JSON NOT NULL,
    timestamps JSON NOT NULL,
    model_versions JSON NOT NULL,
    weights JSON NOT NULL,
    calibration_version VARCHAR(32) DEFAULT 'bias-v0',
    blending_version VARCHAR(32) DEFAULT 'blend-v0.1',
    generated_at DATETIME NOT NULL,
    data_mode VARCHAR(32) DEFAULT 'demonstration',
    INDEX ix_fp_fid (forecast_id)
);

CREATE TABLE IF NOT EXISTS simulation_runs (
    id VARCHAR(64) PRIMARY KEY,
    request JSON NOT NULL,
    result JSON NOT NULL,
    created_at DATETIME NOT NULL,
    production_mutated BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS ml_models (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    version VARCHAR(32) NOT NULL,
    stage VARCHAR(32) DEFAULT 'Staging',
    blending_strategy VARCHAR(32) NOT NULL,
    metrics JSON,
    hyperparameters JSON,
    dataset_version VARCHAR(32) NOT NULL,
    feature_version VARCHAR(32) NOT NULL,
    mlflow_run_id VARCHAR(64),
    trained_at DATETIME NOT NULL,
    validation_status VARCHAR(32) DEFAULT 'benchmark-only'
);

CREATE TABLE IF NOT EXISTS training_runs (
    id VARCHAR(64) PRIMARY KEY,
    model_name VARCHAR(128) NOT NULL,
    mode VARCHAR(32) DEFAULT 'real_IMD',
    dataset_version VARCHAR(128) DEFAULT 'aeris_multimodel_ready',
    artifact_path VARCHAR(256) NOT NULL,
    training_timestamp DATETIME NOT NULL,
    init_dates JSON,
    lead_time_count INT DEFAULT 0,
    metrics JSON,
    status VARCHAR(32) DEFAULT 'SUCCESS'
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INT PRIMARY KEY AUTO_INCREMENT,
    event_type VARCHAR(64) NOT NULL,
    message TEXT NOT NULL,
    details JSON,
    created_at DATETIME NOT NULL,
    INDEX ix_al_type (event_type)
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id VARCHAR(64) PRIMARY KEY,
    job_name VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    started_at DATETIME NOT NULL,
    finished_at DATETIME,
    detail TEXT DEFAULT '',
    INDEX ix_pr_job (job_name)
);

CREATE TABLE IF NOT EXISTS alerts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    level VARCHAR(16) NOT NULL,
    message TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    acknowledged BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS system_metrics (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(64) NOT NULL,
    value FLOAT NOT NULL,
    captured_at DATETIME NOT NULL,
    INDEX ix_sm_name (name)
);

SHOW TABLES;
