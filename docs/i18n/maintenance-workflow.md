# 中文版维护与发布流程

本文说明英文版文档发生修改后，如何重新生成并发布完整的中文版 PDF。

## 1. 修改英文源文档

英文源文档位于 `sop/`，构建顺序由以下文件控制：

```text
sop/pdf-order.txt
```

修改后先确认：

- 新文件是否加入 `sop/pdf-order.txt`；
- 图片、链接、公式和代码块是否仍然有效；
- 新增的固定术语是否需要加入 `i18n/glossary.json`；
- `.env` 中的 `PDF_VERSION` 是否需要更新。

版本配置示例：

```dotenv
PDF_VERSION=v2026.10
```

中文版构建会自动读取该值，并写入 PDF 的 release metadata 和构建报告。

## 2. 重新生成翻译任务

在仓库根目录执行：

```bash
python -m sop_i18n translate plan \
  --order-file sop/pdf-order.txt \
  --memory i18n/memory/zh-CN.json \
  --glossary i18n/glossary.json \
  --out tmp/translation-jobs.json \
  --force
```

规划器会根据当前 source key 生成任务。未变化且已有 approved TM 的内容会被复用；新增或发生变化的段落才需要重新翻译。

如果命令提示拒绝覆盖旧文件，确认确实要基于当前英文源重新规划后使用 `--force`。

## 3. 生成候选译文

### 使用 OpenAI 兼容 API

API key 可以放在 `.env` 中：

```dotenv
API_KEY=your-api-key
```

DeepSeek 示例：

```bash
python -m sop_i18n translate run \
  --jobs tmp/translation-jobs.json \
  --run-dir tmp/i18n-runs/<run-name> \
  --model deepseek-chat \
  --endpoint https://api.deepseek.com/v1/chat/completions \
  --glossary i18n/glossary.json
```

建议每次使用新的 `<run-name>`，例如 `deepseek-2026-10-16`。任务运行支持断点续跑，结果会写入：

```text
tmp/i18n-runs/<run-name>/candidates.json
```

如果使用其他 OpenAI 兼容服务，替换 `--endpoint` 和 `--model` 即可。API key 不要提交到 Git。

### 手工翻译

也可以直接编辑或生成符合 candidate schema 的 `candidates.json`，但必须保留正确的 `job_id`、placeholder 和 source key。推荐仍然使用本地 QA 和审核 UI，不要直接修改生产 TM。

## 4. 执行本地 QA

```bash
python -m sop_i18n translate check \
  --jobs tmp/translation-jobs.json \
  --candidates tmp/i18n-runs/<run-name>/candidates.json \
  --glossary i18n/glossary.json \
  --out tmp/i18n-runs/<run-name>/checked-candidates.json \
  --force
```

只有 QA 通过的 candidate 才允许导入 TM。重点关注：

- placeholder 是否完整且顺序合理；
- 数字、单位和数学公式是否保留；
- 代码、链接、图片路径和格式标记是否被破坏；
- glossary 术语是否使用一致；
- 是否混入模型解释、Markdown fence 或额外说明。

`NUMBER_UNIT_MISMATCH` 表示源文和译文识别出的数字/单位集合不同。placeholder 中的数字不会参与比较；如果源文确实没有某个数字，应检查模型是否错误添加了数字或单位。

## 5. 审核候选译文

启动本地审核 UI：

```bash
python -m sop_i18n review \
  --jobs tmp/translation-jobs.json \
  --candidates tmp/i18n-runs/<run-name>/candidates.json \
  --memory i18n/memory/zh-CN.json \
  --glossary i18n/glossary.json
```

打开：

```text
http://127.0.0.1:8765
```

推荐审核顺序：

1. 先处理 QA 失败项；
2. 查看“术语候选”，确认需要固定的术语并加入 glossary；
3. 修改候选译文并保存；
4. 使用“保存并导入 draft”进行中间保存；
5. 确认无误后点击“审核通过并批准”。

已存在 approved TM 的相同 source key 会被识别为 `duplicate`，不会重复出现在默认 candidate 列表，也不会覆盖原有译文。

如果英文文本只是重复出现但属于不同 occurrence，系统优先使用当前 occurrence 的 approved 记录；不要为了消除重复而手工删除已有 TM。

## 6. 检查翻译覆盖率

开发过程中可以使用默认的部分翻译模式：

```bash
python -m sop_i18n build --check-only \
  --order-file sop/pdf-order.txt \
  --memory i18n/memory/zh-CN.json \
  --report tmp/i18n-runs/<run-name>/partial-report.json
```

部分模式允许未翻译段落保留英文，报告状态通常为：

```text
passed_with_warnings
```

正式发布前必须使用严格模式：

```bash
python -m sop_i18n build --check-only \
  --translation-policy strict \
  --order-file sop/pdf-order.txt \
  --memory i18n/memory/zh-CN.json \
  --report tmp/i18n-runs/<run-name>/strict-report.json
```

只有以下条件全部满足，才表示中文版已经完整：

```text
status: passed
segments_untranslated: 0
issues: []
```

如果 strict 检查失败：

- `MISSING_TRANSLATION`：仍有段落没有 approved 译文；
- `AMBIGUOUS_TRANSLATION`：同一 source key 有多个可用 approved 译文，需要确认 occurrence 或清理冲突；
- `PLACEHOLDER_*`：占位符或保护内容不匹配；
- `STRUCTURE_CHANGED`：译文改变了 AST 结构，通常需要检查占位符是否被移动、删除或重复。

## 7. 构建中文版 PDF

严格检查通过后构建：

```bash
python -m sop_i18n build \
  --translation-policy strict \
  --order-file sop/pdf-order.txt \
  --memory i18n/memory/zh-CN.json \
  --output dist/sop-zh-CN.pdf \
  --report dist/i18n/zh-CN-report.json \
  --cjk-mainfont SimSun
```

版本默认来自 `.env` 的 `PDF_VERSION`。如需一次性覆盖：

```bash
python -m sop_i18n build \
  --version v2026.11 \
  --translation-policy strict \
  --order-file sop/pdf-order.txt \
  --memory i18n/memory/zh-CN.json \
  --output dist/sop-zh-CN.pdf
```

如使用其他环境文件：

```bash
python -m sop_i18n build \
  --env-file .env.release \
  --translation-policy strict \
  --order-file sop/pdf-order.txt \
  --memory i18n/memory/zh-CN.json \
  --output dist/sop-zh-CN.pdf
```

中文版标题为 `Polymaker 耗材预设调校指南`，目录标题为 `目录`。

构建完成后仍应人工检查 PDF 的中文字体、目录、标题、表格、图片、公式、分页、链接和中英文混排效果。

## 8. 提交前检查

建议在提交前执行：

```bash
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q sop_i18n tests
git diff --check
```

需要关注的文件：

- 英文源文档：`sop/`；
- 术语表：`i18n/glossary.json`；
- 生产 TM：`i18n/memory/zh-CN.json`；
- 构建报告：`dist/i18n/`；
- 中文 PDF：`dist/`。

`tmp/translation-jobs.json`、候选译文和运行报告主要是过程产物，是否提交应遵循项目当前的 Git 管理约定；API key、`.env` 私密内容和临时凭据不得提交。

## 9. 最简发布清单

```text
[ ] 修改 sop/ 英文源文档
[ ] 更新 pdf-order.txt（如有新增文件）
[ ] 更新 glossary.json（如有新增术语）
[ ] 更新 .env 中的 PDF_VERSION
[ ] translate plan --force
[ ] 生成 candidates.json
[ ] translate check
[ ] 审核并批准候选译文
[ ] build --check-only --translation-policy strict
[ ] build --translation-policy strict
[ ] 人工检查 PDF
[ ] 运行测试并检查 git diff
```
