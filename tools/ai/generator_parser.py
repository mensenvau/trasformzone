import yaml
import shutil
import argparse
from pathlib import Path
from google import genai
from datetime import datetime
from config.settings import get_settings
from utils.build_logger import log_build
from utils.data_reader import DataReader

def generate(domain: str, report_type: str, guid: str, sub_id: str, file_wildcard: str = None, max_examples: int = 2, prompt_ver: str = "01") -> None:
    """Generate parser.py for a report layout via Gemini."""
    root = Path(__file__).parent.parent.parent
    parser_dir = root / "parsers" / domain / report_type

    config_path = parser_dir / "current" / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Config missing at {config_path}")

    with open(config_path, encoding='utf-8') as f:
        config = yaml.safe_load(f)

    reader = DataReader()
    blob_files = reader.list_files(guid, sub_id, file_wildcard=file_wildcard)
    if not blob_files:
        raise FileNotFoundError(f"No files matching '{file_wildcard}' in raw/{guid}/{sub_id}/")

    examples = blob_files[:max_examples]
    samples = "\n\n".join([f"--- File {i+1}: {Path(b).name} ---\n{reader.read_preview(b, rows=50)}" for i, b in enumerate(examples)])

    prompt_path = root / "tools" / "prompt" / f"system_parser_{prompt_ver}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt template missing: system_parser_{prompt_ver}.md")

    template = open(prompt_path, encoding='utf-8').read()
    extra = config.get('prompt', '') or config.get('extra_prompt', '')
    prompt = template.replace("{config_yaml}", yaml.dump(config)).replace("{extra_prompt}", extra).replace("{sample_csv}", samples)

    settings = get_settings()
    res = genai.Client(api_key=settings.GOOGLE_API_KEY).models.generate_content(model=settings.GEMINI_MODEL_NAME, contents=prompt)
    usage = getattr(res, 'usage_metadata', None)

    code = res.text.replace("```python", "").replace("```", "").strip()
    output_path = parser_dir / "current" / "parser.py"
    history_dir = parser_dir / "history"

    if output_path.exists():
        history_dir.mkdir(exist_ok=True, parents=True)
        shutil.copy2(output_path, history_dir / f"parser_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    header = [f"# Build: {ts}", f"# Model: {settings.GEMINI_MODEL_NAME}", f"# Files: {', '.join(Path(b).name for b in examples)}"]
    open(output_path, 'w', encoding='utf-8').write("\n".join(header) + "\n\n" + code)
    log_build("parser", domain, report_type, settings.GEMINI_MODEL_NAME, usage)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--guid", required=True)
    parser.add_argument("--sub-id", required=True)
    parser.add_argument("--file_wildcard", default=None)
    parser.add_argument("--max-examples", type=int, default=2)
    parser.add_argument("--prompt", default="01")
    args = parser.parse_args()
    generate(args.domain, args.report, args.guid, args.sub_id, args.file_wildcard, args.max_examples, args.prompt)

if __name__ == "__main__":
    main()
