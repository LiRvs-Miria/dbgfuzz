# ptrfuzz

[English](README.md) | 简体中文

为跑不了 sanitizer runtime 的目标做覆盖率引导模糊测试。

ptrfuzz 在**调试器侧**收集覆盖率——经 ptrace、硬件断点或 LLDB 会话——并与
**编译器侧插桩**配对：后者只多产出一张覆盖图，不引入任何完整 runtime。结
果是：在嵌入式 Linux、RT 内核和遗留目标上获得真正的覆盖率引导反馈，而这些
目标上 ASan/TSan 类 runtime 通常不可用。

## 为什么做这个

今天的覆盖率引导模糊测试默认目标能承载 sanitizer runtime。嵌入式和 RT 目
标经常不能：没有 ASan、内存预算紧张、内核功能缺失（ptrace regset、硬件断
点）、跑在真机上。在这类目标上，模糊测试退化为盲变异或缓慢的全系统仿真。

ptrfuzz 用可插拔的覆盖率后端填补这个空隙：

- **调试器侧**：ptrace 单步 / 硬件断点 / LLDB 会话收集覆盖率——零重编译，
  慢但普适；
- **编译器侧**：LLVM 插桩只产出覆盖位图，不引入完整 sanitizer runtime——
  快，但需要重编译。

## 生态

ptrfuzz 之于 [symrepl](https://github.com/LiRvs-Miria/symrepl)，如同 Clang
之于 LLVM：symrepl 提供调试侧基础设施（会话编排、断点管理、状态检查），
ptrfuzz 在其上构建模糊测试平台。从 ptrfuzz M2 起，symrepl 成为库依赖。

## 范围与架构铁律

ptrfuzz 只消费**公开标准格式**——与 symrepl 同一条防火墙（见
[docs/adr/0001-scope-ip-firewall-and-ecosystem.md](docs/adr/0001-scope-ip-firewall-and-ecosystem.md)）：

- DWARF 调试信息、LLVM IR / bitcode
- libFuzzer 兼容的语料库与覆盖图
- QEMU（user / system 模式）作为目标运行时

任何只有了解特定私有代码库或方言才有意义的内容都不属于这里。

## 状态

Pre-MVP：仅脚手架。路线图见 [docs/roadmap.md](docs/roadmap.md)——下一步是
M1（ptrace 单步覆盖率基线）。

## 计划中的依赖

- 支持 ptrace 的 Linux（x86-64 / aarch64）；跨目标运行用 QEMU
- 带 SanitizerCoverage 类插桩的 LLVM（M3+）
- Python >= 3.10；symrepl（M2 起）

## 许可证

Apache-2.0 WITH LLVM-exception——与 LLVM 项目相同的许可证，与 ptrfuzz 所处
的生态一致。
