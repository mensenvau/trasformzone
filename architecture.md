# TransformZone Architecture

## Data Flow

```
Email/Upload → Azure Blob (raw/{guid}/{sub_id}/) → Pipeline → Azure SQL Server
```

## Blob Storage Layout

```
Azure Blob Container (transformzone-storage):
  raw/
    {guid}/
      {sub_id}/
        ResAnalytics_Rent_Roll_x28.xlsx
        ResAnalytics_Rent_Roll_x45.xlsx
        SomeOtherReport.csv
```

- `guid` — top-level batch/customer identifier
- `sub_id` — sub-level identifier (message_id, email hash, upload batch, etc.)

Files remain in blob after processing. Status is tracked in `dbo.processing_log`.

## Pipeline Execution Flow

```
1. Pipeline receives --guid and --sub-id
2. DataReader.list_files(guid, sub_id) scans raw/{guid}/{sub_id}/ in blob
3. For each file:
   a. ParserRegistry.lookup_file_wildcard(filename) matches against dbo.file_registry using fnmatch
   b. File is downloaded to temp
   c. parse(file_path) from parsers/{domain}/{report_type}/parser.py returns DataFrame
   d. Metadata columns added: _source_file, _guid, _sub_id, _file_wildcard, _parsed_at
   e. DataWriter.ensure_table_exists() auto-creates target table if needed
   f. DataWriter.write() inserts data (append/upsert)
   g. DataWriter.log_processing() writes result to dbo.processing_log
   h. Temp file cleaned up
```

## Database Tables

### dbo.file_registry
Maps file_wildcard patterns to parsers via fnmatch glob matching.

| Column | Type | Purpose |
|--------|------|---------|
| file_wildcard | VARCHAR(200) | Glob pattern (e.g., `ResAnalytics_Rent_Roll_x*.xlsx`) |
| domain | VARCHAR(100) | Parser domain folder |
| report_type | VARCHAR(100) | Parser report folder |
| target_table | VARCHAR(200) | SQL target (e.g., `bronze.yardi_rent_roll`) |
| insert_mode | VARCHAR(50) | append / upsert / replace |
| key_columns | VARCHAR(500) | Comma-separated keys for upsert |
| is_active | BIT | Enable/disable pattern |

### dbo.processing_log
Audit trail for every file processed.

| Column | Type | Purpose |
|--------|------|---------|
| guid | VARCHAR(255) | Batch identifier |
| sub_id | VARCHAR(255) | Sub-level identifier |
| file_wildcard | VARCHAR(200) | Matched pattern |
| filename | VARCHAR(500) | Original filename |
| domain | VARCHAR(100) | Parser domain used |
| report_type | VARCHAR(100) | Parser report used |
| target_table | VARCHAR(200) | SQL target written to |
| status | VARCHAR(50) | success / failed / skipped |
| rows_inserted | INT | Rows written |
| error_message | VARCHAR(MAX) | Error details if failed |
| processed_at | DATETIME | Timestamp |

## AI Parser Generation (Development Only)

```
1. Upload example files to blob: raw/{guid}/{sub_id}/
2. Write config.yaml with column specs and prompt
3. Run: python tools/ai/generate_parser.py --domain X --report Y --guid G --sub-id S
4. Tool reads examples from blob, generates prompt with first file preview
5. Send generated_prompt.txt to AI model
6. Save AI output as parser.py
7. Register file_wildcard in dbo.file_registry
```

## Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `registry.py` | Discover parse() functions + lookup file_wildcard from DB |
| `data_reader.py` | Azure Blob list/download/preview |
| `data_writer.py` | SQL Server write (append/upsert) + auto-create table + processing log |
| `execute_pipeline.py` | Orchestrates: reader → registry → parser → writer |
| `generate_parser.py` | Reads blob examples + config.yaml → builds AI prompt |
