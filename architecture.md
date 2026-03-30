# TransformZone — Master Architecture Blueprint

## 1. System Overview
TransformZone is an AI-accelerated, metadata-driven ETL (Extract, Transform, Load) platform designed to parse unstructured or semi-structured Excel/CSV reports into normalized, relational database tables. 
It uses an Azure Blob-native approach for storage, SQL Server for data warehousing, and Google Gemini AI for accelerating parser code generation.

## 2. Core Technologies
- **Language**: Python 3.x
- **Storage**: Azure Blob Storage (Azurite for local dev)
- **Database**: Microsoft SQL Server (target tables, metadata registry, logs)
- **AI Integration**: Google GenAI SDK (Gemini 2.5/3.1)
- **Data Manipulation**: Pandas, SQLAlchemy
- **Containerization (Optional)**: Docker (for deployment)

## 3. Storage Layout & Path Convention

All source data resides in Azure Blob Storage following a strict multi-tenant execution convention:
```text
Azure Blob Container (transformzone-dev):
  raw/
    {guid}/             <-- Main batch or Customer Tenant ID
      {sub_id}/         <-- Sub-batch, message id, upload session
        Report1.xlsx
        Report2.csv
```

## 4. Database Architecture & Schemas

The database uses multiple schemas to organize data stages:
- `dbo`: Metadata (file registry, processing logs)
- `stg`: Temporary staging area during upsert operations
- `bronze`: Raw parsed data (target tables for parsed data)

### 4.1. `dbo.file_registry`
Maps a glob-style filename pattern (`file_wildcard`) to its specific parser module and target database table.

| Column | Type | Description |
|--------|------|-------------|
| **id** | INT (PK) | Auto-incrementing primary key |
| **guid** | VARCHAR | Identifier bound to the mapping (if scoped) |
| **file_wildcard** | VARCHAR | Glob pattern (e.g., `ResAnalytics_*x*.xlsx`) |
| **domain** | VARCHAR | Folder domain (e.g., `yardi_multifamily`) |
| **report_type** | VARCHAR | Report subfolder (e.g., `rent_roll`) |
| **target_table** | VARCHAR | Target schema and table (e.g., `bronze.yardi_rent_roll`) |
| **insert_mode** | VARCHAR | Writing behavior: `append`, `upsert`, or `replace` |
| **key_columns** | VARCHAR | Comma-separated keys for the upsert/merge logic |
| **description**| VARCHAR | Human-readable explanation of the parser |
| **is_active** | BIT | Soft-delete / enable toggle (1=active) |

### 4.2. `dbo.processing_log`
Tracks the execution lifecycle of every single file processed by the pipeline.

| Column | Type | Description |
|--------|------|-------------|
| **id** | INT (PK) | Auto-incrementing primary key |
| **guid** | VARCHAR | Pipeline execution GUID context |
| **sub_id** | VARCHAR | Pipeline execution Sub-ID context |
| **file_wildcard** | VARCHAR | Matched pattern from the registry |
| **filename** | VARCHAR | Actual source filename processed |
| **target_table** | VARCHAR | Table data was written into |
| **status** | VARCHAR | Result: `success`, `skipped`, or `failed` |
| **rows_inserted**| INT | Number of payload rows written/upserted |
| **error_message**| VARCHAR | Stacktrace or exception message if failed |
| **processed_at** | DATETIME | Execution timestamp |

### 4.3. Target Execution (`bronze` & `stg`)
- **Staging tables (`stg.*`)**: Created dynamically on the fly to hold Pandas DataFrame outputs.
- **Merge/Upsert Logic**: When `insert_mode="upsert"`, the code performs:
  1. Write to temporary `stg.{table_name}`
  2. Perform `DELETE` from target where keys match staging data.
  3. Perform `INSERT` from `stg` to target.
  4. Perform `DROP` on the temporary `stg` table.

## 5. Directory Structure & Module Responsibilities

| Path | Purpose / Responsibility |
|------|--------------------------|
| `config/` | Environment abstractions (`settings.py`), database connection strings (`database.py`). |
| `utils/data_reader.py` | Interfaces with Azure Blob Storage. Lists files based on guid/sub_id, downloads to local temp, extracts metadata. |
| `utils/data_writer.py` | Interfaces with SQL Server. Creates `stg`/`bronze` schemas automatically. Handles Pandas `append`, `replace`, and `DELETE+INSERT` upsert patterns. Logs results. |
| `utils/registry.py` | Reads available parsers from disk, connects to DB `dbo.file_registry` to look up the exact parser to invoke based on file pattern. |
| `utils/logger.py` | Uses `structlog` for structured, formatted JSON/text console logging while suppressing noisy 3rd party SDK logs. |
| `orchestration/` | `execute_pipeline.py` integrates reader, registry, parser, and writer execution into a single unified CLI flow context. |
| `parsers/{domain}/{report}/`| Contains `current/` and `history/` folders. Holds `parser.py` (the actual Python function transforming Pandas) and `config.yaml` defining columns. |
| `tools/ai/` | Contains `generate_parser.py`, an automation tool that grabs files from Blob, reads `config.yaml`, and prompts Gemini AI to auto-generate the `parser.py` code. |

## 6. Pipeline Execution Flow

When triggered via CLI (`python -m orchestration.execute_pipeline --guid ... --sub-id ...`):
1. **Initialize**: Pipeline executor spins up `DataReader`, `DataWriter`, and `ParserRegistry`.
2. **Scan**: Lists all files physically present in Blob at `raw/{guid}/{sub_id}/`.
3. **Loop**: For each file:
   1. **Lookup**: Match filename against `dbo.file_registry` (`fnmatch`). If no match, log `skipped`.
   2. **Download**: Pull Blob content to local temp file.
   3. **Parse**: Execute the exact `parse(filepath)` function matched. Returns a clean dataframe.
   4. **Enrich**: Inject metadata columns (`_source_file`, `_guid`, `_sub_id`, `_parsed_at`).
   5. **Store**: Writer executes `append/upsert`. 
   6. **Log**: Writer inserts success/failure stats to `dbo.processing_log`.
4. **Cleanup**: Temp files removed from disk. Returns final metrics.

## 7. AI Code Generation Workflow (Developer Mode)

The system allows fast scale-up of new parsers. No manual Pandas coding needed initially:
1. Standardize goal: Define `parsers/{domain}/{report}/current/config.yaml` with the required resulting table columns and data types.
2. Provide context: Upload 1-2 sample reports to `raw/test-guid/test-message/`.
3. Run Generator: `python tools/ai/generate_parser.py --domain X --report Y --guid test-guid --sub-id test-message`
4. The AI tool pulls the top 50 lines of Blob samples, combines it with the YAML config and `system_01.md` prompt, and calls the Google Gemini API.
5. AI replies with a raw python script. The script is auto-saved as `parser.py` (and the previous version is backed up in `history/`).
