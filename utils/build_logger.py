from utils.sql import execute_all

def log_build(type, domain, report, model, usage=None):
    t_in = usage.prompt_token_count if usage else 0
    t_out = usage.candidates_token_count if usage else 0
    execute_all(
        "INSERT INTO config.build_history (type, domain, report, model, tokens_in, tokens_out, cost, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (type, domain, report, model, t_in, t_out, (t_in + t_out) * 0.000001, 'success')
    )

def get_build_history(limit: int = 50) -> list:
    try:
        return execute_all("SELECT TOP (?) * FROM config.build_history ORDER BY timestamp DESC", (limit,))
    except:
        return []
