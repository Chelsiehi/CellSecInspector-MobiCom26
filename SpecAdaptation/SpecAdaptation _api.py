"""Minimal RAG demo for telecom specification question answering.

This script:
- extracts visible text from `.docx` specification files,
- writes normalized `.txt` files for inspection,
- builds paragraph-level retrieval chunks, and
- sends retrieved context to the DeepSeek chat API.

"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    import docx
except ImportError:
    docx = None

try:
    import nltk
    from nltk.tokenize import word_tokenize
except ImportError:
    nltk = None
    word_tokenize = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

LOGGER = logging.getLogger("specadaptation")
DEFAULT_MODEL = "deepseek-reasoner"
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_QUERY = "What is the purpose of NAS security?"
SECTION_HEADER_PATTERN = re.compile(r"^\d+(\.\d+)*\s+[A-Za-z]+.*$")


@dataclass(frozen=True)
class ParagraphChunk:
    """A paragraph-sized retrieval unit produced from a cleaned text file."""

    document: str
    paragraph_id: int
    text: str


def require_dependency(module: object | None, package_name: str, import_name: str) -> None:
    """Raise a user-facing error when an optional runtime dependency is missing."""
    if module is None:
        raise RuntimeError(
            f"Missing dependency '{import_name}'. Install '{package_name}' or run "
            "`pip install -r requirements.txt`."
        )


def clean_and_normalize(text: str) -> str:
    """Apply lightweight cleanup to spec text extracted from Word files."""
    text = re.sub(r" +", " ", text)
    text = re.sub(r"(\n)+", "", text)
    text = re.sub(r"^[\.:·\-]", "", text)
    text = re.sub(r"^ ", "", text)
    text = re.sub(r"[\.:,;\-]*$", "", text)
    text = re.sub(r"(\(\))|(\[\])|(\{\})", "", text)
    text = re.sub(r"(as shown below|[Ss]ee figure below):*\-*", "", text)
    text = re.sub(r"([,;:])(\w)", r"\1 \2", text)
    text = re.sub(r"\ue000", "", text, re.UNICODE)
    return text.strip()


def extract_clean_text_from_docx(docx_path: Path) -> list[str]:
    """Read visible paragraph text from a DOCX while skipping tables and drawings."""
    require_dependency(docx, "python-docx", "docx")

    try:
        doc = docx.Document(docx_path)
    except Exception as exc:
        raise RuntimeError(f"Failed to read DOCX file: {docx_path}") from exc

    output_text: list[str] = []

    for block in doc.element.body:
        if block.tag.endswith("tbl"):
            continue

        if not block.tag.endswith("p"):
            continue

        text_parts: list[str] = []
        for run in block.iter():
            if run.tag.endswith("drawing") or run.tag.endswith("pict"):
                continue
            if run.tag.endswith("t") and run.text:
                text_parts.append(run.text)

        raw_text = " ".join(text_parts).strip()
        if not raw_text:
            continue

        cleaned = clean_and_normalize(raw_text)
        if cleaned:
            output_text.append(cleaned)

    return output_text


def save_list_to_txt(lines: Sequence[str], output_txt_path: Path) -> None:
    output_txt_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def batch_process_docx(input_dir: Path, output_dir: Path) -> list[Path]:
    """Convert all DOCX files in a directory into cleaned TXT files."""
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    txt_files: list[Path] = []

    docx_files = sorted(path for path in input_dir.iterdir() if path.suffix.lower() == ".docx")
    if not docx_files:
        raise FileNotFoundError(f"No DOCX files found in: {input_dir}")

    for docx_path in docx_files:
        txt_path = output_dir / f"{docx_path.stem}_clean.txt"
        LOGGER.info("Processing %s", docx_path.name)
        clean_lines = extract_clean_text_from_docx(docx_path)
        save_list_to_txt(clean_lines, txt_path)
        txt_files.append(txt_path)
        LOGGER.info("Saved cleaned text to %s", txt_path)

    return txt_files


def split_into_paragraphs(file_path: Path) -> list[str]:
    """Collapse cleaned lines into paragraphs while skipping simple section headers."""
    paragraphs: list[str] = []
    current_paragraph: list[str] = []

    with file_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()

            if SECTION_HEADER_PATTERN.match(line):
                continue

            if not line:
                if current_paragraph:
                    paragraphs.append(" ".join(current_paragraph).strip())
                    current_paragraph = []
                continue

            cleaned_line = clean_and_normalize(line)
            if cleaned_line:
                current_paragraph.append(cleaned_line)

    if current_paragraph:
        paragraphs.append(" ".join(current_paragraph).strip())

    return paragraphs


def build_corpus(txt_files: Iterable[Path]) -> list[ParagraphChunk]:
    """Build a list of paragraph chunks from cleaned TXT files."""
    corpus: list[ParagraphChunk] = []

    for file_path in txt_files:
        paragraphs = split_into_paragraphs(file_path)
        for index, paragraph in enumerate(paragraphs):
            corpus.append(
                ParagraphChunk(
                    document=file_path.name,
                    paragraph_id=index,
                    text=paragraph,
                )
            )

    return corpus


def ensure_punkt(download: bool = False) -> None:
    """Ensure the NLTK punkt tokenizer is available before retrieval runs."""
    require_dependency(nltk, "nltk", "nltk")
    require_dependency(word_tokenize, "nltk", "nltk")

    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        if not download:
            raise RuntimeError(
                "Missing NLTK resource 'punkt'. Run with --download-nltk-data once "
                "or install it manually before using retrieval."
            ) from None
        nltk.download("punkt", quiet=True)
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError as exc:
            raise RuntimeError("Failed to download NLTK resource 'punkt'.") from exc


def simple_retriever(query: str, corpus: Sequence[ParagraphChunk], top_k: int = 5) -> list[ParagraphChunk]:
    """Return top paragraphs ranked by token overlap with the query."""
    require_dependency(word_tokenize, "nltk", "nltk")

    q_tokens = set(word_tokenize(query.lower()))
    scored: list[tuple[int, ParagraphChunk]] = []

    for item in corpus:
        p_tokens = set(word_tokenize(item.text.lower()))
        score = len(q_tokens & p_tokens)
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:top_k]]


def format_context(retrieved_chunks: Sequence[ParagraphChunk]) -> str:
    """Format retrieved paragraphs into a prompt-ready context block."""
    return "\n".join(
        f"[{item.document}#para{item.paragraph_id}] {item.text}"
        for item in retrieved_chunks
    )


def get_deepseek_client(api_key: str | None = None, base_url: str = DEFAULT_BASE_URL) -> Any:
    """Create an OpenAI-compatible client configured for DeepSeek."""
    require_dependency(OpenAI, "openai", "openai")

    resolved_api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
    if not resolved_api_key:
        raise RuntimeError("Set DEEPSEEK_API_KEY or pass --api-key before calling the API.")

    return OpenAI(base_url=base_url, api_key=resolved_api_key)


def rag_ask_api(
    query: str,
    corpus: Sequence[ParagraphChunk],
    model_name: str = DEFAULT_MODEL,
    top_k: int = 6,
    api_key: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
) -> str:
    """Retrieve context from the local corpus and ask the DeepSeek API."""
    if not corpus:
        raise RuntimeError("Corpus is empty. Process at least one document before querying.")

    retrieved = simple_retriever(query, corpus, top_k=top_k)
    if not retrieved:
        raise RuntimeError("No relevant paragraphs were retrieved for the query.")

    context = format_context(retrieved)
    system_prompt = (
        "You are an expert in 4G/5G NAS and RRC protocols.\n"
        "Below are relevant spec paragraphs.\n"
        "Answer only using this context.\n\n"
        f"{context}"
    )

    client = get_deepseek_client(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        temperature=0.1,
    )

    message = response.choices[0].message.content
    if not message:
        raise RuntimeError("The API returned an empty response.")
    return message


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract telecom specs from DOCX files and query them with DeepSeek."
    )
    parser.add_argument(
        "--input-dir",
        default="input_docx",
        help="Directory containing source .docx specification files.",
    )
    parser.add_argument(
        "--output-dir",
        default="clean_txt",
        help="Directory used to store cleaned .txt files.",
    )
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help="Question to ask after building the local corpus.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="DeepSeek chat model name.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="OpenAI-compatible API base URL.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key override. Defaults to DEEPSEEK_API_KEY.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=6,
        help="Number of retrieved paragraphs to include in the prompt.",
    )
    parser.add_argument(
        "--download-nltk-data",
        action="store_true",
        help="Download missing NLTK tokenizer data before retrieval.",
    )
    parser.add_argument(
        "--process-only",
        action="store_true",
        help="Only generate cleaned text files and the local corpus; skip the API call.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser.parse_args()


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    if args.top_k < 1:
        print("Error: --top-k must be at least 1.", file=sys.stderr)
        return 2

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    try:
        txt_files = batch_process_docx(input_dir, output_dir)
        corpus = build_corpus(txt_files)
        print(f"Processed {len(txt_files)} document(s) into {len(corpus)} paragraph chunk(s).")

        if args.process_only:
            return 0

        ensure_punkt(download=args.download_nltk_data)
        answer = rag_ask_api(
            query=args.query,
            corpus=corpus,
            model_name=args.model,
            top_k=args.top_k,
            api_key=args.api_key,
            base_url=args.base_url,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("\nAnswer:\n")
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
