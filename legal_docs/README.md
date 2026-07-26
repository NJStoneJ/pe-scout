# 德国法原文目录

PE-Scout 的 RAG 检索支持直接索引德国法原文 PDF/EPUB，实现真正的中德税法语义检索。

## 使用方法

将以下德国法 PDF 或 EPUB 文件放入本目录（文件名需匹配）：

| 文件名 | 说明 | RAG 作用 |
|--------|------|---------|
| `AO.pdf` | 德国租税通则 (Abgabenordnung) | PE 定义核心法源（§12-13） |
| `HGB.epub` 或 `HGB.pdf` | 德国商法典 (Handelsgesetzbuch) | PE 构成后合规义务（§238-263） |
| `EStG.pdf` | 德国所得税法 (Einkommensteuergesetz) | 个人所得税 + 预提税规则 |
| `KStG.pdf` | 德国企业所得税法 (Körperschaftsteuergesetz) | 企业所得税 + 有限纳税义务 |
| `UStG.pdf` | 德国增值税法 (Umsatzsteuergesetz) | 增值税登记与申报 |

## 备选方式

如果文件放在其他路径，设置环境变量：

```bash
# Windows
set GERMAN_LAW_DIR=C:\your\path\to\german_law

# Linux/Mac
export GERMAN_LAW_DIR=/your/path/to/german_law
```

## 无德国法文件时

即使没有以上文件，PE-Scout 仍可使用内置的 66 段中德税收法律知识库（协定全文、AO 定义、BEPS 规则、HGB 条款摘要）进行检索。添加德国法原文可将检索深度从"条文摘要"提升至"原著全文"。

## 版权声明

德国法原文受版权保护。请使用合法获取的版本。本工具不附带任何受版权保护的德国法全文。
