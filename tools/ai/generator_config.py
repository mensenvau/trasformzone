import yaml
import shutil
import argparse
from pathlib import Path
from google import genai
from datetime import datetime
from config.settings import get_settings
from utils.build_logger import log_build
from utils.data_reader import DataReader

def generate(domain: str, report_type: str, guid: str, sub_id: str, file_wildcard: str = None, prompt_ver: str = "01") -> None:
    """Generate YAML config for a report layout via Gemini."""
    root = Path(__file__).parent.parent.parent
    parser_dir = root / "parsers" / domain / report_type / "current"
    parser_dir.mkdir(parents=True, exist_ok=True)

    reader = DataReader()
    blob_files = reader.list_files(guid, sub_id, file_wildcard=file_wildcard)
    if not blob_files:
        raise FileNotFoundError(f"No files matching '{file_wildcard}' in raw/{guid}/{sub_id}/")

    preview = reader.read_preview(blob_files[0], rows=50)
    prompt_path = root / "tools" / "prompt" / f"system_config_{prompt_ver}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt template missing: system_config_{prompt_ver}.md")

    template = open(prompt_path, encoding='utf-8').read()
    settings = get_settings()
    res = genai.Client(api_key=settings.GOOGLE_API_KEY).models.generate_content(
        model=settings.GEMINI_MODEL_NAME, contents=template.replace("{sample_data}", preview)
    )

    config_yaml = res.text.replace("```yaml", "").replace("```", "").strip()
    config_path = parser_dir / "config.yaml"

    if config_path.exists():
        history_dir = root / "parsers" / domain / report_type / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config_path, history_dir / f"config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")

    open(config_path, 'w', encoding='utf-8').write(config_yaml)
    log_build("config", domain, report_type, settings.GEMINI_MODEL_NAME, getattr(res, 'usage_metadata', None))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--guid", required=True)
    parser.add_argument("--sub_id", required=True)
    parser.add_argument("--file_wildcard", default=None)
    parser.add_argument("--prompt", default="01")
    args = parser.parse_args()
    generate(args.domain, args.report, args.guid, args.sub_id, args.file_wildcard, args.prompt)

if __name__ == "__main__":
    main()
