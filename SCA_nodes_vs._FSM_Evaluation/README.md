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
- `reproduce_hermes.sh`
  - verifies the pinned Hermes commit and runs the complete Hermes extraction with explicit paths
- `HERMES_COMMIT.txt`
  - records the exact Hermes commit used for evaluation
- `environment.yml`
  - provides a Conda starting environment for the Python-based artifact
- `run_arcane_light.py`
  - runs a lightweight refinement procedure over an initial ARCANE-like model and traces
  - produces a DOT graph that can be used for structural inspection
- `initial_model.json`
  - example initial model for ARCANE-style refinement
- `sample_trace.json`
  - example traces used by the light ARCANE refinement script
- `Expert_answer/`
  - contains the expert-reviewed evaluation samples and paired Pass/Fail annotations used in Table 6
  - includes SCA reference records for 4G NAS, 5G NAS, and 5G RRC
  - includes paired annotations from two domain experts for CellSecInspector, Hermes, and ARCANE
  - supports the acceptance-rate and inter-rater agreement calculations in Table 6(a)
  - provides expert-reviewed reference data for evaluating extraction results produced by different language models in Table 6(b)
  - contains a separate README describing the included files, formats, counts, and intended usage

## Why These Scripts Exist

RQ3 compares representations, not just final vulnerability counts.

Prior work typically builds FSMs first and then performs downstream analysis. In contrast, the SCA-based approach preserves richer transition semantics in four explicit fields. To make the comparison fair, the paper converts competing representations into the same comparison space:

- **Hermes** transitions are mapped into four fields by splitting and interpreting labeled outputs
- **ARCANE** transitions are approximated through message-level models and manual or structural mapping into four fields
- **SCA nodes** already natively contain these four fields

This directory supports that representation-level evaluation workflow.


## Running Hermes and ARCANE

Run the commands below from this directory unless stated otherwise:

```bash
cd SCA_nodes_vs._FSM_Evaluation
```

The three helper scripts support `--help`:

```bash
python3 hermes_4fields.py --help
python3 generate_inputs_from_spec.py --help
python3 run_arcane_light.py --help
```

### Run Hermes

#### Prerequisites

`hermes_4fields.py` is a wrapper around an external Hermes/NEUTREX installation. It does not install Hermes or download its trained models. Before running it, prepare:

1. A Hermes repository containing:
   - `neutrex/xml_to_tree/conversion.py`
   - `neutrex/tree_to_xml/tree_to_xml.py`
   - `neutrex/tree_to_xml/tree_cleanup.py`
2. A model repository containing:
   - `neutrex/model_5g_nas`
   - `neutrex/saved_model`
3. A Python interpreter from the Hermes/NEUTREX environment with its dependencies, including `supar`.
4. A plain-text specification input. Non-empty lines are passed to Hermes as labeling units, so sentence- or procedure-level lines work best.

The Hermes repository and model repository may be the same checkout. Pass explicit paths because the defaults in the script refer to the machine used for the original experiment.

The evaluation used Hermes commit
`d37fe752fec2592dcc10cc11fabfcb6429d6a216`, recorded in
`HERMES_COMMIT.txt`. For reproducibility, use a snapshot or a Git checkout of
Hermes at exactly this commit. The helper below refuses to run if the checkout
is at a different commit. This artifact keeps Hermes as an external checkout
because the upstream repository URL and its redistribution terms are not part
of this repository; if those become available, the same commit can be vendored
or added as a Git submodule without changing the helper interface.

For Python compatibility, create the supplied Conda environment first and then
install the dependencies specified by the pinned Hermes/NEUTREX checkout. Once
the environment has been validated, preserve the exact package versions with
`conda env export --no-builds > environment-lock.yml` (or provide a Docker
image containing the same environment).

```bash
conda env create -f environment.yml
conda activate cellsecinspector-hermes
```

#### Command

```bash
mkdir -p outputs/hermes

python3 hermes_4fields.py \
  --raw-spec /absolute/path/to/spec.txt \
  --name ts24501_clause4 \
  --out-dir ./outputs/hermes \
  --hermes-repo /absolute/path/to/hermes-spec-to-fsm-main \
  --model-repo /absolute/path/to/hermes-spec-to-fsm-main \
  --python-bin /absolute/path/to/hermes-spec-to-fsm-main/neutrex/.venv/bin/python
```

The recommended reproducibility entry point is the helper script. It keeps the
Hermes revision, model location, and interpreter explicit:

```bash
export HERMES_DIR=/absolute/path/to/hermes-spec-to-fsm-main
export MODEL_REPO=/absolute/path/to/hermes-spec-to-fsm-main
export HERMES_PYTHON=/absolute/path/to/hermes-spec-to-fsm-main/neutrex/.venv/bin/python

./reproduce_hermes.sh /absolute/path/to/spec.txt ./outputs/hermes
```

`HERMES_DIR` must be a Git checkout at the commit in `HERMES_COMMIT.txt`, and
`MODEL_REPO` must contain the trained model directories listed above. Set
`HERMES_NAME` to override the output basename; otherwise it is derived from the
input filename.

The wrapper performs three stages:

1. converts the plain-text input to Hermes `.pid` input;
2. runs the NEUTREX `supar.cmds.crf_con` predictor;
3. converts predictions to labeled text, maps them to `start`, `condition`, `action`, and `end`, and counts how many of those four fields are valid.

For `--name ts24501_clause4`, the output directory contains:

- `hermes_labeled_lines_ts24501_clause4.txt`: raw Hermes labeled lines;
- `hermes_labeled_transitions_ts24501_clause4.xml`: normalized four-field transitions;
- `hermes_field_stats_ts24501_clause4.json`: completeness distribution and per-event details.

The JSON `distribution` object reports the number of events containing 0, 1, 2, 3, or 4 valid fields. Empty values and placeholders such as `unknown`, `N/A`, and `not specified` are treated as invalid.

#### Hermes troubleshooting

- `conversion.py` or `tree_to_xml.py` not found: verify `--hermes-repo` points to the repository root, not its `neutrex` subdirectory.
- Model or BERT path not found: verify `--model-repo/neutrex/model_5g_nas` and `--model-repo/neutrex/saved_model` exist.
- `No module named supar`: use the NEUTREX virtual-environment interpreter for `--python-bin`.
- CUDA/device error: the current wrapper passes `-d 0` to NEUTREX, selecting device 0. Use a Hermes environment with an available compatible device, or adjust that argument in `hermes_4fields.py` for a CPU-only installation.
- A subprocess failure stops the wrapper immediately and preserves its command error, which is normally the most useful diagnostic.

### Run lightweight ARCANE

The lightweight ARCANE workflow uses only the Python standard library; it does not require the original ARCANE repository, NetworkX, or Matplotlib. It has two stages: generate JSON inputs and refine the model.

#### Quick run with the included examples

```bash
mkdir -p outputs/arcane

python3 run_arcane_light.py \
  --initial-model ./initial_model.json \
  --sample-trace ./sample_trace.json \
  --output-dot ./outputs/arcane/arcane_light.dot
```

The command prints the initial and refined state/transition counts and writes a Graphviz DOT file.

#### Generate ARCANE inputs from a specification

The input generator extracts message-like names from plain text, builds a small initial model, and creates representative message traces:

```bash
mkdir -p outputs/arcane

python3 generate_inputs_from_spec.py \
  --spec-file /absolute/path/to/spec.txt \
  --initial-out ./outputs/arcane/initial_model.json \
  --trace-out ./outputs/arcane/sample_trace.json
```

The generated files have the following roles:

- `initial_model.json`: states and message-labeled transitions used as the base model;
- `sample_trace.json`: lists of observed messages and information elements to merge into the model.

The generator uses common NAS procedure patterns when available and falls back to message sequences found in specification paragraphs. Review generated JSON before using it for a paper result because message extraction is heuristic.

#### Refine the generated model

```bash
python3 run_arcane_light.py \
  --initial-model ./outputs/arcane/initial_model.json \
  --sample-trace ./outputs/arcane/sample_trace.json \
  --output-dot ./outputs/arcane/arcane_light.dot \
  --threshold 0.7 \
  --alpha 0.6
```

`--threshold` controls when an observed trace message is merged with an existing transition; a higher value requires a closer match. `--alpha` controls the similarity balance between message type and information elements: higher values give more weight to the message type. Their defaults are `0.7` and `0.6`, respectively.

If Graphviz is installed, render the resulting graph with:

```bash
dot -Tpng ./outputs/arcane/arcane_light.dot \
  -o ./outputs/arcane/arcane_light.png
```

#### ARCANE troubleshooting

- `FileNotFoundError`: check the paths passed to `--initial-model` and `--sample-trace` and create the output directory before running.
- JSON decoding error: validate that the initial model and trace files contain valid JSON. The included files show the expected schemas.
- Empty or very small generated traces: provide specification text containing explicit message names such as `REQUEST`, `ACCEPT`, `REJECT`, `COMMAND`, `COMPLETE`, `FAILURE`, or `INDICATION`.
- Unexpectedly many new states: increase `--threshold` only if you want stricter merging; decrease it to merge more observed messages with existing transitions. Adjust `--alpha` when message names and information-element similarity disagree.
