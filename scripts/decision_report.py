"""Show what the bot decides for each canonical test pair, with no language model involved.

For every pair it prints the strategy, who the message goes to, what it leads with (the
"why now"), the supporting facts, the call-to-action and any warnings. Run it after changing
the router or the lead builders to see the effect on all 30 pairs at once.

    python scripts/decision_report.py --data data/expanded
    python scripts/decision_report.py --data data/expanded --only T05,T24
    python scripts/decision_report.py --data data/expanded --all      # every trigger, summary only
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vera.dataset import load_pairs, load_store  # noqa: E402
from vera.ledger import Ledger  # noqa: E402
from vera.planner import plan_tick  # noqa: E402
from vera.signals import build_brief  # noqa: E402


def show(label: str, brief) -> None:
    flags = " ".join(f for f, on in (("[PLACEHOLDER]", brief.placeholder), ("[DEGRADED]", brief.degraded)) if on)
    who = brief.salutation or "(no name)"
    if brief.about:
        who += f" (about {brief.about})"
    print(f"{label}  {brief.kind}  ->  {brief.send_as}  to {who}  [{brief.language}]  cta={brief.cta}  urgency={brief.urgency}  {flags}")
    print(f"      LEAD     {brief.lead.text if brief.lead else '(nothing found)'}")
    for fact in brief.support:
        print(f"      support  - {fact.text}")
    for note in brief.notes:
        print(f"      note     ! {note}")
    print()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default="data/expanded", type=Path)
    parser.add_argument("--only", default="", help="comma-separated test ids, e.g. T05,T24")
    parser.add_argument("--all", action="store_true", help="every trigger in the dataset (summary only)")
    args = parser.parse_args()

    store = load_store(args.data)
    print(f"loaded {store.counts()}\n")

    if args.all:
        reasons, kinds, degraded = Counter(), Counter(), Counter()
        for trigger_id in store.ids("trigger"):
            brief, why = build_brief(store.get("trigger", trigger_id), store, trigger_id)
            if brief is None:
                reasons[why] += 1
                continue
            kinds[brief.kind] += 1
            degraded[brief.degraded] += 1
        print("briefs by kind:", dict(kinds))
        print("degraded:", dict(degraded), " could not build:", dict(reasons))
        return

    pairs = load_pairs(args.data)
    wanted = {t.strip().upper() for t in args.only.split(",") if t.strip()}
    shown = Counter()
    for pair in pairs:
        if wanted and pair["test_id"] not in wanted:
            continue
        brief, why = build_brief(store.get("trigger", pair["trigger_id"]), store, pair["trigger_id"])
        if brief is None:
            print(f"{pair['test_id']}  CANNOT BUILD: {why}\n")
            shown["cannot_build"] += 1
            continue
        show(pair["test_id"], brief)
        shown["placeholder" if brief.placeholder else "real_payload"] += 1
        shown["degraded"] += brief.degraded

    print("summary:", dict(shown))

    plan = plan_tick(store, Ledger(), [p["trigger_id"] for p in pairs if not wanted or p["test_id"] in wanted])
    print(f"\nif all of these were active in one tick: {len(plan.briefs)} messages, {len(plan.skipped)} skipped")
    for skip in plan.skipped:
        print(f"      skipped {skip.trigger_id}: {skip.reason}")


if __name__ == "__main__":
    main()
