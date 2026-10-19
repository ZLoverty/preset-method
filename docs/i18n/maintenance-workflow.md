# i18n 维护与发布流程

英文源文档位于 `sop/`，顺序由 `sop/pdf-order.txt` 控制。翻译记忆库和术语表分别是：

- `i18n/memory/zh-CN.json`
- `i18n/glossary.json`

项目提供统一脚本 `scripts/i18n-workflow.py`，自动填充这些路径、运行目录和输出文件名。所有命令都应在仓库根目录执行。

## 最短工作流

修改 `sop/` 后，必要时同步更新 `sop/pdf-order.txt`、术语表和 `.env` 中的 `PDF_VERSION`。然后创建运行目录：

```bash
python scripts/i18n-workflow.py plan --run-name 2026-10-19
```

如需调用翻译模型：

```bash
python scripts/i18n-workflow.py run --run-name 2026-10-19 --model deepseek-chat
```

`run` 会读取 `.env` 中的 API 配置，并生成：

```text
tmp/i18n-runs/2026-10-19/candidates.json
```

执行本地 QA：

```bash
python scripts/i18n-workflow.py check --run-name 2026-10-19
```

打开审核 UI：

```bash
python scripts/i18n-workflow.py review --run-name 2026-10-19
```

浏览器访问 `http://127.0.0.1:8765`。审核 UI 会直接更新该运行目录中的 `checked-candidates.json`，并可将通过的译文导入 TM。

批量导入所有 QA 通过的候选：

```bash
python scripts/i18n-workflow.py import --run-name 2026-10-19
```

## 发布前检查与构建

严格检查翻译覆盖率：

```bash
python scripts/i18n-workflow.py build-check --run-name 2026-10-19
```

报告写入 `tmp/i18n-runs/2026-10-19/strict-report.json`。只有报告状态为 `passed`、未翻译段落为零且没有 issues，才可以发布。

生成中文 PDF：

```bash
python scripts/i18n-workflow.py build
```

临时覆盖版本号或输出路径：

```bash
python scripts/i18n-workflow.py build --version v2026.10 --output dist/sop-zh-CN-v2026.10.pdf
```

## 参数与安全边界

- `I18N_RUN_NAME` 可作为 `--run-name` 的默认值。
- `I18N_MODEL` 可作为 `run --model` 的默认值。
- `I18N_ENDPOINT` 可作为翻译服务 endpoint 的默认值。
- API key 只放在 `.env`，不要提交 Git。
- `plan`、`check`、`build-check` 和 `build` 不会调用翻译 API。
- `run` 是唯一会调用外部翻译服务的步骤；它支持断点续跑，重复执行同一运行目录即可继续。
- `import` 只导入 QA 通过的候选，不会自动覆盖已批准的 TM 记录。
- `run-name` 只能是单层目录名，避免意外写入 `tmp/i18n-runs` 之外的位置。

## 低层命令

包装脚本没有覆盖的诊断或审核操作，继续使用原始 CLI：

```bash
python -m sop_i18n tm status --order-file sop/pdf-order.txt
python -m sop_i18n glossary extract --jobs tmp/i18n-runs/<run-name>/translation-jobs.json
```

提交前运行：

```bash
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q sop_i18n scripts tests
git diff --check
```
