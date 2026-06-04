# Dolby Vision EDID 修改指南

> 本文记录 Dolby Vision（杜比视界）在显示器 EDID 中的数据结构、各字段含义，以及如何通过修改 EDID 强制开启 Windows 下的 Dolby Vision PC 模式。

---

## 1. EDID 中的 Dolby Vision 数据在哪

### EDID 基本结构

EDID（Extended Display Identification Data）是显示器向系统报告自身能力的二进制数据，Windows 存储在注册表中：

```
HKLM\SYSTEM\CurrentControlSet\Enum\DISPLAY\<型号>\<实例ID>\Device Parameters\EDID
```

- 数据类型：`REG_BINARY`
- 常见大小：128 / 256 / 384 字节
- 每 128 字节为一个 Block，最后一个字节为该 Block 的校验和
- 校验和规则：Block 内前 127 字节之和 mod 256 = 0（校验和使总和凑 256 的整数倍）

### CTA-861 扩展块

Dolby Vision 数据位于 CTA-861 扩展块中（Block 1 及之后）：

| 偏移（相对于 Block 起始） | 含义 |
|---|---|
| +0 | Tag = `0x02`（CTA-861 Extension） |
| +1 | Revision（通常 0x03） |
| +2 | DTD Start Offset（Detailed Timing Descriptor 起始偏移） |
| +3 | Byte count of native data block |
| +4 ~ +DTD Offset | Data Block Collection（所有厂商数据块在这） |

### Dolby Vision VSDB

在 Data Block Collection 中，通过 IEEE OUI（Organizationally Unique Identifier）识别 Dolby Vision 的 Vendor Specific Data Block：

- **Dolby IEEE OUI**: `0x000D046`
- **小端存储**: `46 D0 00`
- 找到 OUI 后，紧跟其后的 **7 字节**就是 Dolby Vision Payload

```
  46 D0 00 | 4D 0A 9F 58 98 AA 5C
  OUI(3B)  |   Payload(7B)
```

---

## 2. Dolby Vision Payload 结构（7 字节）

以 Payload `4D 0A 9F 58 98 AA 5C` 为例：

| 字节 | 偏移 | 值 | 含义 |
|---|---|---|---|
| Byte 0 | +0 | `0x4D` | Dolby Vision 版本（0x4D = Dolby Vision Version 4） |
| Byte 1 | +1 | `0x0A` | 向后兼容的最低版本/Profile 标志 |
| **Byte 2** | **+2** | **`0x9F`** | **Dolby Vision Capability（核心字段，8 个 bit）** |
| Byte 3 | +3 | `0x58` | 支持的亮度信息（forward compatible） |
| Byte 4-6 | +4~+6 | `58 98 AA 5C` | 保留/厂商自定义数据 |

**Byte 2（Dolby Vision Capability）是最关键字段，Windows 通过它判断显示器的 DV 能力。**

---

## 3. Dolby Vision Capability 逐位解释

以 `0x9F = 10011111` 为例：

| Bit | 名称 | 含义 | 说明 |
|---|---|---|---|
| **Bit 0** | **DV over HDMI** | **标准 HDMI 杜比视界信令** | **Windows 杜比视界 PC 模式的关键位。置 1 → 系统认为显示器支持 DV 输入 → 设置→显示→HDR 出现杜比视界开关。置 0 → 厂商省 PC 授权费的手段。** |
| Bit 1 | DV over MHL | MHL 接口杜比视界 | 通过 MHL（Mobile High-Definition Link）传输 DV，面向移动设备接口，PC HDMI 连接无影响 |
| Bit 2 | Backlight Control | 背光控制（Local Dimming） | 声明显示器支持通过 DV 元数据控制分区背光，系统可配合面板做更精准的亮度调节 |
| Bit 3 | Profile 8 | Profile 8（BL+EL） | **最主流的 Profile。** 基础层用 HDR10/HLG 信号，增强层单独传输 DV 元数据。Netflix、Disney+、Apple TV+ 等流媒体主要用此 Profile |
| Bit 4 | Profile 7 | Profile 7（FEL） | Full Enhancement Layer，传输完整的增强层+基础层两路数据，画质最好但带宽需求最高。4K UHD Blu-ray 使用此 Profile |
| Bit 5 | Profile 5 | Profile 5（RGB 12-bit 无损） | RGB 12-bit 无压缩模式。只有原生 12-bit 面板的专业监视器（如 Sony BVM）才真正支持，HDMI 2.1 带宽在 4K60 下足够但面板硬件限制，几乎没有消费级内容源 |
| Bit 6 | Low Latency Dolby Vision | 低延迟杜比视界（LLDV） | 面向游戏场景，开启后牺牲元数据精度（12-bit → 10-bit）换取更低视频处理延迟。画质优先的显示器不建议开启 |
| Bit 7 | DV Version Report | Dolby Vision 版本报表 | 声明支持通过 VSDB 报告 DV 版本号，驱动/系统据此读取后续版本字段 |

---

## 4. Dolby Vision Profiles 对比

| Profile | 信号方式 | 色深 | 带宽需求 | 内容来源 | 受众 |
|---|---|---|---|---|---|
| **Profile 5** | RGB 无压缩 | 12-bit 原生 | ~20.2 Gbps @4K60 | 几乎无（仅数字影院母版/归档） | 专业后期 |
| **Profile 7** | BL + FEL 双层 | 10-bit | 较高 | 4K UHD Blu-ray | 家庭影院 |
| **Profile 8** | BL + EL（兼容 HDR10） | 10-bit | 适中 | Netflix/Disney+/Apple TV+ | 主流消费者 |

> **日常使用只需关注 Profile 7 和 Profile 8。** Profile 5 是"专业工具人的 Profile"，没有任何流媒体或光盘内容使用。

---

## 5. 为什么有些显示器硬件支持 Dolby Vision 但 Windows 不显示 PC 模式

### Dolby 授权机制

Dolby Vision 的授权是**分级收费**的：

| 模式 | 授权对象 | 费用 |
|---|---|---|
| Dolby Vision TV 模式 | 电视/投影仪厂商 | 较低，基础授权 |
| Dolby Vision PC 模式 | 显示器/PC 厂商 | **额外付费，需单独授权** |

很多显示器厂商的策略：
- 硬件完全支持 Dolby Vision（面板、处理芯片都具备）
- 接 PS5、Xbox 等"电视模式"信号时正常工作
- 但在 **EDID 中将 Bit 0 设为 0**，声明"我不是 DV PC 显示器"
- 这样可以**省掉 Dolby Vision PC 授权费**
- Windows 读取 EDID 后认为不支持 → 不显示 Dolby Vision PC 选项

### 其他厂商的标注

部分厂商会同时宣传两个模式，因为两个都授权了：
- "杜比视界"（TV 模式，连接游戏机等设备时生效）
- "杜比视界 PC"（PC 模式，Windows HDR 下额外出现开关）

**只宣传"杜比视界"而没有"杜比视界 PC"的，大概率就是没买 PC 授权。**

---

## 6. 如何开启 Dolby Vision PC 模式

### 方法概述

只需修改 EDID 中 Dolby Vision Capability 的 **Bit 0**（从 0 改为 1），并重算对应 Block 的校验和。

### 实际修改（2 字节）

| 字节 | 修改前 | 修改后 | 说明 |
|---|---|---|---|
| DV Capability | `0x9E` | `0x9F` | 翻转 Bit 0（DV over HDMI = 1） |
| Block 校验和 | 对应值 | `0x100 - (sum mod 256)` | 重算 Block 1 前 127 字节 |

### 修改方式

1. **CRU（Custom Resolution Utility）**— 推荐，导入修改好的 .bin 文件，运行 Restart64.exe 重启显卡驱动
2. **注册表直接写入** — 用管理员权限写入 EDID 键值，然后重新插拔显示线缆或重启
3. **DV Payload Editor 工具** — 见下方

---

## 7. DV Payload Editor 工具

一个通用的 Dolby Vision EDID 修改工具，支持所有显示器。

### 功能

- 自动扫描所有显示器 EDID，定位 Dolby Vision VSDB
- 8 个 bit 可视化编辑（勾选框）
- 一键开启 DV PC 模式（Bit 0）和低延迟模式（Bit 6）
- 自动备份原始 EDID + 校验和重算
- UAC 自动提权
- 导出 .bin 文件供 CRU 导入
- 命令行模式

### 使用方式

```
DolbyVisionPayloadEditor.exe                  # 启动 GUI
DolbyVisionPayloadEditor.exe --list          # 列出所有显示器
DolbyVisionPayloadEditor.exe --read          # 读取 Dolby Vision Payload
DolbyVisionPayloadEditor.exe --patch         # 自动打补丁（翻转 Bit 0）
DolbyVisionPayloadEditor.exe --export        # 导出修改后的 .bin（供 CRU）
```

### GitHub

https://github.com/MioruRin/DolbyVisionPayloadEditor

---

## 8. 注意事项

- 修改 EDID 后需要重新插拔显示线缆或重启显卡驱动（CRU 附带的 Restart64.exe）才能生效
- 修改前务必备份原始 EDID（工具会自动备份到 `%TEMP%`）
- 使用 AW EDID Editor（AWE）等工具修改 EDID 时需注意：它会重新序列化整个 CTA-861 扩展块，可能破坏 VRR、刷新率等数据，建议只做单字节精确修改
- Windows 11 的杜比视界开关位置：**设置 → 系统 → 显示 → HDR → 使用杜比视界**
- Windows 没有独立的低延迟 Dolby Vision 开关，只有杜比视界总开关

---

## 参考

- [balu100/dolby-vision-for-windows (GitHub)](https://github.com/balu100/dolby-vision-for-windows)
- CTA-861-H Standard
- Dolby Vision Licensing
