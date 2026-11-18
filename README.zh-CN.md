# dbgfuzz

面向跑不了 sanitizer runtime 的目标的覆盖率引导模糊测试：闭源二进制、嵌入式固件、RTOS 任务、真实设备。

**模糊输入。盯着 crash。留住 crash 现场——调用栈、寄存器、内存，调试器停下时的原样。**

## 背景

经典 fuzzing 工具各自都有失效的地方：

- **libFuzzer / AFL++** 需要源码或可重编译的插桩。快，但对你编译不了的东西一概失明。
- **QEMU 模式 fuzzing** 能打裸二进制，但扭曲设备行为：外设、时序、硬件状态全部缺失。嵌入式 ARM 上也没有便宜的硬件 trace 替代品。
- **协议 fuzzer**（boofuzz 之类）能注入结构化输入，但盲打——没有覆盖反馈。

而调试器就摆在那里。凡是它能 attach 的进程——包括所有 fuzzer 无法插桩的目标——它都能单步、下硬件断点、读寄存器、dump 内存。

dbgfuzz 就是把这台调试器变成 fuzzer 的眼睛和手：给黑盒目标覆盖反馈，crash 一发生现场就在手边。

完整故事见 [docs/background.zh-CN.md](docs/background.zh-CN.md)（English: [docs/background.md](docs/background.md)）。

## 你能得到什么

1. **黑盒目标的定向输入。** 调试器侧覆盖（单步、硬件断点、LLDB 会话）告诉变异引擎哪些路径真的跑到过。不需要源码、不需要重编译、不需要 sanitizer。
2. **crash = 活现场。** crash 触发的瞬间，目标已经停在调试器里。调用栈、寄存器、内存就地可查，逐步重放内建。没有丢失的状态，没有"拿输入文件从头重现"的仪式。

## 使用场景

| 场景 | 谁用 | 为什么是 dbgfuzz |
|---|---|---|
| 真机上的闭源固件（IoT / 车规 / 医疗） | 设备安全团队、研究员 | 真机行为 QEMU 模拟不了；ARM 缺便宜 trace 硬件 |
| 硬件在环测试（RTOS 目标） | 厂商 SDL 团队 | EU CRA 2027 年 12 月起适用：厂商必须测试出厂二进制，而他们没有 sanitizer 构建 |
| 深度定向测试（patch 验证、假设驱动） | 安全响应 | 覆盖钉在指定区域；crash 现场与重放内建 |
| ICS 运行时/协议（FORTE、OpenPLC、OPC UA 栈） | OT 安全研究 | 真实运行时语义 + 覆盖引导（boofuzz 盲打） |
| 免重编译的覆盖反馈 | 没有覆盖构建管线的团队 | 调试器侧覆盖图，不重编译 |

dbgfuzz 不和 libFuzzer/AFL++ 竞争：有源码、要吞吐，就用它们。dbgfuzz 服务的是交集——**真机 + 闭源 + 要覆盖引导 + 要便宜 triage**。

## 状态

已 scaffold；设计中。文档：本文件（中文镜像）+ [`README.md`](README.md)（英文权威版）+ [背景](docs/background.zh-CN.md)（[English](docs/background.md)）。
