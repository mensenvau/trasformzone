import yaml
import shutil
import argparse
from google import genai
from pathlib import Path
from datetime import datetime
from config.settings import get_settings
from utils.data_reader import DataReader

def prepare_prompt(config: dict, reader: DataReader, guid: str, sub_id: str, max_examples: int) -> tuple:
    blob_files = reader.list_files(guid, sub_id)
    if not blob_files:
        raise FileNotFoundError(f"No files found in raw/{guid}/{sub_id}/")
    
    examples = blob_files[:max_examples]
    print(f"Found {len(blob_files)} files, using {len(examples)} examples:")
    
    sample_sections = []
    for i, blob_path in enumerate(examples):
        info = reader.get_blob_info(blob_path)
        print(f"  [{i+1}] {Path(blob_path).name} ({info['size']:,} bytes)")
        preview = reader.read_preview(blob_path, rows=50)
        sample_sections.append(f"--- Example File {i+1}: {Path(blob_path).name} ---\n{preview}")
    
    with open(Path("tools/prompt/system_01.md"), 'r', encoding='utf-8') as f:
        template = f.read()
    
    prompt = template.replace("{config_yaml}", yaml.dump(config, default_flow_style=False)).replace("{extra_prompt}", config.get('prompt', '')).replace("{sample_csv}", "\n\n".join(sample_sections))
    return examples, prompt

def save_parser(code: str, output_path: Path, history_dir: Path, model: str, examples: list, guid: str, sub_id: str, usage=None) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_path.exists():
        history_dir.mkdir(exist_ok=True)
        shutil.copy2(output_path, history_dir / f"parser_{timestamp}.py")
        print(f"Previous parser backed up: history/parser_{timestamp}.py")
    
    meta = [f"# Generated: {timestamp}", f"# Model: {model}"]
    if usage:
        meta.append(f"# Tokens: prompt={usage.prompt_token_count}, output={usage.candidates_token_count}, total={usage.total_token_count}")
        print(f"Tokens - Prompt: {usage.prompt_token_count}, Output: {usage.candidates_token_count}, Total: {usage.total_token_count}")
    meta.extend([f"# Examples: {', '.join(Path(b).name for b in examples)}", f"# GUID: {guid} / {sub_id}"])
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(meta) + "\n\n" + code)
    print(f"Parser generated: {output_path}")

def generate(domain: str, report_type: str, guid: str, sub_id: str, max_examples: int = 2) -> None:
    parser_dir = Path(f"parsers/{domain}/{report_type}")
    config_path = parser_dir / "current" / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"config.yaml not found at {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    reader = DataReader()
    examples, prompt = prepare_prompt(config, reader, guid, sub_id, max_examples)
    
    settings = get_settings()
    print(f"\nCalling Gemini API ({settings.GEMINI_MODEL_NAME})...")
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    res = client.models.generate_content(model=settings.GEMINI_MODEL_NAME, contents=prompt)
    
    code = res.text.replace("```python", "").replace("```", "").strip()
    usage = res.usage_metadata if hasattr(res, 'usage_metadata') else None
    
    save_parser(code, parser_dir / "current" / "parser.py", parser_dir / "history", settings.GEMINI_MODEL_NAME, examples, guid, sub_id, usage)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--guid", required=True)
    parser.add_argument("--sub-id", required=True)
    parser.add_argument("--max-examples", type=int, default=2)
    args = parser.parse_args()
    generate(args.domain, args.report, args.guid, args.sub_id, args.max_examples)

if __name__ == "__main__":
    main()
