# P0 i18n / SOP build audit

审计目标：`preset-method` 当前仓库（提交 `3d8fafa`）。审计依据为
`docs/p0.md`。本次只读检查未修改 SOP、构建脚本、工作流或既有 PDF；新增文件仅限本目录。

## Audit Result

**PASS WITH WARNINGS**。仓库内容具备 Pandoc AST 翻译的技术基础；路径已统一到 `sop/`，Pandoc 解析和本地英文 PDF 构建均已通过。发布 workflow 未在仓库中核验，跨环境 PDF 可复现性仍有条件。

## Build Baseline

- 目标格式：Pandoc + XeLaTeX PDF；没有发现 HTML/EPUB 构建配置。
- 入口：`scripts/build-pdf.sh`；文档顺序文件实际为 `sop/pdf-order.txt`。
- 路径修正后，脚本可读取 `sop/pdf-order.txt`、校验 `sop/*.md` 并完成 Pandoc/XeLaTeX 构建。
- 后续重试已成功生成 `dist/preset-method-v2.0-pre.pdf`。
- `dist/` 中存在两个本地 PDF，但未发现它们由当前脚本成功生成，也不能据此宣称可复现。

## AST Findings

临时拼接实际 `sop/` 文档并使用脚本声明的 reader extensions 后，AST 节点包括：

`Header`、`Para`、`Plain`、`Strong`、`Emph`、`Link`、`Image`、`Figure`、`Table`、`BulletList`、`OrderedList`、`Code`、`BlockQuote`、`InlineMath`、`DisplayMath`、`RawBlock`、`LineBreak` 等。

特殊处理点：

- `$...$` / `$$...$$` 和 `\\text{}`、`\\pi` 等 LaTeX 必须整体保护。
- 图片路径和 alt/caption 分属不同字段；14 个被引用资源均在 `sop/assets/` 存在。
- 表格目前发现 1 张普通 Markdown pipe table；未发现 rowspan/colspan。
- `printer-calibration.md` 含 `\\appendix` RawBlock。
- 文档包含显式编号、重复编号、相对链接、视觉分隔线和代码样式参数；翻译不能按每个 `Str` 独立处理。
- AST round-trip 的块数量保持 187，但 JSON 对象不完全相等，不能把 round-trip 成功等同于渲染等价。

## Architecture Recommendation

翻译层应插在“源文档按既定顺序拼接/解析为 Pandoc AST”之后、PDF writer 之前；P1 先只做 AST-safe extraction/reconstruction，不接 AI、TM 持久化或 Actions。

推荐以 Header、段落/Plain、列表项、表格单元格、BlockQuote、图注和脚注为逻辑 segment；在 segment 内用 inline placeholder 保护数学、链接 URL/title、图片路径、代码、数字/单位、属性和 ID。重建后执行 AST 结构、placeholder、资源、链接和公式校验。

## Risks

### HIGH

1. **发布工作流不可核验**
   - 证据：README 第 74–83 行引用 `.gitea/workflows/release-docs-pdf.yml`，当前仓库未发现 `.gitea/` 或 `.github/` 工作流。
   - 影响：官方构建、字体安装和 release 上传行为未知，无法满足“官方构建不得调用 AI”及可复现性要求。
   - 缓解：恢复/提交实际 workflow，固定 Pandoc/XeLaTeX/字体版本和容器 digest，并在 CI 中执行路径检查与 no-op build。
2. **LaTeX/字体依赖未固定**：脚本硬编码 `Cambria`、`SimSun`；不同 runner 的字体、TeX 包和元数据会改变 PDF。
3. **源文档拼接会改变相对链接语境**：脚本把多个文件合并到临时文件后再解析；图片资源路径已改为 `sop`，但文档内部链接仍需在渲染环境中验证。
4. **源文本存在质量信号**：发现重复编号、拼写错误、公式/单位中疑似编码乱码和若干文档内部链接；翻译系统应先把这些作为 source QA，而不是静默修复。

## P1 Readiness

**READY**。P1 的 AST extractor、protected-content、validation 和本地英文 PDF 构建均已验证。发布 workflow 和跨环境构建固定仍属于后续发布工程工作。

## Files Created

- `docs/i18n-audit/README.md`
- `docs/i18n-audit/01-repository-inventory.md`
- `docs/i18n-audit/02-build-pipeline.md`
- `docs/i18n-audit/03-ast-structure-audit.md`
- `docs/i18n-audit/04-baseline-verification.md`
- `docs/i18n-audit/05-ast-roundtrip.md`
- `docs/i18n-audit/06-proposed-architecture.md`
- `docs/i18n-audit/07-p1-specification.md`

## Acceptance checklist

- [x] Repository structure inspected
- [x] Build command and configuration inspected
- [x] Workflow references inspected; actual workflow **NOT VERIFIED**
- [x] Dependencies and filters documented
- [x] AST node types inventoried
- [x] Tables, captions/images, formulas and links examined
- [x] English build attempted
- [x] No-op AST round-trip tested on a temporary corrected-path input
- [x] Translation insertion point justified
- [x] P1 specification produced
- [x] Existing SOP Markdown and PDF artifacts unchanged
- [x] Build path references updated to the actual `sop/` source root
