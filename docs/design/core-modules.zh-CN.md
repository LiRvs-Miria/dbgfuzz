# ptrfuzz 设计：核心骨架——Driver/Engine、四方言、里程碑

> 状态：草案 v2，Driver/Engine 切分按作者裁定（2026-11-18）。范围：模块切分、四个产物
> 方言、pass 家族、构建顺序。部署视图见 [architecture.zh-CN.md](architecture.zh-CN.md)
> （English: [architecture.md](architecture.md)）。English: [core-modules.md](core-modules.md)。

## 已裁定

1. **产物 IR 用真 MLIR（方案 a）**。mlir-opt-fuzzer 作者裁定：基础设施成本
   （PassManager、verifier、textual round-trip、TableGen）已预付学费。溯源 = pass pipeline
   串（`种子 S + 管线 P` 可复现产物）。
2. **四个方言，不是一个**：`ptrf.seed`（种子）、`ptrf.mut`（变异产物）、`ptrf.dbg`
   （调试侧结果：停因、PC、寄存器 dump、覆盖命中）、`ptrf.report`（报告）。方言词汇表是
   共同语言，pass 是大脑。
3. **顶层分两部分**：
   - **引擎（Engine）**——纯 MLIR 世界：四方言 + 全部 pass 家族。无 socket、无进程。
     覆盖率分析、变异转换、变异分析（由 `ptrf.dbg` 驱动的策略选择）、结果分析、报告转换、
     语料库。
   - **驱动（Driver）**——活物世界，三职责：fuzzing 数据送入（输入通道）、被 fuzzing
     测试程序结果返回（stdout/响应收集）、调试交互（lldb-server：断点、停、寄存器/内存
     读），外加目标生命周期与 crash 捕获机制。

## 边界法则（约束性）

1. **Driver 循环是命令式的；pass 活在 Engine 阶段内部。** 循环——取产物字节→注入→等调试
   事件→收集结果→交 Engine→执行 Engine 的下一条管线→重复——是编排，不是变换管线。
2. **每次命中不上 IR。** 单个 BP 命中保持地址键裸位图运算。调试命中**按运行轮次批量**打成
   `ptrf.dbg` IR 交给 Engine——IR 在轮次粒度，绝不在事件粒度。
3. **每个方言自带 parser/emitter 对。** 目标吃字节：每个方言向线格式 lower、从线字节
   ingest。RawBytes 是默认方言（字节级目标零 IR 税）；协议方言（OPC UA、Modbus……）随
   结构化目标到来。
4. **纯度是结构性质。** Engine 只链 MLIR——无 socket、无进程。Driver 只链 liblldb/OS——
   **无 MLIR**（默认，可否决）：Engine 交给 Driver lower 好的字节与管线规格；Driver 交给
   Engine 原始事实（经 Engine 的 parse API 打成 `ptrf.dbg` IR）加目标结果。review/CI 查
   include 图：Driver 出现 MLIR 头文件或 Engine 出现 socket 头文件即否决。
5. **单 ABI 法则**：进程内一套 LLVM 构建——liblldb 与 MLIR 同出 LLVM 22 树（M0 spike 已
   验证：MLIR context + SBDebugger 同进程跑通，exit 0）。

## 模块

```
 ┌────────────────────── CLI / config（薄） ──────────────────────┐
 │                                                                │
 └──► Driver（循环；唯一活物世界）           Engine（纯 MLIR）
 ┌───────────────────────────┐            ┌───────────────────────────┐
 │ fuzz-loop（命令式）         │ seed IR    │ 方言: seed / mut /          │
 │  ├ 输入: 注入字节           │ + dbg IR ─►│        dbg / report        │
 │  ├ 调试: BP/停/寄存器       │◄─ 字节 + ──│ passes:                    │
 │  ├ 目标结果返回             │   管线规格  │  · 变异转换                 │
 │  ├ 生命周期/重启            │            │  · 变异分析（策略←ptrf.dbg）│
 │  └ crash 捕获机制           │            │  · 覆盖率分析               │
 └───────────────────────────┘            │  · 结果分析                 │
 ┌──────────────┐                          │  · 报告转换                 │
 │ symbolization │── 址位, build-id ─────► │ 语料库                      │
 └──────────────┘                          └───────────────────────────┘
```

| 模块 | 独占（owns） | 绝不碰（must-not） | 依赖 |
|---|---|---|---|
| **Driver** | 循环；输入注入；目标结果返回；调试交互（SB API 封装：断点、停、寄存器/内存读、停因分类）；目标生命周期与重启；crash 捕获机制 | 任何 MLIR（默认，可否决）；任何策略/分析逻辑 | liblldb、OS |
| **Engine** | 四方言；全部 pass 家族（变异转换；变异分析 = 从 `ptrf.dbg` 选策略；覆盖率分析 = 图/新颖性；结果分析；报告转换）；语料库；硬件槽位账本 | socket、进程、活连接 | MLIR |
| **symbolization** | ELF/DWARF 资产策略：同构建不变量（build-id）、址位枚举、地址链降级档 | 碰连接（直接解析 ELF 副本） | LLVM DWARF 库 |
| **reporting / config / CLI** | 报告序列化、战役统计、配置解析、入口 | 持有连接 | 快照（拉模型） |

Engine 内的 pass 家族（按裁定原意逐条）：

- **变异转换**——`ptrf.seed`/`ptrf.mut` 上的 bitflip/arith/splice/havoc
- **变异分析**——下一轮用什么策略，从 `ptrf.dbg` 算出（反馈大脑，作为带缓存/失效语义的
  MLIR analysis）
- **覆盖率分析**——`ptrf.dbg` → 图/位图标注、新颖性信号
- **结果分析**——`ptrf.dbg` + 目标结果 → 发现/crash 分类
- **报告转换**——`ptrf.report` 去重/聚合/输出形态

## 不变量

1. **两条连接永不通话。** 输入与调试连接是 Driver 内的机制；任何数据不得在它们之间路由
   （architecture.md 的永久拒绝项）。
2. **Engine 无 socket；Driver 无 MLIR**（法则 4）——纯度边界是 include 图性质，可 CI 检查。
3. **模块接口是数据形状**：IR（序列化或内存内）、lower 后的字节、管线规格、plain struct——
   方言与引擎可离线测试。
4. **回归网与架构同构**：纯核网 = 直接喂 `ptrf.dbg` IR 给 Engine，不起服务；探针网 =
   Driver 打真 lldb-server（E2E 环境）；手动客户端保持人工验收。

## 工具链（Debian 13，全部 22.1.8）

`llvm-22-dev`、`libmlir-22-dev`、`mlir-22-tools`（dev cmake target 引用其二进制）、
`liblldb-22-dev`。CMake：`find_package(LLVM REQUIRED CONFIG)` + MLIR CONFIG，配
`CMAKE_PREFIX_PATH=/usr/lib/llvm-22`；LLVM 版本检查是 major.minor 精确匹配（22.1.8 ≠ "22"）；
**LLDB 不带 cmake 包**——直接链 `liblldb-22.so`，头文件在 `/usr/lib/llvm-22/include`。

## 里程碑

- **M0** — 骨架编译（根 CMake：LLVM+MLIR+LLDB 三链接，spike 已绿）；Driver 的调试交互
  半边用 SB API 复刻已验证的 E2E 流程。Oracle 已就位：CLI 对照组 + `dap_client.py`。
- **M1** — 四方言最小形态 + RawBytes；第一个变异 transform + 覆盖率分析 pass；Driver 循环
  闭环打 stdin shim 解析器目标。
- **M2** — SIGSEGV 目标；crash 捕获（Driver）→ `ptrf.report` IR（Engine）带溯源串。
- **M3** — 语料库 + 完整变异转换集 + 变异分析（策略选择）；第一个协议 dialect 决策。
- **M4** — symbolization build-id 强制；硬件断点/单步档走址位账本；报告导出。
