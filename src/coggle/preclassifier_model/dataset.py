from __future__ import annotations
import csv
from dataclasses import dataclass
from torch.utils.data import Dataset
from transformers import AutoTokenizer


ROLES = ["target", "destination", "constraint", "attribute"]
ROLE_TO_ID = {role: idx for idx, role in enumerate(ROLES)}
ID_TO_ROLE = {idx: role for role, idx in ROLE_TO_ID.items()}


@dataclass
class SpanSample:
    text: str
    label: int


class SpanRoleDataset(Dataset):
    def __init__(self, samples: list[SpanSample], tokenizer, max_length: int = 32):
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        encoding = self.tokenizer(
            sample.text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "label": sample.label,
        }


def load_csv(path: str) -> list[SpanSample]:
    samples = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row["text"].strip()
            role = row[" role"].strip().lower()
            if role not in ROLE_TO_ID:
                raise ValueError(f"Unknown role '{role}' in dataset. Expected one of {ROLES}")
            samples.append(SpanSample(text=text, label=ROLE_TO_ID[role]))
    return samples


def split_dataset(samples: list[SpanSample], val_ratio: float = 0.2, seed: int = 42):
    import random
    random.seed(seed)
    shuffled = samples[:]
    random.shuffle(shuffled)
    split = int(len(shuffled) * (1 - val_ratio))
    return shuffled[:split], shuffled[split:]