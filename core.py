"""Shared data, exact arithmetic, and application-owned state. No API dependencies."""
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
INSTRUCTIONS = (
    "You are a sales report tutor. Explain the supplied fictional sales figures "
    "clearly and concisely. Use gross profit = revenue - cost, and gross margin "
    "percentage = gross profit / revenue * 100. Do not confuse margin with markup. "
    "Use the supplied verified totals; do not invent figures or business causes. "
    "Ask for missing facts. Answer follow-up questions using the conversation."
)


def sales_facts(path=ROOT / "data" / "sales.json"):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    products = data.get("products")
    if not isinstance(products, list) or not products:
        raise ValueError("Sales data must contain a nonempty products list.")
    revenue, cost = Decimal(0), Decimal(0)
    for product in products:
        try:
            r, c = Decimal(str(product["revenue"])), Decimal(str(product["cost"]))
        except (KeyError, InvalidOperation) as exc:
            raise ValueError("Each product needs numeric revenue and cost.") from exc
        if not r.is_finite() or not c.is_finite() or r < 0 or c < 0:
            raise ValueError("Revenue and cost must be finite, nonnegative values.")
        revenue += r
        cost += c
    profit = revenue - cost
    return {
        "company": data["company"], "period": data["period"],
        "currency": data["currency"], "revenue": f"{revenue:.2f}",
        "cost": f"{cost:.2f}", "gross_profit": f"{profit:.2f}",
        "gross_margin_percent": f"{profit / revenue * 100:.2f}" if revenue else None,
    }


def initial_input(question, facts):
    return f"Verified sales facts:\n{json.dumps(facts, indent=2)}\n\nStudent request: {question}"


def state_path(base, mode, runtime, session):
    # A classroom label becomes a filename, never an arbitrary filesystem path.
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", session):
        raise ValueError("Session labels must use 1-64 letters, digits, _ or -.")
    return Path(base) / mode / runtime / f"{session}.json"


def load_state(path):
    if not path.exists():
        return {"turns": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid state JSON: {path}. Choose a new session label.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("turns"), list):
        raise ValueError("State must be an object with a turns list.")
    return data


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


BOUNDARIES = {
    "managed": {
        "loop": "OpenAI-managed harness (remote)",
        "state": "Remote agent session; application saves its session_id",
        "tools": "No tools or sandbox in this example; verified facts sent as text",
    },
    "sdk": {
        "loop": "Agents SDK Runner in this Python process; model called remotely",
        "state": "SQLiteSession in local application-owned storage",
        "tools": "get_sales_facts executes inside this Python application",
    },
    "responses": {
        "loop": "Application sends one direct model request per student turn",
        "state": "Application saves previous_response_id; response chain is remote",
        "tools": "Application supplies verified facts; no model tools configured",
    },
}
