# SCA Nodes vs. FSM Evaluation

This directory contains the artifact for **RQ3** in the paper: **How effectively does SCA preserve procedural information?**.

## Relation to the Paper

This repository folder corresponds to the paper section:

- `RQ3: How effectively does SCA preserve procedural information?`

The goal of RQ3 is not just to show that the SCA-based pipeline finds more vulnerabilities, but to explain **why** it performs better. The paper compares:

- **SCA nodes** used by the CellSecInspector pipeline
- **FSM-style intermediate representations** produced by prior systems such as **Hermes** and **ARCANE**

The comparison is performed along three dimensions described in the paper:

1. **Quantity**
2. **Completeness**
3. **Accuracy**

At a high level, the paper argues that SCA nodes preserve more of the protocol semantics required for standards reasoning, including:

- start state
- condition
- action
- end state


## What This Directory Contains

- `generate_inputs_from_spec.py`
  - extracts message-like procedures from raw specification text
  - generates simplified ARCANE-style input artifacts such as initial models and sample traces
- `hermes_4fields.py`
  - runs a Hermes labeling pipeline on raw spec text
  - converts Hermes-style outputs into the same four-field structure used in SCA nodes
  - computes the `0/1/2/3/4 valid fields` completeness statistics used in the RQ3 discussion
- `run_arcane_light.py`
  - runs a lightweight refinement procedure over an initial ARCANE-like model and traces
  - produces a DOT graph that can be used for structural inspection
- `initial_model.json`
  - example initial model for ARCANE-style refinement
- `sample_trace.json`
  - example traces used by the light ARCANE refinement script

## Why These Scripts Exist

RQ3 compares representations, not just final vulnerability counts.

Prior work typically builds FSMs first and then performs downstream analysis. In contrast, the SCA-based approach preserves richer transition semantics in four explicit fields. To make the comparison fair, the paper converts competing representations into the same comparison space:

- **Hermes** transitions are mapped into four fields by splitting and interpreting labeled outputs
- **ARCANE** transitions are approximated through message-level models and manual or structural mapping into four fields
- **SCA nodes** already natively contain these four fields

This directory supports that representation-level evaluation workflow.


## Usage Overview

### Generate ARCANE-style inputs from raw specification text

```bash
python3 generate_inputs_from_spec.py --help
```

Typical use:

```bash
python3 generate_inputs_from_spec.py \
  --input /path/to/spec.txt \
  --initial-model ./initial_model.json \
  --sample-trace ./sample_trace.json
```

### Run Hermes four-field conversion and completeness counting

```bash
python3 hermes_4fields.py --help
```

Typical use:

```bash
python3 hermes_4fields.py \
  --raw-spec /path/to/spec.txt \
  --name ts24501_clause4 \
  --out-dir ./outputs
```

Important:
This script depends on an external Hermes/NEUTREX environment and expects local paths to those repositories and Python environments. The defaults in the script reflect the original experiment environment and may need to be changed on a new machine.

### Run lightweight ARCANE refinement

```bash
python3 run_arcane_light.py --help
```

Typical use:

```bash
python3 run_arcane_light.py \
  --initial-model ./initial_model.json \
  --sample-trace ./sample_trace.json \
  --output-dot ./arcane_light.dot
```
