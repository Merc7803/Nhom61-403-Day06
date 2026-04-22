import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = ROOT / "chat_logs"
DEFAULT_PRICING_PATH = ROOT / "analytics" / "model_pricing_usd_per_1m_tokens.json"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_number(x: Any) -> float:
    try:
        v = float(x)
        if math.isfinite(v):
            return v
    except Exception:
        pass
    return 0.0


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


def _parse_usage(meta: dict) -> Usage | None:
    u = meta.get("openai_usage")
    if not isinstance(u, dict):
        return None
    pt = int(_safe_number(u.get("prompt_tokens")))
    ct = int(_safe_number(u.get("completion_tokens")))
    tt = int(_safe_number(u.get("total_tokens"))) or (pt + ct)
    if pt <= 0 and ct <= 0 and tt <= 0:
        return None
    return Usage(prompt_tokens=max(0, pt), completion_tokens=max(0, ct), total_tokens=max(0, tt))


def _price_for(model: str, pricing: dict) -> tuple[float, float]:
    row = pricing.get(model)
    if not isinstance(row, dict):
        row = pricing.get("default", {}) if isinstance(pricing.get("default"), dict) else {}
    return (_safe_number(row.get("input")), _safe_number(row.get("output")))


def _estimate_cost_usd(model: str, usage: Usage, pricing: dict) -> dict:
    p_in, p_out = _price_for(model, pricing)
    cost_in = (usage.prompt_tokens / 1_000_000.0) * p_in
    cost_out = (usage.completion_tokens / 1_000_000.0) * p_out
    return {
        "currency": "USD",
        "pricing_usd_per_1m_tokens": {"input": p_in, "output": p_out},
        "estimated_cost_usd": round(cost_in + cost_out, 6),
        "estimated_cost_usd_input": round(cost_in, 6),
        "estimated_cost_usd_output": round(cost_out, 6),
    }


def _count_tool_events(tool_events: Any) -> dict:
    out: dict[str, int] = {}
    if not isinstance(tool_events, list):
        return out
    for e in tool_events:
        if not isinstance(e, dict):
            continue
        k = str(e.get("kind") or "unknown")
        out[k] = out.get(k, 0) + 1
        name = e.get("name")
        if isinstance(name, str) and name:
            out[f"{k}:{name}"] = out.get(f"{k}:{name}", 0) + 1
    return out


def build_report(log_dir: Path, pricing_path: Path) -> dict:
    pricing = _read_json(pricing_path) if pricing_path.exists() else {"default": {"input": 0.0, "output": 0.0}}

    sessions = []
    totals = {
        "sessions": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "estimated_cost_usd": 0.0,
        "openai_request_count": 0,
        "openai_latency_ms_total": 0,
        "tool_events": {},
        "errors": 0,
    }

    for p in sorted(log_dir.glob("*.json")):
        try:
            data = _read_json(p)
        except Exception:
            continue

        meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
        model = str(data.get("model") or meta.get("model") or "unknown")
        usage = _parse_usage(meta)
        tool_events = data.get("tool_events")
        tool_counts = _count_tool_events(tool_events)
        err = meta.get("error")

        latency_total = int(_safe_number(meta.get("openai_latency_ms_total")))
        req_count = int(_safe_number(meta.get("openai_request_count")))

        sess = {
            "session_id": data.get("session_id"),
            "updated_at_unix": data.get("updated_at_unix"),
            "app": data.get("app"),
            "model": model,
            "has_usage": usage is not None,
            "usage": None,
            "cost": None,
            "openai_request_count": req_count,
            "openai_latency_ms_total": latency_total,
            "tool_event_counts": tool_counts,
            "has_error": bool(err),
            "error": str(err)[:500] if err else None,
            "path": str(p),
        }

        if usage:
            sess["usage"] = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            }
            cost = _estimate_cost_usd(model, usage, pricing)
            sess["cost"] = cost

            totals["prompt_tokens"] += usage.prompt_tokens
            totals["completion_tokens"] += usage.completion_tokens
            totals["total_tokens"] += usage.total_tokens
            totals["estimated_cost_usd"] += float(cost["estimated_cost_usd"])

        totals["sessions"] += 1
        totals["openai_request_count"] += max(0, req_count)
        totals["openai_latency_ms_total"] += max(0, latency_total)
        if err:
            totals["errors"] += 1

        for k, v in tool_counts.items():
            totals["tool_events"][k] = totals["tool_events"].get(k, 0) + int(v)

        sessions.append(sess)

    totals["estimated_cost_usd"] = round(float(totals["estimated_cost_usd"]), 6)
    avg_latency = 0
    if totals["openai_request_count"] > 0:
        avg_latency = int(round(totals["openai_latency_ms_total"] / totals["openai_request_count"]))

    return {
        "log_dir": str(log_dir),
        "pricing_path": str(pricing_path),
        "totals": {**totals, "openai_latency_ms_avg": avg_latency},
        "sessions": sessions,
    }


def _print_markdown_summary(report: dict) -> None:
    t = report["totals"]
    print("## Token/Cost summary")
    print(f"- sessions: {t['sessions']}")
    print(f"- prompt_tokens: {t['prompt_tokens']}")
    print(f"- completion_tokens: {t['completion_tokens']}")
    print(f"- total_tokens: {t['total_tokens']}")
    print(f"- estimated_cost_usd: {t['estimated_cost_usd']}")
    print("")
    print("## Reliability/Latency summary")
    print(f"- openai_request_count: {t['openai_request_count']}")
    print(f"- openai_latency_ms_total: {t['openai_latency_ms_total']}")
    print(f"- openai_latency_ms_avg: {t['openai_latency_ms_avg']}")
    print(f"- sessions_with_error: {t['errors']}")
    print("")
    print("## Tool-call summary")
    tool_events = t.get("tool_events", {})
    for k in sorted(tool_events.keys()):
        print(f"- {k}: {tool_events[k]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    ap.add_argument("--pricing", default=str(DEFAULT_PRICING_PATH))
    ap.add_argument("--out", default="")
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()

    report = build_report(Path(args.log_dir), Path(args.pricing))
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.markdown:
        _print_markdown_summary(report)
    else:
        print(json.dumps(report["totals"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

