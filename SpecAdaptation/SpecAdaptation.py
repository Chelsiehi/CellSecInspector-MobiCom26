import os
import re
import docx
import nltk
import torch
from datasets import Dataset
from transformers import (AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments,
                          DataCollatorForLanguageModeling, pipeline)
from peft import LoraConfig, get_peft_model, TaskType


nltk.download('punkt')


def clean_and_normalize(text):
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'(\n)+', '', text)
    text = re.sub(r'^[\.:·\-]', '', text)
    text = re.sub(r'^ ', '', text)
    text = re.sub(r'[\.:,;\-]*$', '', text)
    text = re.sub(r'(\(\))|(\[\])|(\{\})', '', text)
    text = re.sub(r'(as shown below|[Ss]ee figure below):*\-*', '', text)
    text = re.sub(r'([,;:])(\w)', r'\1 \2', text)
    text = re.sub(r'\ue000', '', text, re.UNICODE)
    return text.strip()


def extract_clean_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    output_text = []

    for block in doc.element.body:
        if block.tag.endswith("tbl"):
            continue

        if block.tag.endswith("p"):
            paragraph = block
            text_parts = []

            for run in paragraph.iter():
                if run.tag.endswith("drawing") or run.tag.endswith("pict"):
                    continue

                if run.tag.endswith("t"):
                    text_parts.append(run.text)

            raw_text = " ".join(text_parts).strip()

            if raw_text:
                cleaned = clean_and_normalize(raw_text)
                if cleaned:
                    output_text.append(cleaned)

    return output_text


def save_list_to_txt(lines, output_txt_path):
    with open(output_txt_path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def batch_process_docx(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    txt_files = []

    for filename in os.listdir(input_folder):
        if filename.lower().endswith(".docx"):
            docx_path = os.path.join(input_folder, filename)
            txt_path = os.path.join(output_folder, filename.replace(".docx", "_clean.txt"))
            txt_files.append(txt_path)

            print(f"[DOCX] Processing {filename}...")

            clean_lines = extract_clean_text_from_docx(docx_path)
            save_list_to_txt(clean_lines, txt_path)

            print(f"[TXT] Saved → {txt_path}\n")

    return txt_files


def split_into_paragraphs(file_path):
    paragraphs = []
    current_paragraph = ""

    section_header_pattern = re.compile(r'^\d+(\.\d+)*\s+[A-Za-z]+.*$')

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()

            if section_header_pattern.match(line):
                continue

            if not line:
                if current_paragraph:
                    paragraphs.append(current_paragraph.strip())
                    current_paragraph = ""
                continue

            cleaned_line = clean_and_normalize(line)
            if cleaned_line:
                current_paragraph += cleaned_line + " "

    if current_paragraph:
        paragraphs.append(current_paragraph.strip())

    return paragraphs


def tokenize_and_chunk(paragraphs, tokenizer, max_length=512):
    inputs = tokenizer(
        paragraphs,
        add_special_tokens=True,
        truncation=True,
        max_length=max_length,
        return_overflowing_tokens=True,
        return_length=True
    )
    return [
        {"input_ids": ids, "attention_mask": mask}
        for ids, mask in zip(inputs["input_ids"], inputs["attention_mask"])
    ]



if __name__ == "__main__":

    input_folder = "input_docx"
    output_folder = "clean_txt"

    print("\n=========== STEP 1: DOCX → CLEAN TXT ===========")
    txt_files = batch_process_docx(input_folder, output_folder)

    print("Clean TXT files:", txt_files)

    print("\n=========== STEP 2: Build Training Corpus ===========")

    corpus = []
    for txt_path in txt_files:
        corpus.extend(split_into_paragraphs(txt_path))

    print(f"Total paragraphs collected: {len(corpus)}")
    print("Example paragraph:", corpus[0] if corpus else "EMPTY")


    print("\n=========== STEP 3: Load Tokenizer ===========")

    model_name = "deepseek-ai/DeepSeek-R1-Distill-Llama-8B"
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)

    print("\n=========== STEP 4: Tokenizing Corpus ===========")

    tokenized_chunks = tokenize_and_chunk(corpus, tokenizer)
    dataset = Dataset.from_dict({
        "input_ids": [chunk["input_ids"] for chunk in tokenized_chunks],
        "attention_mask": [chunk["attention_mask"] for chunk in tokenized_chunks]
    })

    print("Total chunks:", len(dataset))


    print("\n=========== STEP 5: Load Base Model ===========")

    base_model = AutoModelForCausalLM.from_pretrained(
        model_name,
        load_in_8bit=True,
        device_map="auto",
        low_cpu_mem_usage=True
    )

    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=8,
        lora_alpha=32,
        lora_dropout=0.1,
    )

    print("Applying LoRA...")
    model = get_peft_model(base_model, peft_config)


    print("\n=========== STEP 6: Start Training ===========")

    training_args = TrainingArguments(
        output_dir="./lora-finetuned-model",
        overwrite_output_dir=True,
        num_train_epochs=10,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        save_steps=50,
        save_total_limit=2,
        logging_steps=50,
        evaluation_strategy="steps",
        eval_steps=100,
        learning_rate=5e-5,
        fp16=True,
        report_to="none"
    )

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        eval_dataset=dataset,
        data_collator=data_collator
    )

    trainer.train()

    trainer.save_model("./lora-finetuned-model")


    print("\n=========== STEP 7: Generate Sample Output ===========")

    generation_pipeline = pipeline(
        "text-generation",
        model="./lora-finetuned-model",
        tokenizer=tokenizer,
        device_map="auto"
    )

    test_prompt = "The NAS protocol is used for"
    outputs = generation_pipeline(test_prompt, max_length=120, do_sample=True)

    print("\nGenerated Example:\n", outputs[0]["generated_text"])

    print("\n=========== ALL DONE ===========")
