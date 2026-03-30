---
trigger: always_on
---

# TransformZone - AI Development Rules

When creating code for TransformZone using AI, follow these strict rules:

### Architecture Context
1. **No AI in Runtime**: The executed pipeline logic (`main_pipeline.py`, parsers, utility functions) must not contain any AI logic, LLM calls, or non-deterministic mapping functions. Everything parsed must be explicitly coded.
2. **AI as an Accelerator**: Use the AI tools (like `tools/ai/generate_parser.py`) only to read example files and generate the boilerplate `parser.py` and `config.yaml`.
3. **One Parser per Report**: Each report format has a dedicated parser in `parsers/{domain}/{report_type}/parser.py` and a config in `config.yaml`.

### Coding Style & Patterns
4. **English Commits & Code**: Ensure all AI-generated code has English comments, variables, and documentation. Git commits must also be in English.
5. **Clean Code & Less Comments**: Write clear, minimal code. Do NOT add unnecessary line-by-line comments. Use comments strictly for module-level docstrings, class docstrings, or complex logic.
6. **Fewer Print Statements**: Do not use arbitrary or excessive `print()` statements. Only output necessary information needed for logging. Use `utils.logger` for required state changes.
7. **No Internal Underscores**: Do not use leading underscores `_` for function or method names (e.g. use `read_csv` instead of `_read_csv`).
8. **Short Docstrings**: Keep method docstrings or commits incredibly concise and single-line whenever possible. No need for long explanations on simple functions.
9. **Consistent Formatting & Single-line arguments**: Keep parameter formatting consistent. Keep function signatures and logic single-line wherever feasible to maintain visual cleanliness.
10. **Import Sorting**: All Python files must sort their imports dynamically by group (first `import X`, then `from X import Y`) and then sort them strictly by character length (shortest to longest) within each group.
