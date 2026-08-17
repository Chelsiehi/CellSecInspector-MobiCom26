#!/usr/bin/env python3
"""Generate ARCANE exp1 input JSON files from a protocol spec text."""

import argparse
import json
import re
from collections import Counter


MESSAGE_KEYWORDS = {
    "REQUEST",
    "ACCEPT",
    "REJECT",
    "COMPLETE",
    "COMMAND",
    "FAILURE",
    "INDICATION",
}

PRIORITY_MESSAGES = [
    "ATTACH REQUEST",
    "SECURITY MODE COMMAND",
    "SECURITY MODE COMPLETE",
    "ATTACH ACCEPT",
    "TRACKING AREA UPDATE REQUEST",
    "TRACKING AREA UPDATE ACCEPT",
    "SERVICE REQUEST",
    "EXTENDED SERVICE REQUEST",
    "CONTROL PLANE SERVICE REQUEST",
    "SERVICE REJECT",
    "DETACH REQUEST",
    "DETACH ACCEPT",
    "ATTACH REJECT",
    "TRACKING AREA UPDATE REJECT",
    "PDN CONNECTIVITY REQUEST",
    "ROUTING AREA UPDATE REQUEST",
]


def normalize_message(name: str) -> str:
    return " ".join(name.strip().split())


def camel_to_words(token: str) -> str:
    # e.g., RRCReconfigurationRequest -> RRC Reconfiguration Request
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", token)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    return normalize_message(s)


def extract_messages(text: str):
    pattern = re.compile(r"\b([A-Z][A-Z0-9\-/]+(?: [A-Z][A-Z0-9\-/]+){0,7})\b")
    found = []
    for m in pattern.finditer(text):
        msg = normalize_message(m.group(1))
        tokens = msg.split()
        if len(tokens) < 2 or len(tokens) > 8:
            continue
        if not any(k in tokens for k in MESSAGE_KEYWORDS):
            continue
        found.append(msg)

    # Also capture CamelCase message names common in RRC specs.
    camel_pat = re.compile(
        r"\b([A-Za-z0-9\-]*(?:Request|Accept|Reject|Complete|Command|Indication|Response|Failure))\b"
    )
    for m in camel_pat.finditer(text):
        tok = m.group(1)
        if len(tok) < 6:
            continue
        norm = camel_to_words(tok).upper()
        tokens = norm.split()
        if len(tokens) < 1 or len(tokens) > 8:
            continue
        if not any(k in tokens for k in MESSAGE_KEYWORDS):
            continue
        # Keep only message-like names that contain at least one alphabetic token before suffix.
        found.append(norm)

    # Capture "X ... REQUEST/COMMAND ... message" style mentions in mixed case.
    phrase_pat = re.compile(
        r"\b([A-Za-z0-9\-/]+(?: [A-Za-z0-9\-/]+){0,6} "
        r"(?:REQUEST|ACCEPT|REJECT|COMPLETE|COMMAND|INDICATION|RESPONSE|FAILURE))\s+message\b",
        re.IGNORECASE,
    )
    for m in phrase_pat.finditer(text):
        norm = normalize_message(m.group(1)).upper()
        tokens = norm.split()
        if any(k in tokens for k in MESSAGE_KEYWORDS):
            found.append(norm)

    counts = Counter(x.upper() for x in found)
    unique = set(counts.keys())
    ordered = [m for m in PRIORITY_MESSAGES if m in unique]
    ordered.extend([m for m, _ in counts.most_common() if m not in ordered])
    return ordered, counts


def default_ies_for_message(message: str):
    ies = {"NAS key set identifier": "valid"}
    if "REQUEST" in message:
        ies.update(
            {
                "EPS mobile identity": "valid",
                "UE network capability": "valid",
            }
        )
    if "ACCEPT" in message:
        ies.update(
            {
                "EPS bearer context status": "valid",
                "ESM message container": "valid",
            }
        )
    if "REJECT" in message:
        ies.update(
            {
                "EMM cause": "valid",
                "Extended EMM cause": "valid",
            }
        )
    if "SECURITY MODE" in message:
        ies.update(
            {
                "Selected NAS security algorithms": "valid",
                "HASHMME": "valid",
            }
        )
    if "CONTROL PLANE SERVICE REQUEST" in message:
        ies.update(
            {
                "Device properties": "valid",
                "NAS message container": "valid",
            }
        )
    if "DETACH" in message:
        ies.update({"Detach type": "valid"})
    if "TRACKING AREA UPDATE" in message:
        ies.update({"TAI": "valid"})
    if "ATTACH" in message:
        ies.update({"EPS attach type": "valid"})
    return ies


def build_initial_model(messages):
    core = messages[: min(len(messages), 12)]
    states = {"IDLE": {"label": "IDLE", "description": "Initial NAS state"}}
    for idx, msg in enumerate(core, start=1):
        sid = f"S{idx}"
        states[sid] = {
            "label": msg.replace(" ", "_"),
            "description": f"Observed after {msg}",
        }

    transitions = {}
    if not core:
        return {"states": states, "transitions": transitions}

    prev = "IDLE"
    for idx, msg in enumerate(core, start=1):
        target = f"S{idx}"
        transitions.setdefault(prev, {})
        transitions[prev][target] = {
            "MessageType": msg,
            "IEs": default_ies_for_message(msg),
        }
        prev = target

    # Add a couple of fallback/error-like edges from IDLE if present.
    for msg in core:
        if "REJECT" in msg or "FAILURE" in msg:
            sid = f"S{core.index(msg) + 1}"
            transitions.setdefault("IDLE", {})
            transitions["IDLE"][sid] = {
                "MessageType": msg,
                "IEs": default_ies_for_message(msg),
            }

    return {"states": states, "transitions": transitions}


def build_traces(messages):
    m = set(messages)
    traces = []

    def add_trace(seq):
        if len(seq) < 2:
            return
        trace = [{"MessageType": s, "IEs": default_ies_for_message(s)} for s in seq]
        traces.append(trace)

    # Common NAS control flows.
    if {"ATTACH REQUEST", "SECURITY MODE COMMAND", "SECURITY MODE COMPLETE", "ATTACH ACCEPT"} <= m:
        add_trace(
            [
                "ATTACH REQUEST",
                "SECURITY MODE COMMAND",
                "SECURITY MODE COMPLETE",
                "ATTACH ACCEPT",
            ]
        )
    if {"ATTACH REQUEST", "ATTACH REJECT"} <= m:
        add_trace(["ATTACH REQUEST", "ATTACH REJECT"])
    if {"TRACKING AREA UPDATE REQUEST", "SECURITY MODE COMMAND", "SECURITY MODE COMPLETE", "TRACKING AREA UPDATE ACCEPT"} <= m:
        add_trace(
            [
                "TRACKING AREA UPDATE REQUEST",
                "SECURITY MODE COMMAND",
                "SECURITY MODE COMPLETE",
                "TRACKING AREA UPDATE ACCEPT",
            ]
        )
    if {"SERVICE REQUEST", "SERVICE REJECT"} <= m:
        add_trace(["SERVICE REQUEST", "SERVICE REJECT"])
    if {"EXTENDED SERVICE REQUEST", "SERVICE REJECT"} <= m:
        add_trace(["EXTENDED SERVICE REQUEST", "SERVICE REJECT"])
    if {"CONTROL PLANE SERVICE REQUEST", "SECURITY MODE COMMAND", "SECURITY MODE COMPLETE"} <= m:
        add_trace(
            [
                "CONTROL PLANE SERVICE REQUEST",
                "SECURITY MODE COMMAND",
                "SECURITY MODE COMPLETE",
            ]
        )
    if {"DETACH REQUEST", "DETACH ACCEPT"} <= m:
        add_trace(["DETACH REQUEST", "DETACH ACCEPT"])

    # Add paragraph-derived traces to increase coverage.
    paragraphs = [p for p in re.split(r"\n\s*\n", SPEC_TEXT) if p.strip()]
    msg_pattern = re.compile(r"\b(" + "|".join(re.escape(x) for x in messages[:30]) + r")\b")
    for para in paragraphs:
        seq = []
        for mm in msg_pattern.finditer(para):
            token = mm.group(1)
            if not seq or seq[-1] != token:
                seq.append(token)
        if len(seq) >= 2:
            add_trace(seq[:8])
        if len(traces) >= 24:
            break

    # Final fallback in case extraction is sparse.
    if not traces and len(messages) >= 2:
        add_trace(messages[: min(len(messages), 5)])

    return traces


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate ARCANE inputs from a spec text file")
    parser.add_argument("--spec-file", required=True, help="Path to source spec txt")
    parser.add_argument("--initial-out", required=True, help="Output initial_model JSON path")
    parser.add_argument("--trace-out", required=True, help="Output sample_trace JSON path")
    args = parser.parse_args()

    with open(args.spec_file, "r", encoding="utf-8", errors="ignore") as f:
        SPEC_TEXT = f.read()

    messages, counts = extract_messages(SPEC_TEXT)
    initial_model = build_initial_model(messages)
    traces = build_traces(messages)

    with open(args.initial_out, "w", encoding="utf-8") as f:
        json.dump(initial_model, f, indent=2)
    with open(args.trace_out, "w", encoding="utf-8") as f:
        json.dump(traces, f, indent=2)

    print(f"Extracted unique messages: {len(messages)}")
    print("Top messages:")
    for msg, c in counts.most_common(12):
        print(f"  {msg}: {c}")
    print(f"Initial model states: {len(initial_model['states'])}")
    trans_cnt = sum(len(v) for v in initial_model["transitions"].values())
    print(f"Initial model transitions: {trans_cnt}")
    print(f"Generated traces: {len(traces)}")
    print(f"Wrote: {args.initial_out}")
    print(f"Wrote: {args.trace_out}")
