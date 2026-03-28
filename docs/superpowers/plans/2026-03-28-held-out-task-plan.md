# Held-Out Task Plan

Date: 2026-03-28
Repo: `C:\Users\sou35\Documents\repo-research\autoresearch-plus`
Status: implemented

## Step 1: Goal Alignment

`[架構視角 + 整合視角]`

在**不增加新機制**的前提下，用**最少自定義代碼**為 `autoresearch-plus` 增加一個 **held-out task**，測試 current harness 在**同 family held-out task** 上是否保有可遷移性。

## Step 2: Current State

`[架構視角 + 實作視角]`

### 可直接複用的部分

- 核心 loop 已經完整：
  - `proposal -> evaluate -> keep/discard -> ledger -> report -> benchmark`
  - `src/autoresearch_plus/engine.py`
  - `src/autoresearch_plus/loop.py`
- benchmark 基礎設施已完整：
  - 任務註冊、`--task` 過濾、subprocess trial isolation
  - `src/autoresearch_plus/benchmark.py`
  - `src/autoresearch_plus/cli.py`
- DL demo adapter 模板已存在，可直接複用：
  - `src/autoresearch_plus/dl_demo_adapters.py`
- 現有報告與評估框架已成型：
  - `docs/superpowers/plans/2026-03-27-frozen-evaluation-interim-report.md`

### 需要改動的部分

- 新增一個 held-out task artifact：
  - `task.py`
  - `eval.py`
- 在 DL adapter 裡增加一個對應 adapter 類
- 在 benchmark task registry 註冊新 task
- 補最小測試
- 更新 README 和 interim report

### 缺失的部分

- 缺一個**未參與既有收斂**的新任務，作為 held-out 證據
- 缺 held-out task 的 benchmark 結果，用來判斷系統是否仍然過度依賴 adapter-shaped fix space

## Step 3: Plan

`[架構視角]`

1. 選擇一個與現有 DL task 同形狀的 held-out 任務
   - ⚠️ 假設：同 family 的 held-out task 是目前最小且可信的泛化測試
   - ⚖️ Tradeoff：只能測同 family 泛化，不能測跨 family 泛化
   - ❓ 未知項：這個 held-out task 會不會太容易或太噪

2. 復用現有 DL adapter 模板，不新增新機制
   - ⚠️ 假設：核心問題是泛化，不是缺少新的 loop/beam/memory 機制
   - ⚖️ Tradeoff：仍然使用 fix catalog，不能直接證明 freeform unknown-method 能力
   - ❓ 未知項：held-out 任務是否仍然被現有 fix space 形狀主導

3. 用現有 benchmark protocol 跑 held-out task
   - ⚠️ 假設：`iterations=1`, `trials=3` 足以給出方向性信號
   - ⚖️ Tradeoff：不能觀察更高 budget 下的行為
   - ❓ 未知項：更高 budget 會不會改變 mode 排序

4. 將 held-out 結果與現有結論分開匯報
   - ⚠️ 假設：held-out 必須單列，不能混進既有已調過的 task 集
   - ⚖️ Tradeoff：報告會再多一層結構
   - ❓ 未知項：是否需要第二個 held-out task 才足夠支撐更強 claim

## Step 4: Multi-View Review

`[審查視角 主導]`

### 挑戰 1

- 這仍然是同 family 的 DL task，不是真正的 unknown-method problem。

### 回應

- `[整合視角]` 成立，但這一步的目標不是一步跨到真正 open-ended unknown-method；目標是用**最少代碼**先測「現有 search policy 能不能遷移到未見任務」。
- `[架構視角]` 如果連同 family held-out 都過不了，先談更自由的 freeform proposal 沒意義。
- 結論：保留此方案，但明確把它標註為 `held-out same-family generalization`，不是 broad unknown-method proof。

### 挑戰 2

- 既然 still 用 fix catalog，結果可能仍然主要反映 adapter 設計，而不是 LLM/strategy 能力。

### 回應

- `[實作視角]` 這個質疑成立，所以這一步的價值不是“證明通用 autoresearch 已成立”，而是“檢查 current harness 是否只會在已調任務上贏”。
- `[審查視角]` 如果 held-out 也輸，反而是更有價值的負結果。
- 方案修正：在報告裡明確把 held-out 結果解讀為“task-dependent / adapter-shaped evidence”，而不是泛化成功證據。

## Step 5: Implementation

`[實作視角 + 整合視角]`

### 新增文件

- `demo_wine_classification/task.py`
- `demo_wine_classification/eval.py`

### 接線修改

- `src/autoresearch_plus/dl_demo_adapters.py`
- `src/autoresearch_plus/loop.py`
- `src/autoresearch_plus/benchmark.py`
- `README.md`

### 測試修改

- `tests/test_dl_demo_adapters.py`
- `tests/test_benchmark.py`

### 報告修改

- `docs/superpowers/plans/2026-03-27-frozen-evaluation-interim-report.md`

### 可直接執行的驗證命令

```powershell
cd C:\Users\sou35\Documents\repo-research\autoresearch-plus
python -m unittest discover -s tests -v
python -m src.autoresearch_plus.cli benchmark --iterations 1 --trials 3 --task wine_classification
```

### 實際結果

- `single_step_random / chunked_prior`
  - `median_gain=0.583333`
- `llm_codex_no_memory`
  - `median_gain=0.500000`
- `llm_codex_memory_retry`
  - `median_gain=0.250000`

### 整合結論

- 這個 held-out task **沒有**顯示 LLM 廣泛泛化優勢
- 它反而強化了目前更保守、也更可信的判斷：
  - 系統目前仍是 **task-dependent**
  - 而且還有明顯 **adapter-shaped** 特徵
