from __future__ import annotations
import torch
import torch.nn as nn
from transformers import AutoModel


class SpanRoleClassifier(nn.Module):
    """
    frozen MiniLM backbone with a trainable classification head.
    miniLM acts purely as a feature extractor — only the head is updated during training.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", num_classes: int = 4, dropout: float = 0.1):
        super().__init__()

        self.backbone = AutoModel.from_pretrained(model_name)

        # Freeze all backbone parameters
        for param in self.backbone.parameters():
            param.requires_grad = False

        hidden_size = self.backbone.config.hidden_size  # 384 for MiniLM-L6

        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes),
        )

    def _mean_pool(self, token_embeddings: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """mean pool over non-padding tokens to get a single span embedding."""
        mask_expanded = attention_mask.unsqueeze(-1).float()
        sum_embeddings = (token_embeddings * mask_expanded).sum(dim=1)
        sum_mask = mask_expanded.sum(dim=1).clamp(min=1e-9)
        return sum_embeddings / sum_mask

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            outputs = self.backbone(input_ids=input_ids, attention_mask=attention_mask)

        pooled = self._mean_pool(outputs.last_hidden_state, attention_mask)
        logits = self.classifier(pooled)
        return logits