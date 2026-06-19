# 技术问题与解决方式

本文件集中记录项目推进中反复可能遇到的技术问题、原因判断和处理方式，供后续 agent 优先检索，减少重复排查。

注意：技术问题记录可能过时。复用任何解决方式前，应先判断它是否仍适用于当前代码、工具、环境和实验阶段。如果记录不再适用，应更新状态和解决方式；如果会误导后续工作，应删除或移到归档区。

## 记录格式

每个问题建议按以下格式追加：

```markdown
## 问题标题

- 首次发现阶段：
- 状态：active / resolved / stale / archived
- 最后复核：
- 现象：
- 影响：
- 原因：
- 解决方式：
- 后续注意：
- 相关文件：
```

## 已知问题

## Python Path.glob 不支持绝对 glob pattern

- 首次发现阶段：Oracle Context 测试阶段
- 状态：resolved
- 最后复核：2026-06-19
- 现象：执行 `python scripts\validate_cases.py` 时，`Path.glob` 收到绝对路径 pattern 后抛出 `NotImplementedError: Non-relative patterns are unsupported`。
- 影响：默认 case glob 无法在 Windows 环境下发现 YAML case，导致 validator 不能运行。
- 原因：`pathlib.Path.glob()` 只支持相对 pattern；项目默认 case glob 在共享工具中被构造成了绝对路径。
- 解决方式：将 case 发现逻辑改为使用 `glob.glob(glob_pattern, recursive=True)` 处理 glob pattern，并继续用 `Path` 做后续路径归一化。
- 后续注意：后续脚本如果需要支持绝对 glob pattern，优先复用 `scripts/call_chain_common.py` 中的 `discover_case_files()`。
- 相关文件：`scripts/call_chain_common.py`

## 根目录中文验收文档读取乱码

- 首次发现阶段：项目初始化与文档确立阶段
- 状态：active
- 最后复核：2026-06-19
- 现象：PowerShell 使用默认读取方式查看 `考核题目与验收要求.md` 时，中文内容显示为乱码。
- 影响：无法可靠引用或修改该文件内容，误改可能破坏原始验收要求。
- 原因：疑似文件编码与当前终端默认解码方式不一致。
- 解决方式：暂不修改该文件。后续如需整理，应先确认原始编码，并使用明确编码读取和转换。
- 后续注意：不要直接按当前乱码输出重写该文件。
- 相关文件：`考核题目与验收要求.md`

## 当前目录 git status 未正常识别仓库

- 首次发现阶段：项目初始化与文档确立阶段
- 状态：resolved
- 最后复核：2026-06-19
- 现象：执行 `git status --short` 返回 `fatal: not a git repository`。
- 影响：不能依赖 git status 判断工作区改动，需要通过文件列表和内容读取确认变更。
- 原因：根目录存在 `.git` 目录，但目录为空，不包含有效 Git 仓库元数据。
- 解决方式：已执行 `git init` 重新初始化仓库，之后 `git status --short` 可正常返回未跟踪文件列表。
- 后续注意：如果后续再次出现类似问题，先检查 `.git` 是否为空或损坏，不要直接删除、重置或移动 `.git`。
- 相关文件：`.git`
