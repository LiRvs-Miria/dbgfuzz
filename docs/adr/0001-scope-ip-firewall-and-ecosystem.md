# ADR-0001 — 范围、IP 防火墙与生态关系

日期：2026-09-30　　状态：已接受

## 背景

作者的主业是某工业编译器团队（闭源：自研 MLIR 方言、lowering 管线、调试系统，运行于无法承载 sanitizer runtime 的嵌入式/RT 目标）。本仓库是个人开源项目，与主业的**领域**相关（嵌入式目标的模糊测试/覆盖率/调试），但**不得**与主业的代码、方言、管线知识直接相关。

## 决策

1. **格式防火墙（架构级，永久约束）**：ptrfuzz 只消费公开标准格式——DWARF、LLVM IR/bitcode、libFuzzer 兼容的语料库与覆盖图、QEMU 作为目标运行时。公司栈仅作为这些格式的"生产方"存在于仓库边界之外。任何"了解某私有代码库/方言/板卡配置才有意义"的代码不得进入本仓库。
2. **生态关系：ptrfuzz : symrepl = Clang : LLVM**。[symrepl](https://github.com/LiRvs-Miria/symrepl) 提供调试侧基础设施（会话编排、断点管理、状态检查）；ptrfuzz 在其上构建模糊测试平台。symrepl 自 ptrfuzz M2 起为库依赖（经 git URL 安装，不上 PyPI）。两仓库只通过公开标准格式交换信息，互不持有对方私有细节。
3. **覆盖率后端可插拔**：ptrace 单步（M1，零重编译、慢、可行性基线）→ LLDB/硬件断点（M2，经 symrepl）→ 编译器侧轻量插桩（M3，SanitizerCoverage 式 inline-8bit 计数器写固定位图，无 ASan 类 runtime）。各后端的性能权衡在文档中如实标注。
4. **License：Apache-2.0 WITH LLVM-exception**，与 LLVM 生态及 symrepl 一致。

## 后果

- 仓库从第一行起即无 IP 风险；主业 IP 谈判与本仓库解耦。
- M1 不依赖 symrepl（裸 ptrace）；M2 起接入——保证 symrepl 依赖是真实契约而非口号。
- 双仓库维护成本存在；两个仓库的 roadmap 都把"标准格式防火墙"列为永久约束，漂移时以 ADR 为准。
