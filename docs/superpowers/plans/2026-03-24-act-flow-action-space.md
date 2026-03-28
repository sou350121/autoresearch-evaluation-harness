# ACT Flow Action Space Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ACT-style chunked mutations and a heuristic flow-inspired prior to `autoresearch-plus` without changing its single-target, single-score, keep/discard contract.

**Architecture:** Introduce one chunk-selection layer and one lightweight prior layer ahead of the existing AST mutator. The loop still applies one concrete patch, runs one evaluation, and accepts or rejects against the previous accepted revision.

**Tech Stack:** Python 3.11, stdlib `ast`, `csv`, `json`, `unittest`

---

### Task 1: Add failing tests for chunking and prior behavior

**Files:**
- Create: `tests/test_chunking.py`
- Create: `tests/test_prior.py`
- Test: `tests/test_chunking.py`
- Test: `tests/test_prior.py`

- [ ] **Step 1: Write failing chunking tests**
- [ ] **Step 2: Run `python -m unittest tests.test_chunking -v` and verify failure**
- [ ] **Step 3: Write failing prior tests**
- [ ] **Step 4: Run `python -m unittest tests.test_prior -v` and verify failure**

### Task 2: Implement chunk derivation and chunk-aware mutation

**Files:**
- Create: `src/autoresearch_plus/chunking.py`
- Modify: `src/autoresearch_plus/mutator.py`
- Modify: `src/autoresearch_plus/models.py`

- [ ] **Step 1: Add chunk dataclasses and stable AST chunk extraction**
- [ ] **Step 2: Update mutation result models to include chunk metadata**
- [ ] **Step 3: Restrict mutation selection to a chosen chunk**
- [ ] **Step 4: Run chunking and mutator tests**

### Task 3: Implement heuristic flow prior

**Files:**
- Create: `src/autoresearch_plus/prior.py`
- Modify: `src/autoresearch_plus/models.py`
- Modify: `src/autoresearch_plus/ledger.py`

- [ ] **Step 1: Add prior config and state models**
- [ ] **Step 2: Compute chunk/operator weights from recent ledger rows**
- [ ] **Step 3: Persist prior-related metadata in results and traces**
- [ ] **Step 4: Run prior and ledger tests**

### Task 4: Integrate chunking and prior into the search loop

**Files:**
- Modify: `src/autoresearch_plus/config.py`
- Modify: `src/autoresearch_plus/loop.py`
- Modify: `src/autoresearch_plus/cli.py`
- Modify: `config/project.toml`

- [ ] **Step 1: Add `[chunking]` and `[prior]` config loading**
- [ ] **Step 2: Select a chunk before each mutation**
- [ ] **Step 3: Bias chunk and mutation choice with the prior**
- [ ] **Step 4: Emit chunk/prior details in CLI and trace output**
- [ ] **Step 5: Run the full test suite**

### Task 5: Update docs and run fresh end-to-end verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document chunked search and heuristic priors**
- [ ] **Step 2: Run `python -m unittest discover -s tests -v`**
- [ ] **Step 3: Run fresh `baseline`, `search --iterations 8`, and `report` in a clean temp copy**
- [ ] **Step 4: Record actual verification results before claiming completion**
