from __future__ import annotations
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from transformers import AutoTokenizer
from sklearn.metrics import classification_report

from coggle.preclassifier_model.dataset import load_csv, split_dataset, SpanRoleDataset, ID_TO_ROLE, ROLES
from coggle.preclassifier_model.model import SpanRoleClassifier


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DATA_PATH = "training_dataset.csv"
SAVE_PATH = "src/coggle/preclassifier_model/span_role_classifier.pt"

EPOCHS = 20
BATCH_SIZE = 16
LEARNING_RATE = 1e-3
DROPOUT = 0.1
MAX_LENGTH = 32
VAL_RATIO = 0.2
SEED = 42


def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # data
    samples = load_csv(DATA_PATH)
    train_samples, val_samples = split_dataset(samples, val_ratio=VAL_RATIO, seed=SEED)
    print(f"Train: {len(train_samples)} | Val: {len(val_samples)}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    train_dataset = SpanRoleDataset(train_samples, tokenizer, max_length=MAX_LENGTH)
    val_dataset = SpanRoleDataset(val_samples, tokenizer, max_length=MAX_LENGTH)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE)

    # model
    model = SpanRoleClassifier(model_name=MODEL_NAME, num_classes=len(ROLES), dropout=DROPOUT)
    model.to(device)

    # you can only train the classifier head 
    optimizer = torch.optim.Adam(model.classifier.parameters(), lr=LEARNING_RATE)
    criterion = nn.CrossEntropyLoss()

    best_val_acc = 0.0

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0
        for batch in train_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["label"].to(device)

            optimizer.zero_grad()
            logits = model(input_ids, attention_mask)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        avg_loss = total_loss / len(train_loader)

        # validator 2 
        model.eval()
        all_preds = []
        all_labels = []

        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels = batch["label"].to(device)

                logits = model(input_ids, attention_mask)
                preds = logits.argmax(dim=-1)

                all_preds.extend(preds.cpu().tolist())
                all_labels.extend(labels.cpu().tolist())

        correct = sum(p == l for p, l in zip(all_preds, all_labels))
        val_acc = correct / len(all_labels)

        print(f"Epoch {epoch:02d} | loss: {avg_loss:.4f} | val_acc: {val_acc:.4f}")

        # save the best model based on val accuracy 
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "val_acc": val_acc,
            }, SAVE_PATH)
            print(f"  → Saved best model (val_acc: {val_acc:.4f})")

    print(f"\nbest val accuracy: {best_val_acc:.4f}")
    print("\nclassification report (best model on val set):")

    checkpoint = torch.load(SAVE_PATH, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in val_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["label"].to(device)
            logits = model(input_ids, attention_mask)
            preds = logits.argmax(dim=-1)
            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())

    print(classification_report(
        all_labels,
        all_preds,
        target_names=ROLES,
    ))


if __name__ == "__main__":
    train()