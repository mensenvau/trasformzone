# TransformZone

Data pipeline that parses Excel/CSV files from CRM/ERP systems (Yardi, Entrata, RealPage, etc.) and writes normalized data into Azure SQL Server.

## Principles
- **Simple Python** — No AI at runtime
- **One parser per report type** — Each file_wildcard maps to a `parse()` function
- **AI for development only** — AI generates parser code from config.yaml + example files
- **Blob Storage only** — All files live in Azure Blob under `raw/{guid}/{sub_id}/`

## How It Works

```
1. Files arrive in Azure Blob Storage: raw/{guid}/{sub_id}/
2. Pipeline receives --guid and --sub-id
3. For each file in raw/{guid}/{sub_id}/:
   a. Match filename against file_wildcard in dbo.file_registry (fnmatch)
   b. Load parse() function from parsers/{domain}/{report_type}/parser.py
   c. Download blob to temp, parse → DataFrame
   d. Auto-create target table if first run
   e. Write to target_table (append/upsert)
   f. Log result to dbo.processing_log
   g. Cleanup temp file
```

## Quick Start

```bash
# 1. Setup
git clone <repo>
cd transformzone
python -m venv .venv
venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env

# 3. Create database tables
# Run tools/scripts/create_tables.sql against your Azure SQL Server

# 4. Register file wildcard in dbo.file_registry
# INSERT INTO dbo.file_registry (file_wildcard, domain, report_type, target_table, insert_mode, key_columns)
# VALUES ('ResAnalytics_Rent_Roll_x*.xlsx', 'yardi_multifamily', 'rent_roll', 'bronze.yardi_rent_roll', 'upsert', 'Property_ID,Unit,As_Of_Date')

# 5. Generate parser (AI-assisted, reads examples from blob)
python -m tools.ai.generate_parser --domain yardi_multifamily --report rent_roll --guid A8BAFAA9-73A6-4BEE-ACDA-12DD3CAAA506  --sub-id test_message_id

# 6. Run pipeline
python -m orchestration.execute_pipeline --guid A8BAFAA9-73A6-4BEE-ACDA-12DD3CAAA506 --sub-id test_message_id
```

## Adding a New Parser

1. Create folder: `parsers/{domain}/{report_type}/`
2. Write `config.yaml` with column definitions, file_wildcard, and prompt instructions
3. Upload 2-3 example files to blob: `raw/{guid}/{sub_id}/`
4. Run: `python tools/ai/generate_parser.py --domain X --report Y --guid G --sub-id S`
5. AI generates `parser.py` automatically via Gemini API
6. Register `file_wildcard` in `dbo.file_registry`

## Project Structure

```
transformzone/
├── orchestration/
│   └── execute_pipeline.py     # Main pipeline (--guid --sub-id)
├── parsers/
│   └── {domain}/{report_type}/
│       ├── current/
│       │   ├── config.yaml      # AI-tool config (columns, prompt)
│       │   └── parser.py        # Active AI-generated parse() function
│       └── history/             # Timestamped backups of previous parsers
├── utils/
│   ├── registry.py              # Parser discovery + file_wildcard lookup from DB
│   ├── data_reader.py           # Azure Blob read/download
│   ├── data_writer.py           # SQL Server write + processing log
│   └── logger.py                # Structured logging (structlog)
├── config/
│   ├── settings.py              # Environment config (pydantic-settings)
│   └── database.py              # SQL Server connection string builder
├── tools/
│   ├── ai/generate_parser.py   # AI prompt generator (reads examples from blob)
│   ├── prompt/system_01.md     # System prompt template
│   └── scripts/create_tables.sql
└── doc/
    └── architecture.md
```

---

## Local Development Setup

### 1. Install Azurite (Azure Blob Emulator)

```bash
npm install -g azurite
azurite --silent --location ./azurite-data --debug ./azurite-debug.log
```

Azurite runs on `http://127.0.0.1:10000` (Blob), `10001` (Queue), `10002` (Table).

### 2. Install SQL Server (Docker)

```bash
docker run -e "ACCEPT_EULA=Y" -e "MSSQL_SA_PASSWORD=YourStrong!Passw0rd" -p 1433:1433 -d mcr.microsoft.com/mssql/server:2022-latest
```

### 3. Create Database and Tables

```bash
# Connect via sqlcmd or Azure Data Studio
sqlcmd -S localhost -U sa -P "YourStrong!Passw0rd" -Q "CREATE DATABASE transformzone_dev"
sqlcmd -S localhost -U sa -P "YourStrong!Passw0rd" -d transformzone_dev -i tools/scripts/create_tables.sql
```

### 4. Create Blob Container and Upload Test Files

```bash
# Install Azure CLI or use Azure Storage Explorer
az storage container create --name transformzone-dev --connection-string "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"

# Upload test files
az storage blob upload --container-name transformzone-dev --name "raw/test-guid/msg-001/ResAnalytics_Rent_Roll_x28.xlsx" --file ./sample.xlsx --connection-string "..."
```

### 5. Configure .env

```bash
cp .env.example .env
# .env.example is pre-configured for local development (Azurite + localhost SQL Server)
```

### 6. Run

```bash
python -m orchestration.execute_pipeline --guid test-guid --sub-id msg-001
```