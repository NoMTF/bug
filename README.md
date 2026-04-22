<h1 align="center">bug</h1>

<p align="center">
  <strong>给 AI 编程 Agent 用的「真实 Bug 版本」生成器</strong>
  <br />
  备份干净源码，生成独立坏掉版本，让测试、审查和 Agent 一起去抓离谱问题。
</p>

<p align="center">
  <img alt="AI Skill" src="https://img.shields.io/badge/AI%20Skill-Codex%20%7C%20OpenClaw%20%7C%20Claude%20Code-111827?style=for-the-badge" />
  <img alt="License" src="https://img.shields.io/badge/License-MIT-16A34A?style=for-the-badge" />
  <img alt="Python" src="https://img.shields.io/badge/Python-3.8%2B-2563EB?style=for-the-badge" />
  <img alt="Node" src="https://img.shields.io/badge/Node-%E2%89%A514-10B981?style=for-the-badge" />
  <img alt="Mutates" src="https://img.shields.io/badge/Mutates-Py%20%7C%20JS%2FTS%20%7C%20Go%20%7C%20Rust%20%7C%20Java%20%7C%20Kotlin%20%7C%20Swift%20%7C%20C%23%20%7C%20C%2FC%2B%2B%20%7C%20Ruby%20%7C%20PHP-B91C1C?style=for-the-badge" />
</p>

<p align="center">
  <strong>一键安装：</strong>
</p>

```bash
curl -fsSL https://raw.githubusercontent.com/NoMTF/bug/main/install.sh | bash
```

<p align="center">
  <a href="#快速开始">快速开始</a>
  |
  <a href="#两种模式">两种模式</a>
  |
  <a href="#agent-接入">Agent 接入</a>
  |
  <a href="#安全模型">安全模型</a>
  |
  <a href="#mit-协议">MIT 协议</a>
</p>

---

<table>
  <tr>
    <td width="50%">
      <h3>真实制造 Bug</h3>
      <p>不是写几句假说明，而是直接变异源码：比较翻转、边界漂移、默认值误判、排序反向、共享引用泄漏。</p>
    </td>
    <td width="50%">
      <h3>不污染干净源码</h3>
      <p>普通项目会先复制成 bug 版本，再把 bug 注入到复制出的版本里，原项目保持干净。</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>适合 Agent 测试</h3>
      <p>Codex、OpenClaw、Claude Code 都能通过 skill/manifest 读懂这个项目的玩法。</p>
    </td>
    <td width="50%">
      <h3>可审计可恢复</h3>
      <p>每次生成都有 manifest、备份和变异记录，知道坏在哪里，也知道怎么还原。</p>
    </td>
  </tr>
</table>

## 项目定位

`bug` 是一个面向 AI 编程 Agent 的小插件和工具集。

它的目标很简单：把一个干净项目复制成一个独立的 bug 版本，然后往这个 bug 版本里注入真实、可观察、会让行为变坏的源码缺陷。它适合用来做代码审查训练、QA 演练、Agent 调试能力评估、bug hunt 游戏和教学 kata。

它追求的不是“明显写错”的玩具 bug，而是更像真实项目里会出现的事故：某次重构漏掉了 `await`，某个默认值从 `??` 被改成 `||`，某个防御性拷贝被悄悄变成共享引用，或者排序方向在一次需求理解里被写反。

它不是一个“假装有 bug”的 README 模板。生成后的 bug 版本会真的变坏。

## 快速开始

在任意项目旁边生成一个 bug 版本：

```bash
python scripts/make_bug_version.py ./my-project --count 12
```

运行后会得到：

```text
my-project/
my-project-clean-backup/
my-project-bug-version/
```

其中：

| 路径 | 作用 |
| --- | --- |
| `my-project/` | 原始干净源码，不被修改。 |
| `my-project-clean-backup/` | 干净源码备份。 |
| `my-project-bug-version/` | 被注入真实 bug 的版本。 |
| `BUG_VERSION_MANIFEST.json` | 记录生成时间、注入类型、文件路径、行号和改动前后内容。 |

再次运行同一条命令，会从干净源码重新刷新 bug 版本，并注入新的 bug：

```bash
python scripts/make_bug_version.py ./my-project --count 12
```

## 效果预览

干净源码：

```js
export function isSameUser(left, right) {
  return left.id === right.id;
}
```

bug 版本：

```js
export function isSameUser(left, right) {
  return left.id !== right.id;
}
```

Manifest 会记录这次变异：

```json
{
  "label": "INTENTIONAL_BUG_VERSION",
  "generated_by": "bug.make_bug_version",
  "bug": "comparison-flip",
  "before": "  return left.id === right.id;",
  "after": "  return left.id !== right.id;"
}
```

## 两种模式

### 1. Bug Version 模式

推荐模式。适合普通项目。

```bash
python scripts/make_bug_version.py ./my-project
```

它会：

| 步骤 | 行为 |
| --- | --- |
| 1 | 读取干净源码目录。 |
| 2 | 复制出 `clean-backup`。 |
| 3 | 复制出 `bug-version`。 |
| 4 | 只在 `bug-version` 里注入真实 bug。 |
| 5 | 写入 `BUG_VERSION_MANIFEST.json`。 |

### 2. Sandbox 原地注入模式

只适合训练目录、示例目录、fixture 或明确标记过的 throwaway 目录。

```bash
python scripts/inject_bug.py ./training/bug-kata-001 --count 2
python scripts/inject_bug.py ./sandbox/demo --bug missing-await
```

如果目录名不像 sandbox，可以放一个标记文件：

```bash
type nul > .bug-sandbox
python scripts/inject_bug.py ./my-copied-project --marker-file .bug-sandbox
```

## 支持的 Bug 类型

| 类型 | 变异方式 | 常见症状 |
| --- | --- | --- |
| `comparison-flip` | 翻转 `===`、`!==`、`==`、`!=`、`<=`、`>=` 等比较。 | 分支走反、权限判断反转、匹配逻辑错误。 |
| `boolean-operator` | 把 `&&` / `||` 或 `and` / `or` 换掉。 | 组合条件变宽或变窄，边缘输入误通过。 |
| `off-by-one` | 修改循环边界或 range 范围。 | 多跑一次、少跑一次、访问 undefined。 |
| `missing-await` | 移除一个 `await`。 | 异步顺序错乱、Promise 未解析、测试偶发失败。 |
| `falsy-default` | 把 `??` 改成 `||`。 | `0`、`""`、`false` 被误当成缺省值。 |
| `normalization-skip` | 移除 `.trim()` / `.strip()`。 | 带空格输入匹配失败。 |
| `case-sensitive` | 移除 `.toLowerCase()` / `.casefold()` 等。 | 原本不区分大小写的逻辑突然区分大小写。 |
| `slice-shift` | 把 slice 起点从 0 改成 1。 | 第一条数据被悄悄丢掉。 |
| `sort-direction` | 反转排序比较器或 `reverse`。 | 列表顺序看似合理但完全相反。 |
| `shared-reference` | 移除防御性拷贝。 | 后续修改污染原数据。 |
| `config-drift` | 调小 timeout、limit、retry、page size 等配置。 | 超时、分页缺失、重试不足。 |
| `property-typo` | 把 `.length` 写成 `.lenght`。 | JS/TS 中出现 undefined 相关错误。 |
| `optional-chain-drop` | 移除 `?.`。 | 少见空值输入触发运行时崩溃。 |
| `index-origin` | 把 Python `enumerate` 改成从 1 开始。 | 索引整体偏移。 |
| `default-drop` | 删除 Python `dict.get` 的默认值。 | 缺失 key 变成 `None`。 |
| `filter-leak` | 取消 `filter(Boolean)` / `filter(None, ...)`。 | 空值、无效值混进下游。 |
| `dedupe-drop` | 移除 `Set` / `set` 去重。 | 重复记录变多。 |
| `partial-match` | 前缀/后缀匹配变成包含匹配。 | 校验过宽。 |
| `rounding-drift` | `floor` / `ceil` / `round` 行为漂移。 | 价格、页数、布局尺寸偏差。 |
| `time-unit` | 时间单位换算倍率变错。 | 延迟、TTL、过期时间异常。 |
| `status-code-drift` | HTTP/status code 变成邻近值。 | 客户端判断错乱。 |
| `reset-skip` | 清理状态变成无效读取。 | 缓存、队列、状态残留。 |
| `order-drift` | append 变 prepend。 | 数据还在，但顺序错了。 |
| `clamp-inversion` | min/max 限幅逻辑漂移。 | 边界值被夹错。 |
| `flag-flip` | 常见布尔配置翻转。 | 功能开关状态反了。 |
| `truthy-empty` | 反转 Python 空值判断。 | 空输入被放行，正常输入被拒绝。 |
| `nil-check-flip` | **Go** 专属：翻转 `if err != nil`。 | 错误分支整个吞掉，看起来还走了成功路径。 |
| `unwrap-panic` | **Rust** 专属：`unwrap_or(...)` 变 `unwrap()`。 | 少见的 None/Err 情况变成运行时 panic。 |
| `equals-to-ref` | **Java / Kotlin** 专属：`.equals()` 变 `==`。 | 值比较退化成引用比较，字符串越像越诡异。 |
| `force-unwrap` | **Swift** 专属：`?? default` 变 `!`。 | 任何 nil optional 直接 crash。 |
| `random` | 从可用变异中随机选择。 | 每次生成都有新鲜的坏法。 |

支持文件类型（v1.1 起大幅扩展）：

```text
Python        .py
JavaScript    .js  .jsx  .mjs  .cjs
TypeScript    .ts  .tsx
Go            .go
Rust          .rs
Java          .java
Kotlin        .kt  .kts
Swift         .swift
C#            .cs
C / C++       .c  .cc  .cpp  .cxx  .h  .hpp  .hxx
Ruby          .rb
PHP           .php
```

Python 不是执行运行时的唯一入口。同时提供三种 CLI 入口，选你喜欢的：

```bash
# 1. Python 直接用
python scripts/make_bug_version.py ./my-project --profile messy --count 12

# 2. Bash / WSL / Git-Bash
bin/bug.sh bug-version ./my-project --profile messy --count 12

# 3. Node.js（也可用 npx）
node bin/bug.js bug-version ./my-project --profile messy --count 12
```

只有变异引擎是 Python。Bash 和 Node 入口是薄壳，用来让 Go/Rust/Java/C# 项目的作者不装 Python 以外任何东西就能用。

## 命令手册

### `make_bug_version.py`

```bash
python scripts/make_bug_version.py <source> [options]
```

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--out <path>` | `<source>-bug-version` | bug 版本输出目录。 |
| `--backup <path>` | `<source>-clean-backup` | 干净源码备份目录。 |
| `--bug <name>` | `random` | 指定 bug 类型。 |
| `--profile <name>` | `messy` | 随机注入强度：`soft`、`messy`、`chaos`。 |
| `--count <n>` | `3` | 变异文件数量。 |
| `--seed <n>` | 随机 | 固定随机种子，方便复现。 |
| `--keep-existing` | 关闭 | 不从源目录刷新，继续变异已有 bug 版本。 |

示例：

```bash
python scripts/make_bug_version.py ./app --profile soft --count 12
python scripts/make_bug_version.py ./app --profile messy --count 20
python scripts/make_bug_version.py ./app --profile chaos --count 30
python scripts/make_bug_version.py ./app --bug comparison-flip --count 3
python scripts/make_bug_version.py ./app --bug shared-reference --count 2
python scripts/make_bug_version.py ./app --bug falsy-default --count 2
python scripts/make_bug_version.py ./app --out ./app-bug-version --backup ./app-clean-backup
```

### `inject_bug.py`

```bash
python scripts/inject_bug.py <sandbox-target> [options]
```

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--bug <name>` | `random` | 指定 bug 类型。 |
| `--profile <name>` | `messy` | 随机注入强度。 |
| `--count <n>` | `1` | 变异文件数量。 |
| `--seed <n>` | 随机 | 固定随机种子。 |
| `--marker-file <name>` | `.bug-sandbox` | 允许原地注入的标记文件。 |
| `--report <path>` | `BUG_INJECTION_REPORT.json` | 注入报告路径。 |

## Agent 接入

### Codex

项目内置 Codex skill：

```text
SKILL.md
agents/openai.yaml
```

推荐提示词：

```text
Use $bug to create a bug version of this repository beside the original source.
```

中文也可以：

```text
使用 $bug，把这个仓库复制成一个独立的 bug 版本，并总结 manifest 里的变异点。
```

### OpenClaw / Claude Code

使用 portable manifest：

```text
bug.skilll
```

推荐提示词：

```text
加载 bug.skilll，为当前项目生成独立 bug-version 输出，不修改原始源码，然后根据 manifest 汇总注入的 bug。
```

## 仓库结构

```text
bug/
|-- README.md
|-- LICENSE
|-- package.json           # 让 npm / npx 能识别，提供 `bug` bin
|-- bug.md
|-- bug.skilll
|-- SKILL.md
|-- agents/
|   `-- openai.yaml
|-- bin/
|   |-- bug.js             # Node.js CLI 壳
|   `-- bug.sh             # Bash / POSIX CLI 壳
|-- scripts/
|   |-- inject_bug.py      # 变异引擎
|   `-- make_bug_version.py
`-- examples/
    |-- js-kata/
    |-- multilang-sandbox/ # Go / Rust / Java / Ruby 混合演示
    |-- version-source/
    |-- version-source-clean-backup/
    `-- version-source-bug-version/
```

## 内置示例

| 示例 | 说明 |
| --- | --- |
| `examples/js-kata` | 原地注入演示，包含一个真实 off-by-one bug。 |
| `examples/multilang-sandbox` | Go / Rust / Java / Ruby 混合项目的注入演示，用来验证多语言支持。 |
| `examples/version-source` | 干净源项目。 |
| `examples/version-source-clean-backup` | 由脚本生成的干净备份。 |
| `examples/version-source-bug-version` | 由脚本生成的 bug 版本。 |

Windows 查看：

```bash
type examples\version-source-bug-version\math.js
type examples\version-source-bug-version\BUG_VERSION_MANIFEST.json
```

macOS / Linux 查看：

```bash
cat examples/version-source-bug-version/math.js
cat examples/version-source-bug-version/BUG_VERSION_MANIFEST.json
```

## 安全模型

这个项目的乐趣是“真的造 bug”，但边界是“不要把干净源项目悄悄污染掉”。

| 规则 | 解释 |
| --- | --- |
| 普通项目只生成 bug 版本 | `make_bug_version.py` 不直接修改源目录。 |
| 原地注入只给 sandbox | `inject_bug.py` 会拒绝非 sandbox 目标。 |
| 每次生成都有记录 | manifest 会写明文件、行号、变异前后内容。 |
| 不做安全破坏 | 不制造凭证泄露、数据删除、权限削弱、部署破坏、供应链篡改。 |
| 对解题者可以隐蔽 | bug 可以藏得很自然，但项目持有人能从 manifest 里审计。 |

<details>
<summary><strong>为什么不是直接改原项目？</strong></summary>

直接污染原项目很容易变成不可控破坏。`bug` 选择生成独立 bug 版本：体验上仍然是真实坏代码，管理上则可以审计、删除、重建和恢复。

</details>

<details>
<summary><strong>后续怎么持续更新 bug 版本？</strong></summary>

再次运行：

```bash
python scripts/make_bug_version.py ./my-project --profile messy --count 12
```

脚本会从干净源目录刷新 bug-version，再注入新的 bug 集合。

</details>

## 开发校验

校验 Codex skill：

```bash
python path/to/skill-creator/scripts/quick_validate.py C:\bug
```

检查 Python 语法：

```bash
python -m py_compile scripts/inject_bug.py scripts/make_bug_version.py
```

检查 Bash 入口：

```bash
bash -n bin/bug.sh
"C:\Program Files\Git\bin\bash.exe" -n bug.skilll
```

检查 Node 入口：

```bash
node --check bin/bug.js
```

多语言冒烟测试（Go / Rust / Java / Ruby）：

```bash
python scripts/inject_bug.py examples/multilang-sandbox --count 8 --profile chaos --seed 42
```

## MIT 协议

本项目使用 MIT 协议，见 [LICENSE](LICENSE)。
