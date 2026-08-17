#!/usr/bin/env python3
"""Dependency-light ARCANE refinement runner (no networkx/matplotlib)."""

import argparse
import json


class LightRefiner:
    def __init__(self, base_model, similarity_threshold=0.7, alpha=0.6):
        self.similarity_threshold = similarity_threshold
        self.alpha = alpha
        self.nodes = {}
        self.edges = {}  # source -> list[{"target": str, "MessageType": str, "IEs": dict}]
        self.ie_weights = {
            "TransactionID": 7,
            "gNB-DU-ID": 9,
            "gNB-CU-UE-F1AP-ID": 8,
            "gNB-DU-UE-F1AP-ID": 8,
            "C-RNTI": 8,
            "UE-Identity": 7,
            "RRCContainer": 6,
            "ServCellIndex": 5,
            "SpCell-ID": 7,
            "Cause": 6,
            "NRCGI": 5,
            "SRBID": 5,
            "DRBs-ToBeModified-List": 4,
            "SRBs-ToBeSetup-List": 4,
            "DRBs-Setup-List": 4,
            "SRBs-Setup-List": 4,
        }
        self.default_ie_weight = 3
        self._initialize(base_model)

    def _initialize(self, base_model):
        self.nodes = {sid: attrs.copy() for sid, attrs in base_model["states"].items()}
        for source, targets in base_model["transitions"].items():
            self.edges.setdefault(source, [])
            for target, attrs in targets.items():
                self.edges[source].append(
                    {
                        "target": target,
                        "MessageType": attrs.get("MessageType", ""),
                        "IEs": dict(attrs.get("IEs", {})),
                    }
                )

    def _procedure_similarity(self, proc1, proc2):
        if proc1["MessageType"] == proc2["MessageType"]:
            return 1.0
        p1 = proc1["MessageType"].split("_")[0] if "_" in proc1["MessageType"] else proc1["MessageType"].split(" ")[0]
        p2 = proc2["MessageType"].split("_")[0] if "_" in proc2["MessageType"] else proc2["MessageType"].split(" ")[0]
        if p1 == p2:
            return 0.5
        return 0.0

    def _weighted_ie_similarity(self, ies1, ies2):
        if not ies1 or not ies2:
            return 0.0
        common = set(ies1.keys()) & set(ies2.keys())
        all_ies = set(ies1.keys()) | set(ies2.keys())
        if not common:
            return 0.0
        num = 0.0
        den = 0.0
        for ie in all_ies:
            w = self.ie_weights.get(ie, self.default_ie_weight)
            den += w
            if ie in common:
                num += w if ies1[ie] == ies2[ie] else 0.5 * w
        return num / den if den > 0 else 0.0

    def _similarity(self, e1, e2):
        ps = self._procedure_similarity(e1, e2)
        ies = self._weighted_ie_similarity(e1.get("IEs", {}), e2.get("IEs", {}))
        return self.alpha * ps + (1 - self.alpha) * ies

    def _new_state_id(self):
        return f"S{len(self.nodes)}"

    def merge_trace(self, trace):
        current = "IDLE"
        for msg in trace:
            out = self.edges.get(current, [])
            max_sim = -1.0
            best = None
            for edge in out:
                sim = self._similarity(edge, msg)
                if sim > max_sim:
                    max_sim = sim
                    best = edge
            if best and max_sim > self.similarity_threshold:
                for ie, value in msg.get("IEs", {}).items():
                    if ie not in best["IEs"]:
                        best["IEs"][ie] = value
                current = best["target"]
            else:
                new_state = self._new_state_id()
                self.nodes[new_state] = {"label": msg["MessageType"]}
                self.edges.setdefault(current, []).append(
                    {
                        "target": new_state,
                        "MessageType": msg["MessageType"],
                        "IEs": dict(msg.get("IEs", {})),
                    }
                )
                current = new_state

    def save_dot(self, output_file):
        lines = [
            "digraph G {",
            "  rankdir=LR;",
            "  node [shape=circle, style=filled, fillcolor=lightblue];",
        ]
        for node, attrs in self.nodes.items():
            label = attrs.get("label", node).replace('"', '\\"')
            lines.append(f'  "{node}" [label="{label}"];')
        for source, outs in self.edges.items():
            for e in outs:
                msg = e.get("MessageType", "")
                ies = e.get("IEs", {})
                ie_preview = ", ".join([f"{k}:{v}" for k, v in list(ies.items())[:3]])
                label = f"{msg}\\n{ie_preview}" if ie_preview else msg
                label = label.replace('"', '\\"')
                lines.append(f'  "{source}" -> "{e["target"]}" [label="{label}"];')
        lines.append("}")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def counts(self):
        return len(self.nodes), sum(len(v) for v in self.edges.values())


def main():
    parser = argparse.ArgumentParser(description="Run light ARCANE refinement")
    parser.add_argument("--initial-model", required=True)
    parser.add_argument("--sample-trace", required=True)
    parser.add_argument("--output-dot", required=True)
    parser.add_argument("--threshold", type=float, default=0.7)
    parser.add_argument("--alpha", type=float, default=0.6)
    args = parser.parse_args()

    with open(args.initial_model, "r", encoding="utf-8") as f:
        initial = json.load(f)
    with open(args.sample_trace, "r", encoding="utf-8") as f:
        traces = json.load(f)

    refiner = LightRefiner(initial, args.threshold, args.alpha)
    init_states, init_trans = refiner.counts()
    for trace in traces:
        refiner.merge_trace(trace)
    ref_states, ref_trans = refiner.counts()
    refiner.save_dot(args.output_dot)

    print(f"Initial model: states={init_states}, transitions={init_trans}")
    print(f"Refined model: states={ref_states}, transitions={ref_trans}")
    print(f"Traces used: {len(traces)}")
    print(f"DOT saved: {args.output_dot}")


if __name__ == "__main__":
    main()
