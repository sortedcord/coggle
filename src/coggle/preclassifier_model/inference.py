from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

import torch
from transformers import AutoTokenizer

from coggle.preclassifier_model.dataset import ID_TO_ROLE, ROLES
from coggle.preclassifier_model.model import SpanRoleClassifier


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MAX_LENGTH = 32


class SpanRole(str, Enum):
    TARGET = "target"
    DESTINATION = "destination"
    CONSTRAINT = "constraint"
    ATTRIBUTE = "attribute"


@dataclass
class ClassifiedSpan:
    tokens: list        # original spaCy token objects
    role: SpanRole
    text: str
    confidence: float   # softmax probability of the predicted class

    def __repr__(self) -> str:
        return f"ClassifiedSpan(role={self.role.value!r}, text={self.text!r}, confidence={self.confidence:.2f})"


class SpanRoleInference:
    """
    Loads the trained classifier and exposes a clean interface
    that accepts spaCy token lists as produced by the span splitter.
    """

    def __init__(self, checkpoint_path: str, device: str | None = None):
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))

        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

        self.model = SpanRoleClassifier(model_name=MODEL_NAME, num_classes=len(ROLES))
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()

    def _span_to_text(self, span: list) -> str:
        """Reconstruct plain text from a list of spaCy tokens."""
        return " ".join(t.text for t in span)

    def classify_span(self, span: list) -> ClassifiedSpan:
        """Classify a single span (list of spaCy tokens) into a role."""
        text = self._span_to_text(span)

        encoding = self.tokenizer(
            text,
            max_length=MAX_LENGTH,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        with torch.no_grad():
            logits = self.model(input_ids, attention_mask)
            probs = torch.softmax(logits, dim=-1)
            pred_id = probs.argmax(dim=-1).item()
            confidence = probs[0, pred_id].item()

        role = SpanRole(ID_TO_ROLE[pred_id])
        return ClassifiedSpan(tokens=span, role=role, text=text, confidence=confidence)

    def classify_spans(self, spans: list[list]) -> list[ClassifiedSpan]:
        """
        classify a list of spans as produced by the span splitter
        uses a single forward pass (more efficient it turns out)
        """
        if not spans:
            return []

        texts = [self._span_to_text(span) for span in spans]

        encoding = self.tokenizer(
            texts,
            max_length=MAX_LENGTH,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        with torch.no_grad():
            logits = self.model(input_ids, attention_mask)
            probs = torch.softmax(logits, dim=-1)
            pred_ids = probs.argmax(dim=-1).tolist()
            confidences = probs.max(dim=-1).values.tolist()

        results = []
        for span, pred_id, confidence in zip(spans, pred_ids, confidences):
            role = SpanRole(ID_TO_ROLE[pred_id])
            text = self._span_to_text(span)
            results.append(ClassifiedSpan(tokens=span, role=role, text=text, confidence=confidence))

        return results