-- TransformZone Database Setup
-- Run in MS SQL Server (idempotent - safe to re-run)

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'stg')
    EXEC('CREATE SCHEMA stg');

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'bronze')
    EXEC('CREATE SCHEMA bronze');

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'config')
    EXEC('CREATE SCHEMA config');

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'file_registry' AND schema_id = SCHEMA_ID('config'))
    CREATE TABLE config.file_registry (
        id            INT          IDENTITY(1,1) PRIMARY KEY,
        guid          VARCHAR(255) NOT NULL DEFAULT NEWID(),
        file_wildcard VARCHAR(200) NOT NULL,
        domain        VARCHAR(100) NOT NULL,
        report_type   VARCHAR(100) NOT NULL,
        target_table  VARCHAR(200) NOT NULL,
        insert_mode   VARCHAR(50)  NOT NULL DEFAULT 'append',
        key_columns   VARCHAR(500),
        description   VARCHAR(500),
        is_active     BIT          NOT NULL DEFAULT 1,
        created_at    DATETIME     NOT NULL DEFAULT GETDATE(),
        updated_at    DATETIME     NOT NULL DEFAULT GETDATE(),
        CONSTRAINT UQ_file_registry_guid UNIQUE (guid)
    );

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'processing_log' AND schema_id = SCHEMA_ID('config'))
    CREATE TABLE config.processing_log (
        id            INT          IDENTITY(1,1) PRIMARY KEY,
        guid          VARCHAR(255) NOT NULL,
        sub_id        VARCHAR(255) NOT NULL,
        file_wildcard VARCHAR(200),
        filename      VARCHAR(500) NOT NULL,
        domain        VARCHAR(100),
        report_type   VARCHAR(100),
        target_table  VARCHAR(200),
        status        VARCHAR(50)  NOT NULL,
        rows_inserted INT          DEFAULT 0,
        error_message VARCHAR(MAX),
        processed_at  DATETIME     NOT NULL DEFAULT GETDATE()
    );

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'build_history' AND schema_id = SCHEMA_ID('config'))
    CREATE TABLE config.build_history (
        id         INT           IDENTITY(1,1) PRIMARY KEY,
        timestamp  DATETIME      NOT NULL DEFAULT GETDATE(),
        type       VARCHAR(50),
        domain     VARCHAR(100),
        report     VARCHAR(100),
        model      VARCHAR(100),
        tokens_in  INT,
        tokens_out INT,
        cost       DECIMAL(18,6),
        status     VARCHAR(20)   DEFAULT 'success'
    );

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_build_history_ts')
    CREATE INDEX idx_build_history_ts ON config.build_history(timestamp);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_processing_log_ts')
    CREATE INDEX idx_processing_log_ts ON config.processing_log(processed_at);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_file_registry_lookup')
    CREATE INDEX idx_file_registry_lookup ON config.file_registry(guid, is_active);
