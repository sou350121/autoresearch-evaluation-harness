from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.datasets import make_moons
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from task import EPOCHS, HIDDEN_DIM, LEARNING_RATE, SECOND_HIDDEN_DIM


class CapacityBudgetModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(2, HIDDEN_DIM),
            nn.ReLU(),
            nn.Linear(HIDDEN_DIM, SECOND_HIDDEN_DIM),
            nn.ReLU(),
            nn.Linear(SECOND_HIDDEN_DIM, 2),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.net(features)


def make_dataset() -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    features, labels = make_moons(n_samples=1000, noise=0.35, random_state=42)
    features = StandardScaler().fit_transform(features).astype(np.float32)
    labels = labels.astype(np.int64)
    train_x, val_x, train_y, val_y = train_test_split(
        features,
        labels,
        test_size=0.35,
        random_state=42,
    )
    return (
        torch.tensor(train_x, dtype=torch.float32),
        torch.tensor(train_y, dtype=torch.long),
        torch.tensor(val_x, dtype=torch.float32),
        torch.tensor(val_y, dtype=torch.long),
    )


def main() -> None:
    torch.manual_seed(42)
    np.random.seed(42)

    train_x, train_y, val_x, val_y = make_dataset()
    model = CapacityBudgetModel()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    criterion = nn.CrossEntropyLoss()

    batch_size = 64
    for _ in range(EPOCHS):
        permutation = torch.randperm(train_x.size(0))
        for start in range(0, train_x.size(0), batch_size):
            indices = permutation[start : start + batch_size]
            xb = train_x[indices]
            yb = train_y[indices]
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()

    with torch.no_grad():
        logits = model(val_x)
        accuracy = (logits.argmax(dim=1) == val_y).float().mean().item()

    print(f"SCORE={accuracy:.6f}")


if __name__ == "__main__":
    main()
