"""
Loads the XLM-R model from a LOCAL folder (no Google Drive mount needed
in VS Code) and classifies article text into flood/other/rain/typhoon.

IMPORTANT: id2label below was empirically verified against the checkpoint
on 2026-06-22 — the model was saved with generic LABEL_0..LABEL_3 names,
so this mapping was reverse-engineered by testing known examples per class.
Indices 0, 2, 3 were confirmed with 3/3 unanimous matches each; index 1
("other") was confirmed by elimination + one clean unambiguous example.
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from dotenv import load_dotenv

load_dotenv()

MODEL_PATH = os.getenv("MODEL_PATH", "./models/xlmr_weather_model")

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)

id2label = {
    0: "flood",
    1: "other",
    2: "rain",
    3: "typhoon"
}

# Bake the corrected mapping into the model itself so future loads
# (here or anywhere else) carry the right labels automatically.
model.config.id2label = id2label
model.config.label2id = {v: k for k, v in id2label.items()}


def classify(text: str) -> dict:
    """Returns {'label': ..., 'confidence': ...} for the given text."""

    inputs = tokenizer(
        text,
        truncation=True,
        padding=True,
        max_length=512,
        return_tensors="pt"
    )

    with torch.no_grad():
        outputs = model(**inputs)

    probs = torch.softmax(outputs.logits, dim=1)
    confidence, pred = torch.max(probs, dim=1)

    return {
        "label": id2label[pred.item()],
        "confidence": confidence.item()
    }


def save_corrected_model():
    """Run this once to permanently bake the fixed labels into the checkpoint
    on disk, so you never have to re-apply this mapping by hand again."""
    model.save_pretrained(MODEL_PATH)
    tokenizer.save_pretrained(MODEL_PATH)
    print(f"Saved corrected id2label into {MODEL_PATH}")
