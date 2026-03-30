-- ============================================================
-- TransformZone Database Setup
-- ============================================================

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'stg')
    EXEC('CREATE SCHEMA stg');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'bronze')
    EXEC('CREATE SCHEMA bronze');
GO
-- 1. File Registry: maps guid + file_wildcard to parser domain/report
CREATE TABLE dbo.file_registry (
    id INT IDENTITY(1,1) PRIMARY KEY,
    guid VARCHAR(255) NOT NULL DEFAULT NEWID(),
    file_wildcard VARCHAR(200) NOT NULL,
    domain VARCHAR(100) NOT NULL,
    report_type VARCHAR(100) NOT NULL,
    target_table VARCHAR(200) NOT NULL,
    insert_mode VARCHAR(50) NOT NULL DEFAULT 'append',
    key_columns VARCHAR(500),
    description VARCHAR(500),
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT UQ_guid UNIQUE (guid)
);
GO

-- 2. Processing Log: tracks every file processed
CREATE TABLE dbo.processing_log (
    id INT IDENTITY(1,1) PRIMARY KEY,
    guid VARCHAR(255) NOT NULL,
    sub_id VARCHAR(255) NOT NULL,
    file_wildcard VARCHAR(200),
    filename VARCHAR(500) NOT NULL,
    domain VARCHAR(100),
    report_type VARCHAR(100),
    target_table VARCHAR(200),
    status VARCHAR(50) NOT NULL,
    rows_inserted INT DEFAULT 0,
    error_message VARCHAR(MAX),
    processed_at DATETIME NOT NULL DEFAULT GETDATE()
);
GO

-- Sample: register a file wildcard pattern for a specific guid
INSERT INTO dbo.file_registry (file_wildcard, domain, report_type, target_table, insert_mode, key_columns, description)
VALUES (
    'ResAnalytics_Rent_Roll_x*.xlsx',
    'yardi_multifamily',
    'rent_roll',
    'bronze.yardi_rent_roll',
    'upsert',
    'Property_ID,Unit,As_Of_Date',
    'Yardi Multifamily Rent Roll export'
);
GO
