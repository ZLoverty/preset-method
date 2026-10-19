# v1.2 之后的变更

## 受影响的打印参数

- 冷却参数
- 热床温度
- 喷嘴温度（软材料）

## 操作方法相关改动

- 全材料冷却参数（风扇曲线）
- 增加热床温度测试方法
- 增加软材料专用温度塔方法
- 额外的验证模型库及推荐使用方法

## 其他改动

### 中文版翻译与构建

- 新增 `sop_i18n`，提供从英文 AST 提取、翻译任务规划、候选 QA、TM 审核到中文 PDF 的完整流水线。

# v1.1 发布说明

本版本基于 `v1.0`，重点改进了文档 PDF 的构建方式、排版效果和本地验证流程。

## 受影响的打印参数

## 操作方法相关改动

## 其他改动

### PDF 构建

- 将 PDF 生成逻辑从 Gitea workflow 中拆分到 [`scripts/build-pdf.sh`](scripts/build-pdf.sh)，减少 workflow 内的脚本复杂度。
- 构建脚本会自动读取 `docs/pdf-order.txt`，检查清单中的文档是否存在，并按清单顺序合并文档。
- 生成 PDF 时会忽略文档中单独成行的 `---` 分割线。
- 保留附录处理逻辑，并通过 `\appendix` 切换附录章节编号。
- 构建完成后会检查 PDF 文件是否成功生成且非空。

### PDF 排版

- 正文字体改为衬线字体：`Noto Serif`。
- 中文字体改为 `Noto Serif CJK SC`。
- 页边距调整为 `3cm`。
- 行距设置为 `1.2`。
- 正文字号设置为 `10.5pt`。
- 保留目录和章节编号。

### CI 与本地构建

- Gitea Actions workflow 现在通过共享脚本生成 PDF，构建逻辑与本地验证保持一致。
- README 增加了使用 PDF 工具镜像在本地生成 PDF 的说明。
- 本地生成的 PDF 输出到 `dist/`，不会自动上传 Release。
- 新增 `.gitignore`，忽略本地生成的 `dist/` 文件和 macOS 的 `.DS_Store` 文件。

### 升级注意事项

- PDF 工具镜像需要预装 Pandoc、XeLaTeX、Noto Serif 和 Noto Serif CJK 字体。
- 运行本地脚本前，需要确保 `pandoc` 和 `xelatex` 可执行文件存在。


