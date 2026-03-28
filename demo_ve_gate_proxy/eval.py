from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from task import (
    EPOCHS,
    GATE_CHANNELS,
    GATE_INIT,
    HIDDEN_DIM,
    LEARNING_RATE,
    N_LAYER,
    SEQUENCE_LEN,
    TRAIN_SAMPLES,
    VAL_SAMPLES,
    VE_PATTERN,
    VOCAB_SIZE,
)


def has_ve(layer_idx: int, n_layer: int, pattern: str) -> bool:
    if pattern == "none":
        return False
    if pattern == "all":
        return True
    if pattern == "alternating":
        return layer_idx % 2 == (n_layer - 1) % 2
    raise ValueError(f"unsupported pattern: {pattern}")


def make_dataset(num_samples: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(42 + num_samples)
    tokens = rng.integers(0, VOCAB_SIZE, size=(num_samples, SEQUENCE_LEN), dtype=np.int64)
    value_scores = np.linspace(-1.3, 1.3, VOCAB_SIZE, dtype=np.float32)
    position_weights = np.linspace(0.6, 1.4, SEQUENCE_LEN, dtype=np.float32)
    cue_bonus = ((tokens[:, :-1] % 5) == 0) & ((tokens[:, 1:] % 3) == 1)
    signal = (value_scores[tokens] * position_weights[None, :]).sum(axis=1)
    signal += cue_bonus.sum(axis=1) * 1.25
    threshold = float(np.median(signal))
    labels = (signal > threshold).astype(np.int64)
    return tokens, labels


class VeGateBlock(nn.Module):
    def __init__(self, hidden_dim: int, gate_channels: int, use_ve: bool) -> None:
        super().__init__()
        self.main = nn.Linear(hidden_dim, hidden_dim)
        self.use_ve = use_ve
        self.gate_channels = gate_channels
        if use_ve:
            self.value_embed = nn.Embedding(VOCAB_SIZE, hidden_dim)
            self.ve_gate = nn.Linear(gate_channels, hidden_dim, bias=False)

    def reset_parameters(self) -> None:
        if not self.use_ve:
            return
        nn.init.normal_(self.value_embed.weight, mean=0.0, std=0.6)
        if GATE_INIT == "zero":
            nn.init.zeros_(self.ve_gate.weight)
        else:
            nn.init.normal_(self.ve_gate.weight, mean=0.0, std=0.9)

    def forward(self, x: torch.Tensor, token_ids: torch.Tensor) -> torch.Tensor:
        h = torch.relu(self.main(x))
        if self.use_ve:
            ve = self.value_embed(token_ids)
            gate = 2 * torch.sigmoid(self.ve_gate(x[..., : self.gate_channels]))
            h = h + gate * ve
        return x + h


class VeGateProxyModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.token_embed = nn.Embedding(VOCAB_SIZE, HIDDEN_DIM)
        self.blocks = nn.ModuleList(
            [
                VeGateBlock(HIDDEN_DIM, GATE_CHANNELS, has_ve(i, N_LAYER, VE_PATTERN))
                for i in range(N_LAYER)
            ]
        )
        self.head = nn.Linear(HIDDEN_DIM, 2)
        self.reset_parameters()

    def reset_parameters(self) -> None:
        nn.init.normal_(self.token_embed.weight, mean=0.0, std=0.35)
        nn.init.normal_(self.head.weight, mean=0.0, std=0.2)
        nn.init.zeros_(self.head.bias)
        for block in self.blocks:
            block.reset_parameters()

    def forward(self, token_ids: torch.Tensor) -> torch.Tensor:
        x = self.token_embed(token_ids)
        for block in self.blocks:
            x = block(x, token_ids)
        pooled = x.mean(dim=1)
        return self.head(pooled)


def main() -> None:
    torch.manual_seed(42)
    np.random.seed(42)

    train_x, train_y = make_dataset(TRAIN_SAMPLES)
    val_x, val_y = make_dataset(VAL_SAMPLES)

    train_x_t = torch.tensor(train_x, dtype=torch.long)
    train_y_t = torch.tensor(train_y, dtype=torch.long)
    val_x_t = torch.tensor(val_x, dtype=torch.long)
    val_y_t = torch.tensor(val_y, dtype=torch.long)

    model = VeGateProxyModel()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    criterion = nn.CrossEntropyLoss()

    batch_size = 64
    for _ in range(EPOCHS):
        perm = torch.randperm(train_x_t.size(0))
        for i in range(0, train_x_t.size(0), batch_size):
            idx = perm[i : i + batch_size]
            xb = train_x_t[idx]
            yb = train_y_t[idx]
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()

    with torch.no_grad():
        logits = model(val_x_t)
        acc = (logits.argmax(dim=1) == val_y_t).float().mean().item()

    print(f"SCORE={acc:.6f}")


if __name__ == "__main__":
    main()
