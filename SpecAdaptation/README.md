# SpecAdaptation 

## What it does

- Reads `.docx` specification files from an input directory.
- Extracts visible paragraph text while skipping tables and embedded drawings.
- Writes cleaned `.txt` files for inspection.
- Builds paragraph-level retrieval chunks.
- Sends retrieved context and a user query to the DeepSeek chat API.


## Requirements

- Python 3.10+
- A `DEEPSEEK_API_KEY` environment variable, or pass `--api-key`
- Dependencies from `requirements.txt`

Install dependencies:

```bash
pip install -r requirements.txt
```

If NLTK `punkt` is not already installed, either install it manually or run the script once with `--download-nltk-data`.

## Usage

1. Put source `.docx` files in `input_docx/`.
2. Run preprocessing only:

```bash
python SpecAdaption_api.py --process-only --verbose
```

3. Run the full demo with a query:

```bash
export DEEPSEEK_API_KEY="your_api_key"
python SpecAdaption_api.py \
  --input-dir input_docx \
  --output-dir clean_txt \
  --query "What is the purpose of NAS security?" \
  --top-k 6 \
  --verbose
```

