from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from task import EPOCHS, HIDDEN_DIM, LEARNING_RATE, SECOND_HIDDEN_DIM


def main() -> None:
    torch.manual_seed(42)
    np.random.seed(42)

    dataset = load_wine()
    X = dataset.data.astype("float32")
    y = dataset.target

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train).astype("float32")
    X_test = scaler.transform(X_test).astype("float32")

    X_train_t = torch.tensor(X_train)
    X_test_t = torch.tensor(X_test)
    y_train_t = torch.tensor(y_train, dtype=torch.long)
    y_test_t = torch.tensor(y_test, dtype=torch.long)

    model = nn.Sequential(
        nn.Linear(X_train.shape[1], HIDDEN_DIM),
        nn.ReLU(),
        nn.Linear(HIDDEN_DIM, SECOND_HIDDEN_DIM),
        nn.ReLU(),
        nn.Linear(SECOND_HIDDEN_DIM, 3),
    )
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    batch_size = 128
    for _ in range(EPOCHS):
        perm = torch.randperm(X_train_t.size(0))
        for i in range(0, X_train_t.size(0), batch_size):
            idx = perm[i : i + batch_size]
            xb = X_train_t[idx]
            yb = y_train_t[idx]
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()

    with torch.no_grad():
        logits = model(X_test_t)
        acc = (logits.argmax(dim=1) == y_test_t).float().mean().item()

    print(f"SCORE={acc:.6f}")


if __name__ == "__main__":
    main()
