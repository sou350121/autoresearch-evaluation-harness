# Generic Task Adapter V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `autoresearch-plus` so the core search loop is task-adapter driven, while preserving the current numeric demo as the first adapter.

**Architecture:** Add a generic engine that operates on accepted-state snapshots, proposals, candidates, and eval results. Move demo-specific chunking/prior logic into a numeric demo adapter. Keep ledger, traces, accepted restoration, and git hygiene as durable core behavior.

**Tech Stack:** Python 3.11, stdlib `dataclasses`, `typing.Protocol`, `unittest`

---

### Task 1: Add failing tests for generic engine and scope snapshots

**Files:**
- Create: `tests/test_engine.py`
- Modify: `tests/test_ledger_cli.py`

- [ ] **Step 1: Write a failing fake-adapter engine test**
- [ ] **Step 2: Run `python -m unittest tests.test_engine -v` and verify failure**
- [ ] **Step 3: Write a failing multi-file scope snapshot round-trip test**
- [ ] **Step 4: Run `python -m unittest tests.test_ledger_cli -v` and verify failure**

### Task 2: Add generic adapter and engine primitives

**Files:**
- Create: `src/autoresearch_plus/adapter.py`
- Create: `src/autoresearch_plus/engine.py`
- Modify: `src/autoresearch_plus/models.py`

- [ ] **Step 1: Add generic state/proposal/candidate/eval dataclasses**
- [ ] **Step 2: Define `TaskAdapter` protocol**
- [ ] **Step 3: Implement generic baseline/search engine over the adapter**
- [ ] **Step 4: Run the new engine test**

### Task 3: Generalize snapshots and git commit scope

**Files:**
- Modify: `src/autoresearch_plus/ledger.py`
- Modify: `src/autoresearch_plus/git_ops.py`

- [ ] **Step 1: Add scope snapshot save/load helpers**
- [ ] **Step 2: Add multi-path commit helper**
- [ ] **Step 3: Keep old single-file helpers as compatibility wrappers**
- [ ] **Step 4: Run ledger tests**

### Task 4: Move demo logic into a numeric adapter

**Files:**
- Create: `src/autoresearch_plus/numeric_demo_adapter.py`
- Modify: `src/autoresearch_plus/config.py`
- Modify: `src/autoresearch_plus/loop.py`
- Modify: `config/project.toml`

- [ ] **Step 1: Add adapter selection and `edit_scope` config**
- [ ] **Step 2: Move current chunk/prior proposal logic into the numeric adapter**
- [ ] **Step 3: Make `run_baseline` and `run_search` call the generic engine with the adapter**
- [ ] **Step 4: Run the full test suite**

### Task 5: Update docs and verify end-to-end

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document the new task-adapter architecture**
- [ ] **Step 2: Re-run `python -m unittest discover -s tests -v`**
- [ ] **Step 3: Run a fresh `baseline`, `search`, and `benchmark` verification**
- [ ] **Step 4: Report actual results, including any regression versus the old demo path**
