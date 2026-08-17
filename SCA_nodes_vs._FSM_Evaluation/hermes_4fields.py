#!/usr/bin/env python3
"""Run Hermes labeling pipeline on raw spec text and compute 0-4 valid field stats."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Dict, List


INVALID_EXACT = {
    "",
    "not specified",
    "not explicitly defined",
    "unknown",
    "unclear",
    "n/a",
    "none",
    "null",
    "_unk_",
}

INVALID_PHRASES = (
    "not specified",
    "not explicitly defined",
)


def run_cmd(cmd: List[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def is_valid_field(value: str) -> bool:
    v = (value or "").strip().lower()
    v = re.sub(r"\s+", " ", v).strip(" .;:,!-_")
    if v in INVALID_EXACT:
        return False
    if any(phrase in v for phrase in INVALID_PHRASES):
        return False
    return True


def extract_tag_text(line: str, tag: str) -> str:
    matches = re.findall(rf"<{tag}>\s*(.*?)\s*</{tag}>", line, flags=re.IGNORECASE)
    if not matches:
        return ""
    return " ".join(m.strip() for m in matches if m.strip())


def escape_xml(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def parse_labeled_lines(output_txt: Path) -> List[Dict[str, str]]:
    events: List[Dict[str, str]] = []
    lines = output_txt.read_text(encoding="utf-8", errors="ignore").splitlines()
    for idx, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        start = extract_tag_text(line, "start_state")
        cond = extract_tag_text(line, "condition")
        action = extract_tag_text(line, "action")
        end = extract_tag_text(line, "end_state")
        events.append(
            {
                "event_id": str(idx),
                "raw_labeled_line": line,
                "start": start,
                "condition": cond,
                "action": action,
                "end": end,
            }
        )
    return events


def build_transition_xml(events: List[Dict[str, str]]) -> str:
    lines = ["<transitions>"]
    for e in events:
        lines.append(f'  <transition id="E{e["event_id"]}">')
        lines.append(f'    <start_state>{escape_xml(e["start"])}</start_state>')
        lines.append(f'    <condition>{escape_xml(e["condition"])}</condition>')
        lines.append(f'    <action>{escape_xml(e["action"])}</action>')
        lines.append(f'    <end_state>{escape_xml(e["end"])}</end_state>')
        lines.append("  </transition>")
    lines.append("</transitions>")
    return "\n".join(lines) + "\n"


def compute_stats(events: List[Dict[str, str]]) -> Dict[str, object]:
    dist = Counter()
    detailed = []
    valid_slots = 0

    for e in events:
        flags = [
            is_valid_field(e["start"]),
            is_valid_field(e["condition"]),
            is_valid_field(e["action"]),
            is_valid_field(e["end"]),
        ]
        vc = sum(flags)
        dist[str(vc)] += 1
        valid_slots += vc
        detailed.append(
            {
                "event_id": e["event_id"],
                "start_text": e["start"],
                "condition_text": e["condition"],
                "action_text": e["action"],
                "end_text": e["end"],
                "valid_fields": vc,
                "is_start_valid": flags[0],
                "is_condition_valid": flags[1],
                "is_action_valid": flags[2],
                "is_end_valid": flags[3],
            }
        )

    total_events = len(events)
    total_slots = total_events * 4
    return {
        "total_events": total_events,
        "total_slots": total_slots,
        "valid_slots": valid_slots,
        "valid_slot_pct": round((valid_slots / total_slots) * 100, 6) if total_slots else 0.0,
        "distribution": {str(i): dist.get(str(i), 0) for i in range(5)},
        "distribution_ratio": {
            str(i): round((dist.get(str(i), 0) / total_events), 6) if total_events else 0.0 for i in range(5)
        },
        "detailed": detailed,
    }


def run_hermes_pipeline(
    raw_spec: Path,
    hermes_repo: Path,
    model_repo: Path,
    py_bin: Path,
) -> Path:
    workdir = Path(tempfile.mkdtemp(prefix="hermes_label_"))
    input_txt = workdir / "input.txt"

    lines = [ln.strip() for ln in raw_spec.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
    input_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    conversion_py = hermes_repo / "neutrex" / "xml_to_tree" / "conversion.py"
    tree_to_xml_py = hermes_repo / "neutrex" / "tree_to_xml" / "tree_to_xml.py"
    tree_cleanup_py = hermes_repo / "neutrex" / "tree_to_xml" / "tree_cleanup.py"

    # 1) Plain text -> .pid
    run_cmd([str(py_bin), str(conversion_py)], cwd=workdir)

    # 2) NEUTREX prediction
    pred_pid = workdir / "pred.pid"
    run_cmd(
        [
            str(py_bin),
            "-u",
            "-m",
            "supar.cmds.crf_con",
            "predict",
            "-d",
            "0",
            "-c",
            "crf-con-roberta-en",
            "-p",
            str(model_repo / "neutrex" / "model_5g_nas"),
            "--data",
            str(workdir / "out_full.pid"),
            "--pred",
            str(pred_pid),
            "--encoder=bert",
            f"--bert={model_repo / 'neutrex' / 'saved_model'}",
        ],
        cwd=model_repo / "neutrex",
    )

    # 3) Predicted .pid -> XML-like labeled text lines
    shutil.copy(pred_pid, workdir / "input.pid")
    shutil.copy(tree_cleanup_py, workdir / "tree_cleanup.py")
    run_cmd([str(py_bin), str(tree_to_xml_py)], cwd=workdir)

    return workdir / "output.txt"


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes labeling + 0-4 field counting from raw spec")
    parser.add_argument("--raw-spec", required=True)
    parser.add_argument("--name", required=True, help="Short name used for output file naming")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--hermes-repo", default="/home/test/hermes-spec-to-fsm-main")
    parser.add_argument("--model-repo", default="/home/test/CellularSecurityInspector/hermes-spec-to-fsm-main")
    parser.add_argument(
        "--python-bin",
        default="/home/test/CellularSecurityInspector/hermes-spec-to-fsm-main/neutrex/.venv/bin/python",
    )
    args = parser.parse_args()

    raw_spec = Path(args.raw_spec)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    output_txt = run_hermes_pipeline(
        raw_spec=raw_spec,
        hermes_repo=Path(args.hermes_repo),
        model_repo=Path(args.model_repo),
        py_bin=Path(args.python_bin),
    )

    events = parse_labeled_lines(output_txt)
    stats = compute_stats(events)
    transitions_xml = build_transition_xml(events)

    labeled_line_out = out_dir / f"hermes_labeled_lines_{args.name}.txt"
    transition_out = out_dir / f"hermes_labeled_transitions_{args.name}.xml"
    stats_out = out_dir / f"hermes_field_stats_{args.name}.json"

    labeled_line_out.write_text(output_txt.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
    transition_out.write_text(transitions_xml, encoding="utf-8")
    stats_out.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"raw_spec={raw_spec}")
    print(f"total_events={stats['total_events']}")
    print(f"distribution={stats['distribution']}")
    print(f"labeled_lines={labeled_line_out}")
    print(f"labeled_transitions={transition_out}")
    print(f"stats={stats_out}")


if __name__ == "__main__":
    main()
