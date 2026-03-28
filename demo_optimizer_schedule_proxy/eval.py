from __future__ import annotations

import math

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from task import BASE_LR, EPOCHS, FINAL_LR_FRAC, HIDDEN_DIM, INPUT_DIM, NUM_CLASSES, WARMUP_RATIO


def make_dataset() -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    data = load_digits()
    features = StandardScaler().fit_transform(data.data).astype(np.float32)
    labels = data.target.astype(np.int64)
    train_x, val_x, train_y, val_y = train_test_split(
        features,
        labels,
        test_size=0.3,
        random_state=42,
        stratify=labels,
    )
    return (
        torch.tensor(train_x, dtype=torch.float32),
        torch.tensor(train_y, dtype=torch.long),
        torch.tensor(val_x, dtype=torch.float32),
        torch.tensor(val_y, dtype=torch.long),
    )


class ScheduleProxyModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(INPUT_DIM, HIDDEN_DIM),
            nn.ReLU(),
            nn.Linear(HIDDEN_DIM, NUM_CLASSES),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.net(features)


def lr_scale(step: int, total_steps: int, warmup_steps: int) -> float:
    if warmup_steps > 0 and step < warmup_steps:
        return (step + 1) / warmup_steps
    progress = 0.0 if total_steps == warmup_steps else (step - warmup_steps) / max(1, total_steps - warmup_steps)
    progress = min(max(progress, 0.0), 1.0)
    return FINAL_LR_FRAC + (1.0 - FINAL_LR_FRAC) * 0.5 * (1.0 + math.cos(math.pi * progress))


def main() -> None:
    torch.manual_seed(42)
    np.random.seed(42)

    train_x, train_y, val_x, val_y = make_dataset()
    model = ScheduleProxyModel()
    optimizer = optim.AdamW(model.parameters(), lr=BASE_LR)
    criterion = nn.CrossEntropyLoss()

    batch_size = 128
    steps_per_epoch = math.ceil(train_x.size(0) / batch_size)
    total_steps = EPOCHS * steps_per_epoch
    warmup_steps = int(total_steps * WARMUP_RATIO)
    step = 0

    for _ in range(EPOCHS):
        permutation = torch.randperm(train_x.size(0))
        for start in range(0, train_x.size(0), batch_size):
            indices = permutation[start : start + batch_size]
            xb = train_x[indices]
            yb = train_y[indices]
            current_lr = BASE_LR * lr_scale(step, total_steps, warmup_steps)
            for group in optimizer.param_groups:
                group["lr"] = current_lr
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
            step += 1

    with torch.no_grad():
        logits = model(val_x)
        accuracy = (logits.argmax(dim=1) == val_y).float().mean().item()

    print(f"SCORE={accuracy:.6f}")


if __name__ == "__main__":
    main()
