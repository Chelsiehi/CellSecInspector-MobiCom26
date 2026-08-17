# VulnTestGenerator

VulnTestGenerator converts candidate violations into concrete vulnerability validation test cases.

## Repository Contents

- `VulnTestGenerator.py`: main generation script
- `README.md`: project overview and usage guide

## What The Script Does

The script reads:

1. a security-analysis Markdown file containing rows such as `(from_event, to_event, attack_type, analysis_json)`
2. a connection-details file containing the protocol state context for each connection

It then:

- matches each security-analysis row to its connection context
- filters to vulnerable rows by default
- prompts a LLM model to generate a concrete Markdown test table
- writes all generated test procedures into one Markdown report

## Requirements

- Python 3.10+
- `openai`

Optional:

- `json5` for tolerant parsing when the analysis JSON is not strict JSON

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## API Configuration

Set your DeepSeek API key before running:

```bash
export DEEPSEEK_API_KEY="your_api_key_here"
```

Optional environment variables:

```bash
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-chat"
```

## Usage

### Basic usage

```bash
python3 VulnTestGenerator.py \
  --security-md ./data/security_analysis_results_5g.md \
  --details-txt ./data/connection_details_output_5g.txt \
  --output ./outputs/all_testcases_step_procedures.md
```

### Include non-vulnerable rows as well

```bash
python3 VulnTestGenerator.py \
  --security-md ./data/security_analysis_results_5g.md \
  --details-txt ./data/connection_details_output_5g.txt \
  --output ./outputs/all_rows_testcases.md \
  --include-non-vulnerable
```

### Custom model settings

```bash
python3 VulnTestGenerator.py \
  --security-md ./data/security_analysis_results_24.229.md \
  --details-txt ./data/connection_details_output_24.229.txt \
  --output ./outputs/ts24229_testcases.md \
  --model deepseek-chat \
  --temperature 0.1 \
  --max-tokens 4096
```

## Input Expectations

### Security analysis Markdown

The script expects a Markdown table whose rows contain:

- `From Event`
- `To Event`
- `Attack Type`
- a JSON analysis payload inside the last column

It supports payloads wrapped in either:

- `BEGIN_JSON ... END_JSON`
- fenced blocks such as ```` ```json ... ``` ````

### Connection details file

The script expects connection blocks shaped like:

```text
=== Connection: 12 -> 13 ===
From Event (12):
Start State: ...
Condition: ...
Action: ...
End State: ...
To Event (13):
Start State: ...
Condition: ...
Action: ...
End State: ...
========================================
```

## Output Format

The generated Markdown report contains one section per selected `(connection, attack)` pair.
Each section includes:

- the original analysis JSON
- a generated Markdown table of test steps

## Notes

- The script makes one model call per selected row, so large reports can be slow and expensive.
- By default, only rows with `"vulnerability_detected": "Yes"` are processed.
- If your analysis JSON is slightly non-standard, install `json5` to improve parsing tolerance.
