from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.datasets import make_friedman1
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from task import EPOCHS, HIDDEN_DIM, LEARNING_RATE, SECOND_HIDDEN_DIM


def main() -> None:
    torch.manual_seed(42)
    np.random.seed(42)

    X, y = make_friedman1(n_samples=1200, n_features=10, noise=1.0, random_state=42)
    X = X.astype("float32")
    y = y.astype("float32").reshape(-1, 1)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train).astype("float32")
    X_test = scaler.transform(X_test).astype("float32")

    X_train_t = torch.tensor(X_train)
    X_test_t = torch.tensor(X_test)
    y_train_t = torch.tensor(y_train)
    y_test_t = torch.tensor(y_test)

    model = nn.Sequential(
        nn.Linear(X_train.shape[1], HIDDEN_DIM),
        nn.ReLU(),
        nn.Linear(HIDDEN_DIM, SECOND_HIDDEN_DIM),
        nn.ReLU(),
        nn.Linear(SECOND_HIDDEN_DIM, 1),
    )
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    batch_size = 128
    for _ in range(EPOCHS):
        perm = torch.randperm(X_train_t.size(0))
        for i in range(0, X_train_t.size(0), batch_size):
            idx = perm[i : i + batch_size]
            xb = X_train_t[idx]
            yb = y_train_t[idx]
            optimizer.zero_grad()
            pred = model(xb)
            loss = criterion(pred, yb)
            loss.backward()
            optimizer.step()

    with torch.no_grad():
        pred = model(X_test_t)
        ss_res = torch.sum((y_test_t - pred) ** 2)
        ss_tot = torch.sum((y_test_t - y_test_t.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot

    print(f"SCORE={float(r2):.6f}")


if __name__ == "__main__":
    main()
