# riff 设计：外部搜索与 WebFetch

状态：已审定（2026-11-19）；第十节的待验证项在实现前逐项核实。

本文是 riff-plugins 第一个功能的整体设计。范围只有**外部搜索（`riff web search`）、网页抓取（`riff web fetch`）和它们
内部用的 Decision Provider**。代码检索、记忆、压缩已决定不做（2026-11-19），本文不涉及。

来源：nyan 的定稿设计与实现（基准 nyan `origin/master` 3227f768e）：

- `docs/nyan/external-search.md`（下称 **ES**）、`docs/nyan/external-search-provider-health.md`（下称 **PH**）；
- `docs/nyan/decision-provider.md`（下称 **DP**）；
- 代码 `src/services/web/**`、`src/services/decision/**`、`src/services/service_health.rs`、`src/services/rerank.rs`、
  `src/cli/web.rs`（`nyan web search|fetch`，nyan#134）。

nyan 将被废弃、不再开发；riff 直接复制上述代码，不与 nyan 共享 crate，也不为 nyan 保留兼容层。本文只写**与 nyan
不同的地方**和**新增的部分**；没提到的行为一律以 ES / PH / DP 为准，复制时连同其测试一起搬。

## 一、目标与边界

- 给 Claude Code、Codex、Antigravity、pi 提供同一套搜索与抓取能力：多 provider 聚合召回 + 精排、SSRF 安全抓取、
  原文快照与 `range` 续读、provider 回退、具名失败。
- 交付形态：PATH 上的一个预编译二进制 `riff`，插件只写命令（riff-plugins 已定的方案 P）。
- **prompt cache 命中率是第一约束**。riff 的输出作为工具结果进入宿主上下文，一旦进去就成为后续每轮的前缀，所以输出
  必须确定、可复现（第六节）。
- 不做：代码检索、记忆、压缩、宿主内的 cache 保活；不替宿主做权限审批（第七节）；`prompt` 抽取（ES 4.4，见 4.4）。

## 二、形态

### 2.1 二进制

- 单个二进制 `riff`，子命令 `riff web search|fetch`；以后的功能作为新的子命令加入。语言 Rust（复用约 1 万行代码与
  166 个测试；冷启动是单次调用成本的一部分，Rust 单二进制为毫秒级）。
- 仓库位置：`features/web/`（crate `riff-web`，库）+ 根目录 `riff` 二进制 crate（`features/` 下各功能的 CLI 汇总）。
  `features/README.md` 中"每个功能单独打 tag"改为单线 tag（第九节）。
- 平台：Linux x86_64 / aarch64（glibc 与 musl）、macOS x86_64 / aarch64、Windows x86_64。依赖 nyan 现有的
  reqwest（rustls + ring）、tokio、supermarkdown；PDF 依赖外部 `pdftotext`（缺失时 `content_type_denied: pdf conversion
  unavailable`，与 ES 4.2 相同）。

### 2.2 进程模型

**每次调用一个短进程**（`riff web search …` 跑完即退出），不做常驻 daemon。

- 理由：四家宿主都通过"执行一个命令 / 工具"接入；常驻进程要处理启动、升级、多用户与崩溃恢复，收益只是省掉每次
  的 TLS 建连。nyan 里依赖"进程常驻"的状态改为落盘（2.3）。
- 代价（接受）：每次调用都要重新建连。DP 1.3 实测首个请求含建连 0.96–1.16 s、复用后 0.40 s；搜索的 provider 扇出
  本来就是每次新建连接（nyan 也一样），不受影响。Decision Provider 的预热（DP 5.2）在短进程里没有意义，删除。
- MCP 模式（`riff mcp`，stdio）作为可选项保留在设计里，**首批不做**：pi 用自己的扩展工具接入，Claude Code 与 Codex
  用 skill + 命令行即可，Antigravity 文档未说明 MCP 工具能否替代其内置 web 工具。需要时它就是同一个库的另一个前端，
  进程内状态可以复用。

### 2.3 nyan 进程内状态的去向

nyan 里有六类状态只存在进程内存里（`OnceLock` / `Mutex` 单例），短进程里每次都会清零：

| 状态 | nyan 位置 | riff |
|---|---|---|
| 会话预算（搜索 / fetch 次数与字节、单 provider 次数、并发） | `services/web/budget.rs:64` | 改为**按 session id 落盘计数**（2.4） |
| 商业 provider 健康（冷却窗口） | `services/web/provider_health.rs:570` | 改为**落盘**，PH 第四节"不落盘"的前提（nyan 常驻）不再成立。文件按 provider 一个，写前加锁 |
| SearXNG / rerank / EMRank 健康（`ServiceHealth`） | `services/service_health.rs` | 同上，落盘；后台合成探测（启动不探测、到期由下一次使用触发探测）在短进程里改为"到期后下一次真实调用即试探"，与 PH 3.4 统一 |
| URL → 最新快照索引（TTL 15 min） | `services/web/snapshot.rs:104` | 删除内存索引，改为磁盘上的 `url-index/<sha256(规范化 URL)>`（内容：快照 hash + `fetched_at`）；TTL 不变 |
| 最近一次搜索的候选（给 `web.page_answers` 提示下一个 URL） | `services/web/search.rs:93` | 按 session id 落盘（只存 URL 列表） |
| 决策事后探针（30 min） | `services/decision/probe.rs:69` | 按 session id 落盘，保留 30 min |

落盘状态都放在 `$RIFF_HOME/state/`（第三节），只存计数、时间戳、hash 与 URL，不存 key、查询正文与页面正文。

**实现（`features/web/src/state.rs`）**：

- 文件：`state/sessions/<id>.json`（预算、决策预算、候选、探针）与 `state/health.json`（provider 与服务健康，所有会话
  共用）。URL 索引在 `url-index/`（上表）。
- 读写方式：命令开始时把文件内容装进 nyan 原有的进程内结构，结束时写回；进程内逻辑与其测试不变。会话文件的独占锁
  （标准库 `File::lock`）持有整条命令，所以**同一会话的并发调用串行执行**，计数不丢；这把 nyan 的
  `maxConcurrentSearches = 2` 在单个会话内实际降为 1（不同会话照常并行）。宿主在一个会话里几乎不并发搜索，接受；
  若实测有影响，再改为只在读改写时持锁。
- `health.json` 只在载入和写回时短暂加锁。写回时**只写本进程记录过结果的条目**（以毫秒级 `updatedAt` 是否变化判断），
  其余保留文件里的值，避免一个进程用它载入时的旧状态覆盖别的会话刚记下的冷却。
- 试探：短进程退出时会杀掉后台任务，所以 `ServiceHealth` 在 CLI 里开启"同步试探"——窗口到期后拿到许可的那次真实
  调用就是试探，结果照常记录；`probing` 不落盘。商业 provider 本来就是这种方式（PH 3.4）。
- 损坏或无法解析的状态文件按空状态处理并在下次写回时覆盖：状态是计数缓存，坏文件不能卡住后续所有命令。
- 7 天未更新的会话文件在写回时顺手删除。

### 2.4 会话

ES 3.5 的预算按"会话"计；riff 没有自己的会话，借宿主的：

- 会话 id 来源：`--session <id>` 参数，或环境变量 `RIFF_SESSION`。适配层负责传入宿主的会话 id：pi 扩展从
  `ctx` 取；Claude Code 与 Codex 的 hook 输入都带 `session_id`，由 SessionStart hook 设法让后续 shell 命令拿到它（两家
  的具体机制都待核实，第十节）；Antigravity hook 带 `conversationId`。
- **没有会话 id 时**：预算按"同一工作目录的 6 小时时段"计（键 = canonical cwd 的 hash + `floor(unix 时间 / 6 h)`），
  上限与 ES 3.5 相同。理由：没有会话就没有自然的清零点，按时间窗口是唯一不会无限累加、也不会每次清零的做法。实现用
  固定时段而不是滑动窗口：结果可预期、不需要记每次调用的时间；代价是时段边界处会提前清零。
- 会话 id 在路径里只用其 SHA-256 前缀（`s-<hex>`），宿主传什么都不会逃出 `state/sessions/`。
- `/clear` 之类的重置：ES 3.5 / PH 3.5 依赖 nyan 的 `/clear`。riff 提供 `riff web reset [--session <id>]` 清该会话的
  预算与 provider 冷却；适配层可在宿主的 `/clear` 对应事件（Claude Code SessionStart `source=clear`、pi
  `session_start` 的 `new`）上调用。

## 三、数据与配置

nyan 不再使用后，数据根只有 riff 自己的：

```
$RIFF_HOME                 默认 ~/.riff（XDG 环境下仍用 ~/.riff，不拆到 ~/.config 与 ~/.cache：一个目录便于两机复制与备份）
├── config.json            配置（3.2）
├── keys/<provider>        凭据，每个 provider 一个文件；目录 0700、文件 0600
├── web-snapshots/         快照，内容寻址，结构同 ES 4.3
├── url-index/             URL → 快照（2.3）
├── state/                 预算、健康、候选、探针（2.3）
└── decision/decisions.jsonl   决策日志（DP 第七节）
```

- **共用**：所有 agent、所有项目共用同一个 `$RIFF_HOME`（用户已定，2026-11-19）。快照本身已经是"临时文件 +
  原子改名"写入（`snapshot.rs:161-164`），多进程同时写同一快照不会损坏；`state/` 下的计数文件需要加锁（`fs2` 文件锁，
  锁粒度为单个文件），竞争只发生在同一会话的并发调用之间，持锁时间是一次读改写。
- **迁移**：首次运行时，若 `~/.riff` 不存在而 `~/.nyan/keys/` 下有 web provider 与 emrank 的 key、`~/.nyan/web-snapshots/`
  存在，**提示**一条可直接执行的复制命令（stderr），不自动复制、不读 `~/.nyan/settings.json`。nyan 的配置结构由用户按 3.2
  手动转写——只有几十行，自动转换不值得维护。

### 3.2 配置

`$RIFF_HOME/config.json`，结构为 nyan `settings.nyan.web` 与 `settings.nyan.decision` 的合并，去掉 nyan 特有的部分：

```jsonc
{
  "web": {
    "providers": { /* 同 ES 第五节；apiKeyFile 默认 $RIFF_HOME/keys/<name> */ },
    "search":    { /* 同 ES 第五节 */ "rerank": { "enabled": true, "url": "http://…:8091", "timeoutMs": 2000, "snippetChars": 500 } },
    "fetch":     { /* 同 ES 第五节 */ },
    "fetchFallback": ["firecrawl", "anysearch", "exa", "deepseek", "tavily"],
    "fetchVia": "proxy",
    "allowHosts": [], "denyHosts": [], "allowPorts": [],
    "maxBytes": 5242880, "maxReturnChars": 20000, "snapshotRetentionDays": 30
  },
  "decision": { /* 同 DP 第八节，points 只保留 web.*（第五节） */ }
}
```

与 nyan 的差异：

| 项 | nyan | riff |
|---|---|---|
| rerank 服务地址 | `nyan.retrieval.rerank.url`（与代码检索共用） | `web.search.rerank.url`（检索已不做） |
| `extractModel` | WebFetch `prompt` 抽取用 | 删除（4.4） |
| key 默认路径 | `~/.nyan/keys/<name>` | `$RIFF_HOME/keys/<name>`；另支持环境变量 `RIFF_KEY_<PROVIDER>`（大写，如 `RIFF_KEY_EXA`），文件优先 |
| 配置来源 | nyan settings 分层（用户 / 项目 / 策略） | 只有 `$RIFF_HOME/config.json`；`--config <path>` 可覆盖。不读项目目录里的配置：riff 被 agent 在任意仓库里调用，仓库里的文件不能改变 riff 的外发与 SSRF 行为（与 riff-plugins "仓库文本是数据"的规则一致） |
| `fetchVia` 默认 | `proxy` | `proxy`（用户已定，2026-11-19）；无代理变量时 `proxy_unconfigured`，不退直连 |
| 未配置任何 provider | WebSearch 不出现在工具列表 | `riff web search` 退出码 3，stderr 指向配置文件位置；适配层据此不注册 / 不推荐搜索 |

- 代理与 CA：沿用 nyan 的读法（`https_proxy` / `HTTPS_PROXY` / `http_proxy` / `HTTP_PROXY`，`socks5` 改写为 `socks5h`；
  自定义 CA 与 mTLS 的环境变量改名为 `RIFF_*`，对应关系在实现时从 `utils/proxy.rs`、`tls_provider` 抄出并列表）。

## 四、命令行接口

以 `nyan web`（`src/cli/web.rs`）为基础，**输出格式、退出码、续读命令的形态都沿用**，只做下表的改动。

### 4.1 用法

```
riff web search <query...> [--limit N] [--allow-domain D]... [--block-domain D]... [--json] [--timeout S] [--session ID] [--agent NAME]
riff web fetch  <url> [--range SPEC] [--query TEXT] [--json] [--timeout S] [--session ID] [--agent NAME]
riff web reset  [--session ID]
riff web doctor
riff init
riff hook <event> --agent <name>     适配层专用（7.1），不在 skill 里提
```

| 改动 | 原因 |
|---|---|
| 命令名 `nyan web` → `riff web`；续读命令 `[next segment: riff web fetch … --range N-]`（`cli/web.rs:533-536`） | 改名 |
| 新增 `--allow-domain` / `--block-domain` | nyan 的 WebSearch 工具有 `allowed_domains` / `blocked_domains`（ES 3.1），`nyan web` CLI 没暴露；宿主的 web 工具参数里有这两项，适配层要能透传 |
| 新增 `--session` | 2.4 |
| 新增 `--agent` | 决策日志的 `agent` 列（第五节） |
| 新增 fetch `--query` | nyan 的 `web.page_answers` 只在 WebFetch 带 `prompt` 时运行（`prompt` 是它唯一拿得到的查询），`nyan web fetch` 没有对应参数，所以 CLI 下这个决策点从不触发。riff 去掉了 `prompt` 抽取（4.4），改用 `--query` 提供查询：判定页面不含答案时在输出末尾加一行提示下一个候选，正文不变。**只在新抓取时判定**：命中 URL 索引或续读时不再问，同一快照的输出保持逐字节相同（6.1） |
| 新增 `reset`、`doctor` | `reset` 见 2.4；`doctor` 逐项报告配置、每个 provider 的 key 是否可读（不打印 key）、代理变量、`pdftotext`、rerank / SearXNG / EMRank 可达性，以及落盘的冷却状态，供用户与适配层排错 |
| `--timeout` 默认 15 s 不变 | 与 `nyan web` 相同；宿主执行命令的超时是否都大于 15 s 待核实（第十节第 1 条） |
| 单次 stdout 上限 30,000 字节不变（`cli/web.rs:20`） | 见 6.2 |

### 4.2 输出

- Markdown（默认）与 `--json` 两种，内容与 `nyan web` 相同：搜索结果每条 title / url / 来源 provider 与日期 / snippet，
  末尾 `[searched: …]` 与"线索不是来源"两行（ES 3.4）；抓取结果为头部一行 + `<web_content source=…>` 包裹的正文 +
  `[Showing chars a–b of N]` + 续读命令（ES 4.4）。
- stdout 只有结果；失败是 stderr 一行 + 具名原因 + 退出码（`0` 成功、`1` 其他、`2` 用法、`3` 配置、`4` 拒绝（SSRF、预算）、
  `5` 网络 / 全部 provider 失败、`124` 超时，`cli/web.rs:47-50`）。

### 4.3 skill

每个适配层都带同一个 skill（`skills/searching-the-web/`，遵循仓库的 skill 规则，描述里不出现任何 agent 专有名词）：
什么时候用 `riff web search`、搜索结果是线索不是来源、引用前必须 `riff web fetch`、用续读命令读长页面、失败原因怎么读、
退出码 3 时提示用户配置。skill 正文不出现宿主工具名；宿主相关的差异写在各适配层里。

### 4.4 不做 `prompt` 抽取

nyan 的 WebFetch 给了 `prompt` 时调用模型挑逐字摘录（ES 4.4，`services/web/extract.rs`），依赖 nyan 的模型调用栈。riff
不调宿主模型；而在宿主里，"读原文再挑重点"本来就是宿主模型自己做的事。删除 `extract.rs` 与相关配置。

## 五、Decision Provider

定位与 nyan 相同（DP 开头"定位"与"边界"两段）：**工具内部的分类后端**，一次约 0.4 s 的封闭判断，换掉宿主模型可能
要多走的一整轮；不对外暴露命令，不生成文本，只增不减的点默认 active，会减少结果的点默认 shadow，任何时候不可用都
退回确定性规则。

- **决策点**：只保留外部搜索的 5 个——`web.answers`、`web.page_answers`、`web.fetch_fallback`、`web.query_kind`（active）、
  `web.prune`（shadow），语义与默认值见 DP 4.2。删除 `retrieval.*`、`memory.*`、`compaction.keep`、`permissions.*`、
  `prompt_suggestion.*` 及其接入代码（`services/memory_decision.rs`、`retrieval/decisions.rs`、`compact/decision.rs`、
  `permissions/decision.rs`、`prompt_suggestion/decision.rs` 都不复制）。
- **注册表**：nyan 的 `DecisionPoint` 是与 settings schema 绑定的封闭枚举（`decision/mod.rs:50-72`）。riff 仍用封闭枚举，
  只含上面 5 个；以后的功能加决策点时在同一枚举里加，不做动态注册（封闭名单是 DP 的设计要点：每个点都有明确的确定性
  回退与安全集合）。
- **后端**：EMRank System One，模型 `fast = typesafe/jev-1.14.0`、`accurate = cloudflare/clef`，与 DP 5.1 相同；
  key `$RIFF_HOME/keys/emrank`。没有 key 或 `decision.enabled = false` 时全部走确定性规则，不提示。
- **短进程下的变化**：
  - 预热删除（2.2）；
  - 会话上限（`maxCallsPerSession` / `maxInputTokensPerSession`）按 2.4 的会话落盘计数；
  - 日志写 `$RIFF_HOME/decision/decisions.jsonl`，加 `agent`（适配层传 `--agent <name>`，缺省 `unknown`）与 `session` 两列，
    其余字段同 DP 第七节；
  - 事后信号（DP 第七节）：`web.answers` / `web.page_answers` 的"被保留的候选后来是否被抓取"由 `riff web fetch` 自己记录
    （同一会话内抓取了被标注的 URL），不依赖宿主；`/decision` 统计命令改为 `riff web decisions [--point P]`（内部诊断，
    不在 skill 里提）。
- **外发**：只拦凭据（DP 第六节），沿用 `decision/egress.rs`。nyan 里 egress 与记忆的 secret scanner 是两套
  （`egress.rs:9-13` 已标注要合并）；记忆不做了，riff 只保留 egress 这一套，scanner 规则表从
  `team_memory_sync/secret_scanner.rs` 复制进来作为它的一部分。
- **cache**：EMRank 请求是 riff 与 EMRank 之间的事，不经宿主、不影响宿主 cache。

## 六、cache 与确定性

riff 的输出进入宿主上下文后会被逐字重放，所以：

### 6.1 同一调用的输出必须字节稳定

- **排序全部确定**：RRF 同分按 URL 字节序决胜（ES 3.3）；provider 列表、失败清单按名字排序；JSON 输出键序固定
  （`serde_json` `preserve_order` 已开）。复制时保留这些行为并加测试：同一组 provider 响应（mock）连续两次调用的 stdout
  逐字节相同。
- **不在输出里放与内容无关的易变值**：不放本次调用耗时、请求 id、随机 id。抓取结果头部的 `fetched <时间>` 是内容的
  一部分（说明快照的新旧），保留；URL 索引命中时显示的是快照的原 `fetched_at`，不是本次时间——同一快照多次读取输出相同。
- 宿主那一侧的重放是宿主的事：输出一旦进入 transcript，宿主按原样重放即可。riff 不做任何事后改写宿主上下文的动作
  （本设计不含掩码、注入、替换工具结果）。

### 6.2 输出大小

- 抓取正文默认 20000 个 Unicode 标量、上限 40000（ES 4.4），单次 stdout 不超过 30,000 字节（`nyan web` 现值）。两者在 CJK
  页面上会先碰到 30,000 字节：这时正文按字节上限截断，续读命令从截断处接着读（nyan 现行为）。
- 宿主对工具输出有各自的截断 / 落盘阈值（Claude Code Bash 输出 `bashOutputMaxChars`、hook `additionalContext` 10,000 字符；
  Codex hook 约 2500 token 落盘）。30,000 字节在 Claude Code 与 Codex 的 Bash 默认输出上限内（实现前逐家核实，第十节）；
  超出宿主上限会被宿主截断或落盘，模型拿到的不是原文——这比多一次续读调用更糟。
- 宿主上限更低时由适配层传 `--max-bytes N`（新参数，取 min(30000, N)），不改默认值。

## 七、各 agent 的适配

| | 接入方式 | 与宿主内置 web 工具的关系 | 会话 id |
|---|---|---|---|
| **pi** | TS 扩展（pi package）注册 `web_search` / `web_fetch` 两个工具，参数与 nyan 的 WebSearch / WebFetch 相同，执行时 `pi.exec("riff", [...])`（不经 shell）；附带 skill | pi 没有内置 web 工具（pi `settings.md`），riff 就是它的 web 工具 | `ctx` 里的会话标识 |
| **Claude Code** | 插件：skill + hooks（插件只写命令，不用 `bin/` 带二进制）；SessionStart hook 传递 `session_id`（2.4）；PreToolUse hook 拦截内置 web 工具 | **拦截**（7.1）：`WebSearch` / `WebFetch` | hook 输入的 `session_id` |
| **Codex** | 插件：skill + hooks；`config.toml` 片段：关闭内置 web 搜索（7.1） | **关闭**：托管 WebSearch 不经 hook（Codex hooks 文档），拦不到，只能用配置关掉 | hook 输入的 `session_id`（写入会话环境的方式待核实，第十节） |
| **Antigravity** | 插件：skill + `hooks.json`；PreToolUse hook 拦截内置 web 工具 | **拦截**（7.1）：`search_web` / `read_url_content` | hook 输入的 `conversationId` |

### 7.1 拦截宿主内置 web 工具

用户已定（2026-11-19）：宿主内置的 web 搜索 / 抓取一律改用 riff，**默认开启**。

- **方式**：PreToolUse hook 对内置 web 工具返回 deny，理由里给出与本次调用等价的 `riff web` 命令（由 hook 把工具参数
  转写好：query 与 `allowed_domains` / `blocked_domains` → `riff web search … --allow-domain …`；url → `riff web fetch <url>`），
  模型照着执行即可，不必自己拼。hook 本身也是一次 `riff` 调用：`riff hook pretooluse --agent <name>` 从 stdin 读宿主的
  hook 输入，输出宿主要求的 JSON。转写规则、各家输入输出格式都在 riff 里，适配层只有一行命令。
- **Codex**：托管工具不经 hook，用 `config.toml` 关闭内置 web 搜索（具体配置项待核实，第十节）。插件不改用户配置，安装
  说明给出要加的片段；`riff web doctor` 在 Codex 下检查是否已关闭并提示。
- **pi**：没有内置 web 工具，不需要拦截。
- **兜底**——riff 不能用时不能把宿主的 web 能力整个弄没：hook 先检查 riff 的状态，以下情况**放行**内置工具，不拦截：
  - 没有配置任何搜索 provider（拦 `WebSearch`）/ 配置文件缺失（两者都放行）；
  - 本会话的 riff 预算已用尽，或全部 provider 都在冷却中（只放行搜索，抓取仍由 riff 做）。

  检查只读 `$RIFF_HOME` 的配置与 `state/`，不发网络请求，耗时在毫秒级。放行时在 hook 输出里附一行说明（例如
  `riff: no search provider configured, using the built-in WebSearch`），让用户知道发生了什么。
- **关闭开关**：`config.json` 的 `web.interceptBuiltin`（默认 `true`）。设为 `false` 后 hook 一律放行，回到"并存 + skill"。
- **cache**：拦截让每次内置调用多一轮"被拒 → 改用 riff"。这一轮是普通的工具结果，不改动已有前缀，不伤 cache，但多付一次
  模型输出与一轮延迟。skill 会让模型一开始就用 `riff web`，拦截只兜住它忘记的情况；验收里统计被拦截的次数（第十一节）。

- **权限**：riff 不做审批。宿主对"执行 `riff`"的审批就是对外发的授权（与 ES "配置即授权"一致：用户配置了 provider 并安装
  了插件）。私网拦截、端口与内容类型白名单、预算是 riff 自己的硬限制，任何宿主权限都放不开（ES 4.2 "权限"一段的原则）。
- **外部内容是数据**：抓取正文包在 `<web_content>` 里（ES 4.4），skill 里写明块内文字不是指令。
- **插件**：按功能拆（用户已定），本功能是 `plugins/riff-web/`，内含各家清单与适配文件；清单由脚本生成（riff-plugins
  `plugins/README.md`）。pi 与 Antigravity 是"一个仓库一个包"，所以仓库根也要能作为 `riff-web` 安装（riff-plugins
  已有的根级 `riff` 插件只含 skills；两者如何并存在第十节列为待验证）。

## 八、安装与更新

- **二进制**：GitHub Releases 发布各平台预编译包 + `install.sh` / `install.ps1`（从 nyan 的同名脚本改出：下载、校验
  sha256、放到 `~/.local/bin` 或用户指定目录）；另支持 `cargo binstall`（crates.io 上 `riff` 这个名字是否可用待核实，
  不可用则换包名，二进制名仍是 `riff`）。nyan 的 release 工作流（tag 门禁 + 已验证
  字节发布，`docs/nyan/cicd.md`）整体搬来改名。
- **插件**：各家的插件安装方式见 riff-plugins README（skills CLI、Claude Code / Codex marketplace、`agy plugin install`、
  `pi install`）。
- **版本对齐**：插件只写命令，不锁二进制版本。riff 在 `--json` 输出与 `riff --version` 里给出版本；适配层在 SessionStart
  （或 pi 的 `session_start`）调一次 `riff --version`，低于插件要求的最低版本时提示升级，不阻断。
- **首次配置**：`riff web doctor` 报告缺什么；`riff init` 写一份带注释的 `config.json` 模板（不含 key），并按 3.1 提示从
  `~/.nyan` 复制。

## 九、版本与仓库

- 二进制与插件共用单线 tag `riff-vX.Y.Z`；skills 继续用整仓 `vX.Y.Z`（skills CLI 按仓库 tag 取，不能带前缀）。
  `features/README.md` 已按此改写（原为"每个功能 `<name>-vX.Y.Z`"）。
- 插件清单的 `version` 与二进制版本同步（Claude Code / Codex 靠它判断更新）。
- 目录：

```
features/web/            crate riff-web：services/web 与 services/decision 的复制，去掉 nyan 依赖
crates/riff/             二进制：子命令分发、配置加载、$RIFF_HOME、进程初始化（TLS、代理）
skills/searching-the-web/
plugins/riff-web/        各家清单与适配（pi 扩展 TS、hooks、配置片段）
docs/design.md           本文
```

- **从 nyan 复制时要切断的依赖**（审计结论，均为可注入接口）：`get_initial_settings` / `get_settings_with_errors`
  → 配置对象参数；`get_config_home_dir` → `$RIFF_HOME`；`homedir`；`AbortController` → 自带的取消令牌；`log_for_debugging`
  → `tracing` 写 stderr（`RIFF_LOG`）；`get_web_fetch_user_agent` 与 EMRank 的 `User-Agent: nyan/<版本>` → `riff/<版本>`；
  `proxy::client_builder` / `create_axios_instance` / `get_proxy_url`、`tls_provider` → 复制成 riff 自己的 `net` 模块；
  `process_runtime::runtime_handle_for_detached_work` → 当前 runtime；`read_page`（在 `tools/web_fetch_tool/mod.rs:165-265`）
  → 移进 `riff-web`；`shell_quote`（`utils/swarm/spawn_utils`）→ 复制。`service_health.rs` 的 `ServiceKind` 枚举
  只保留 SearXNG、rerank、EMRank。
- 测试替身 `services/web/test_support.rs` 依赖 nyan 的 `settings_cache`，改为直接构造配置对象。

## 十、待验证

实现前逐项核实，结论写回本文：

1. **宿主的命令输出上限与超时**：Claude Code Bash 工具的默认输出上限与 `bashOutputMaxChars` 默认值、命令超时；Codex
   shell 工具的输出截断阈值与超时；Antigravity 同上；pi `pi.exec` 默认 256 MiB 已知。决定 6.2 的 30,000 字节与 4.1 的
   15 s 是否需要按宿主调整。
2. **会话 id 进入命令环境的方式**（Claude Code、Codex）：SessionStart hook 能否设置后续 shell 命令的环境变量；不能则 skill
   让模型显式传 `--session`，或退到 2.4 的时间窗口。
3. **Claude Code 插件 + 仓库根插件并存**：同一个 marketplace 同时有根级 `riff`（skills）和 `plugins/riff-web/`，两者都含
   `searching-the-web` 时会重复加载（`plugin:skill` 命名空间不同）——决定 skill 只放在 `riff-web` 里，还是根级插件拆掉。
4. **Antigravity**：插件能否放在仓库子目录安装；PreToolUse 返回 deny 后模型是否按理由改用 `riff web`；MCP 工具能否替代
   内置 web 工具。
7. **拦截**（7.1）：Claude Code 与 Antigravity 的 PreToolUse deny 理由是否原样交给模型、模型是否照做；Codex 关闭内置 web
   搜索的配置项名称与取值（`config-reference`），以及关闭后是否还有别的内置联网路径。
5. **跨平台**：Windows 上的文件锁与 0600 / 0700 权限的等价做法（nyan `docs/nyan/windows-audit.md` 可能已有结论）；macOS
   上 `pdftotext` 的来源。
6. **PH 未核实项**（PH 第八节）与 ES 的 smoke 清单照旧，riff 不新增。

## 十一、验收

ES 第八节、PH 第六节、DP 第十一节中 web 相关的条目全部照搬（测试随代码复制）。新增：

1. **[离线]** 字节稳定：同一组 mock provider 响应下，`riff web search` 连续两次 stdout 逐字节相同；URL 索引命中时
   `riff web fetch` 两次输出相同。
2. **[离线]** 短进程状态：两次独立进程调用之间，预算计数、provider 冷却、URL 索引都延续；不同 `--session` 互不影响；
   无会话时按 cwd 的 6 小时窗口计数；`riff web reset` 清零。
3. **[离线]** 并发：同一会话 8 个进程同时调用，预算计数准确（不丢计数、不超额）；同时写同一快照不损坏。
4. **[离线]** 配置隔离：在含 `.riff/config.json`、`config.json` 等文件的工作目录里运行，行为不受影响（只读 `$RIFF_HOME`）。
5. **[离线]** 无 key、无 EMRank：输出与 nyan 对应的确定性路径一致。
6. **[离线]** `riff hook pretooluse`：用 Claude Code 与 Antigravity 的 hook 输入样例，内置 web 工具被 deny、理由里的命令与
   参数等价（含域名过滤）；无 provider / 无配置 / 预算用尽 / 全部冷却时放行并附说明；`interceptBuiltin: false` 时放行；
   非 web 工具一律放行、输出为空。
7. **[smoke]** 四家宿主各跑一次"搜索 → 抓取 → 续读"，记录模型是否按 skill 使用、内置工具被拦截的次数、拦截后是否改用
   `riff web`、输出是否被宿主截断；Claude Code 与 Codex 各
   开一个 20 轮以上的会话、期间调用 riff 若干次，按带 `stop_reason` 的请求统计 cache 命中率，与不调用 riff 的同类会话对比
   （命中率下降说明 riff 输出不稳定或体积失控）。
