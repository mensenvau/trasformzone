# Config Generation Prompt

You are an expert data analyst and engineer. Your task is to analyze raw file samples (Excel/CSV) and generate a `config.yaml` that can be used to build a robust parser.

## Sample Data (first 50 rows)

{sample_data}

---

## Your Task

Analyze the sample data and identify the core structure of the report. Generate a `config.yaml` with the following schema:

```yaml
domain: <domain_name>
report_type: <report_name>
unique_identifier: <primary_column_to_identify_a_row>

# Column definitions
columns:
  - name: <target_column_name>
    source: <original_column_name_in_file_or_regex>
    type: <string|number|date>
    description: <summary_of_logic_like "parse from header" or "Classification title">
    date_format: <optional_strftime_format_if_date>

# Extraction settings
header_scan_rows: 15
stop_conditions:
  - <regex_to_stop_parsing_e.g_Total>
skip_conditions:
  - <regex_to_skip_rows_e.g_Subtotal>

# Extra prompt for the parser generator
prompt: |
  <Any specific instructions for the parser generator, e.g. "Handle merged cells in column A", "Forward fill section titles from column B">
```

## Analyis Rules

1. **Header Detection**: Find the row that contains the actual column headers. List them in the `source` field.
2. **Type Inference**: Detect if a column is a string, number, or date.
3. **Data Cleaning**: Identify if there are "Total" or "Subtotal" rows at the end or middle of the file to add to `stop_conditions` or `skip_conditions`.
4. **Header Metadata**: If specific values (like "Property Name", "Report Date") are in the top rows (above the main header), define them in `columns` with a description "parse from header".
5. **Section Titles**: If the file is structured with grouping titles (titles that appear on their own row above a group of rows), define a column for them and describe how to extract them.
6. **Unique Identifier**: Choose a column that must be present for a row to be valid (e.g., "Account Number", "Unit").
7. **Robustness**: If column names might change, use regex-like strings for `source`.

## STRICT Output Rules
1. Return ONLY the valid YAML content.
2. Do NOT use markdown fences.
3. Do NOT add any explanations or comments outside the YAML.
