# 路线图（Roadmap）

[English](roadmap.md) | 简体中文

> 以英文版为准（authoritative）；两版在同一提交内同步更新。

每个里程碑刻意做小：约 2–3 个周末深度块。ptrfuzz 的开发在
[symrepl](https://github.com/LiRvs-Miria/symrepl) M2（DAP 基建）完成之后启
动——ptrfuzz 自 M2 起依赖 symrepl。

## M0 — 脚手架（已完成）

- 仓库、许可证（Apache-2.0 WITH LLVM-exception）、CI、范围/IP 防火墙与生
  态关系（见 [ADR-0001](adr/0001-scope-ip-firewall-and-ecosystem.md)）。

## M1 — ptrace 单步覆盖率基线

- 逐指令 `PTRACE_SINGLESTEP`；经 DWARF（`pyelftools`，第一个真实依赖）把
  PC 映射到源码行。
- 验收：在一个**未启用任何 sanitizer** 的小型 C 目标上，单步后端在 QEMU
  user 模式下恢复的行覆盖率与 `gcov` 基准一致，减速倍数实测并如实报告。
- 冻结覆盖图契约（粒度：edge / basic-block / line；尽量兼容 libFuzzer）。

## M2 — 经 symrepl 的 LLDB 后端

- 硬件断点 / 陷阱标志覆盖率，经 symrepl 会话基础设施编排；symrepl 正式成
  为库依赖。

## M3 — 编译器侧插桩

- LLVM SanitizerCoverage 式 inline-8bit 计数器写入固定位图地址——无 ASan
  类 runtime；位图在进程退出或经调试器读取。吞吐与 M1/M2 后端对比。

## M4 — 模糊测试循环

- 语料库管理（libFuzzer 兼容）、调度器、变异器接入；崩溃分诊经 symrepl 回
  放会话。

## M5 — aarch64 / RT 目标

- QEMU system 模式与真机运行（aarch64 嵌入式 Linux）；整理目标约束矩阵
  （没有 ptrace regset 怎么办、硬件断点不足怎么办等）。

## 待决问题

- **覆盖图契约（阻塞 M1）**：粒度与编码——尽量兼容 libFuzzer；任何 sidecar
  格式必须在本仓库公开定义（见 ADR-0001）。
- **硬件断点稀缺（阻塞 M2）**：典型 arm64 每线程仅 4–6 个调试寄存器；依赖
  它之前先设计断点回收策略。
