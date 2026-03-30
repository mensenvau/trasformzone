# Parser Generation Prompt

You are an expert Python data engineer. Generate a robust `parse(file_path)` function that transforms raw Excel/CSV files into a clean pandas DataFrame.

## Configuration (YAML)

```yaml
{config_yaml}
```

## Extra Instructions

{extra_prompt}

## Sample Data (first 50 rows from each example file)

{sample_csv}

---

## Task

Write a single Python function `def parse(file_path):` that reads the file and returns a clean `pd.DataFrame`.

## STRICT Rules

### Output Format
1. Return ONLY valid Python code. No markdown fences, no explanations, no comments except module docstring.
2. Function signature MUST be `def parse(file_path):` — no class, no extra arguments.
3. Sort imports: first `import X` sorted by length, then `from X import Y` sorted by length.
4. Keep code clean: no line-by-line comments, no print statements, single-line function signatures.

### Column Handling
5. Every column defined in the YAML MUST exist in the final DataFrame. If missing in source, fill with `None`.
6. Return ONLY the columns listed in config, in the exact order defined. No extra columns.
7. Apply proper type casting:
   - `string` → `.astype(str)`, replace `"nan"` with `None`
   - `number` → `pd.to_numeric(errors='coerce')`
   - `date` → `pd.to_datetime(errors='coerce')`, respect `date_format` if specified
8. Strip whitespace from all string columns.

### Header & Metadata Extraction
9. If a column description says "parse from header", extract the value from the top rows (scan first 10 rows) and broadcast it to ALL data rows.
10. Use regex for header extraction — be flexible with spacing, casing, and delimiters.
11. If header extraction fails, set the value to `None` — NEVER crash.

### Section / Category Titles
12. If a column description mentions "Classification", "Category", or "Section Title", detect standalone title rows (rows with very few populated cells) and map that title to all subsequent data rows until the next title appears.

### Data Cleaning
13. Detect the header row dynamically — scan first 15 rows looking for the row that best matches expected column names. Do NOT hardcode a row number.
14. If `STOP` conditions are described, implement them: stop reading when a matching row is found.
15. If `SKIP` conditions are described, filter out matching rows (totals, subtotals, summary rows).
16. Remove rows where the primary identifier column (see `unique_identifier` in config) is null or empty.
17. Drop fully empty rows.

### Robustness & Edge Cases
18. Handle merged cells: when reading Excel, merged cells may produce NaN in subsequent rows — forward-fill if it makes sense for the column type.
19. Handle multiple sheets: default to first sheet unless config specifies otherwise.
20. Handle encoding issues for CSV: try `utf-8` first, fallback to `latin-1`.
21. Never crash on malformed data — wrap risky operations in try/except and degrade gracefully (fill with None).
22. Column name matching should be case-insensitive and whitespace-tolerant. Map source columns to target columns using normalized comparison.
23. If the file has inconsistent column counts across rows, handle it without crashing.
24. If date parsing fails for a specific format, try common alternatives: `%m/%d/%Y`, `%Y-%m-%d`, `%d/%m/%Y`, `%m/%Y`.
25. Multiple example files may be provided. Ensure the parse function handles variations between them.

### Final Output
26. Reset index before returning: `df.reset_index(drop=True)`.
27. The returned DataFrame must be ready for direct SQL insertion — no special objects, no nested data, no multi-index.
