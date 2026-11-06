"""Run from this folder: python app.py compare; python app.py --help."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from time import perf_counter
from uuid import uuid4

from core import ROOT, BOUNDARIES, load_state, save_json, state_path
from runtimes import live, offline


def run_turn(args, runtime, session):
    path = state_path(args.storage, args.mode, runtime, session)
    state = load_state(path)
    if args.mode == "live" and state.get("model", args.model) != args.model:
        raise ValueError("Use the same model for an existing session, or choose a new session label.")
    state.update(mode=args.mode, runtime=runtime, model=args.model if args.mode == "live" else None)
    start = perf_counter()
    if args.mode == "offline":
        output, trace = offline(runtime, args.question, state, args.data)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        output, trace = live(runtime, args.model, args.question, state, args.data, path)
    elapsed = perf_counter() - start
    record = {"question": args.question, "answer": output, "elapsed_seconds": round(elapsed, 4),
              "completed_at": datetime.now(timezone.utc).isoformat(), "trace": trace}
    state["turns"].append(record)
    save_json(path, state)
    print(f"\n=== {runtime.upper()} | {args.mode.upper()} | {session} ===")
    for name, value in BOUNDARIES[runtime].items():
        print(f"{name.capitalize()}: {value}")
    if args.mode == "offline":
        print("Above: intended LIVE boundaries. This run simulates them using local JSON only.")
    print(f"\n{output}\n")
    for item in trace:
        print(f"  -> {item}")
    print(f"Elapsed: {elapsed:.4f}s | State: {path}")
    return {"runtime": runtime, "mode": args.mode, "elapsed_seconds": round(elapsed, 4),
            "turn_count": len(state["turns"]), "state_file": str(path),
            "quality_score": None, "cost_usd": None,
            "measurement_note": "Offline timing is local simulation overhead, not model latency." if args.mode == "offline" else "Wall time includes network and local processing; quality and cost need separate evaluation."}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Lesson 4: compare agent runtime ownership and state.")
    parser.add_argument("command", choices=["run", "compare", "state"], nargs="?", default="compare")
    parser.add_argument("--runtime", choices=list(BOUNDARIES), default="responses")
    parser.add_argument("--mode", choices=["offline", "live"], default="offline")
    parser.add_argument("--session", default="classroom")
    parser.add_argument("--question", default="Summarize the sales results and explain gross margin.")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-6-astra"))
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "sales.json")
    parser.add_argument("--storage", type=Path, default=ROOT / "storage")
    args = parser.parse_args(argv)
    if not args.question.strip():
        parser.error("--question cannot be empty")
    try:
        if args.command == "state":
            path = state_path(args.storage, args.mode, args.runtime, args.session)
            print(json.dumps(load_state(path), indent=2, ensure_ascii=False))
        elif args.command == "run":
            run_turn(args, args.runtime, args.session)
        else:
            # Fresh conversation for each runtime, all using the same question and dataset.
            session = "comparison_" + uuid4().hex[:10]
            rows = []
            for runtime in BOUNDARIES:
                try:
                    rows.append(run_turn(args, runtime, session))
                except Exception as exc:
                    rows.append({"runtime": runtime, "mode": args.mode, "error_type": type(exc).__name__})
                    print(f"{runtime} failed: {type(exc).__name__}. See troubleshooting in README.", file=sys.stderr)
            report = args.storage / f"{session}_scorecard.json"
            save_json(report, rows)
            print(f"\nComparison saved: {report}")
            return 1 if any("error_type" in row for row in rows) else 0
        return 0
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        # Do not dump request objects or credential-bearing HTTP headers to the console.
        print(f"Live request failed ({type(exc).__name__}). See README troubleshooting.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
