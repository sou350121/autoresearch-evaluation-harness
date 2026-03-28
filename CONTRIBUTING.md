# Contributing to autoresearch-evaluation-harness

## English

### Getting Started

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `source venv/bin/activate` (on Windows: `venv\Scripts\activate`)
4. Install in development mode: `pip install -e .`
5. Install development dependencies: `pip install pytest mypy ruff`

### Running Tests

```bash
pytest
```

### Code Style

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting.

```bash
ruff check .
ruff format .
```

### Adding a New Task Adapter

1. Create a new file in `src/autoresearch_plus/` named `my_task_adapter.py`
2. Implement the `TaskAdapter` protocol with `propose()`, `materialize()`, `evaluate()`, `is_better()`, and `promote()` methods
3. Add tests in `tests/test_my_task_adapter.py`
4. Register the adapter in `src/autoresearch_plus/loop.py` (`_build_adapter` function)

### Submitting Changes

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes and commit with clear messages
3. Push to your fork and create a Pull Request
4. Ensure all tests pass before submitting

---

## 中文 (Chinese)

### 快速开始

1. 克隆仓库
2. 创建虚拟环境：`python -m venv venv`
3. 激活环境：`source venv/bin/activate`（Windows 上：`venv\Scripts\activate`）
4. 以开发模式安装：`pip install -e .`
5. 安装开发依赖：`pip install pytest mypy ruff`

### 运行测试

```bash
pytest
```

### 代码风格

我们使用 [Ruff](https://github.com/astral-sh/ruff) 进行代码检查和格式化。

```bash
ruff check .
ruff format .
```

### 添加新的任务适配器

1. 在 `src/autoresearch_plus/` 中创建新文件 `my_task_adapter.py`
2. 实现 `TaskAdapter` 协议，包含 `propose()`、`materialize()`、`evaluate()`、`is_better()` 和 `promote()` 方法
3. 在 `tests/test_my_task_adapter.py` 中添加测试
4. 在 `src/autoresearch_plus/loop.py` 的 `_build_adapter` 函数中注册适配器

### 提交更改

1. 创建功能分支：`git checkout -b feature/my-feature`
2. 进行更改并使用清晰的提交信息
3. 推送到你的 fork 并创建 Pull Request
4. 确保所有测试通过后再提交
