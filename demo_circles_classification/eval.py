from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.optim as optim

from task import EPOCHS, HIDDEN_DIM, LEARNING_RATE, NOISE_STD, SECOND_HIDDEN_DIM


def build_dataset() -> tuple[torch.Tensor, torch.Tensor]:
    torch.manual_seed(42)
    n = 2000
    n_half = n // 2
    angles1 = torch.rand(n_half) * 2 * math.pi
    angles2 = torch.rand(n_half) * 2 * math.pi
    r1 = 1.0 + NOISE_STD * torch.randn(n_half)
    r2 = 2.0 + NOISE_STD * torch.randn(n_half)
    class1 = torch.stack([r1 * torch.cos(angles1), r1 * torch.sin(angles1)], dim=1)
    class2 = torch.stack([r2 * torch.cos(angles2), r2 * torch.sin(angles2)], dim=1)
    X = torch.cat([class1, class2], dim=0)
    y = torch.cat([torch.zeros(n_half, dtype=torch.long), torch.ones(n_half, dtype=torch.long)])
    perm = torch.randperm(n)
    return X[perm], y[perm]


def main() -> None:
    X, y = build_dataset()
    split = int(0.8 * X.size(0))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    model = nn.Sequential(
        nn.Linear(2, HIDDEN_DIM),
        nn.ReLU(),
        nn.Linear(HIDDEN_DIM, SECOND_HIDDEN_DIM),
        nn.ReLU(),
        nn.Linear(SECOND_HIDDEN_DIM, 2),
    )
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    for _ in range(EPOCHS):
        optimizer.zero_grad()
        logits = model(X_train)
        loss = criterion(logits, y_train)
        loss.backward()
        optimizer.step()

    with torch.no_grad():
        logits = model(X_test)
        acc = (logits.argmax(dim=1) == y_test).float().mean().item()

    print(f"SCORE={acc:.6f}")


if __name__ == "__main__":
    main()
