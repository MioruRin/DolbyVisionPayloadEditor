# DolbyVisionPayloadEditor

[English](README_EN.md) | 中文

通用 Windows 控制台工具，用于导出和修改显示器 EDID 中的 Dolby Vision VSDB，在硬件支持但厂商禁用了 PC 模式的显示器上启用 Dolby Vision PC 模式。

![Platform](https://img.shields.io/badge/platform-Windows-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 适用范围

本工具适用于**所有硬件支持 Dolby Vision 但 EDID 中禁用了 DV PC 模式的显示器**。

### 要求

- 显示器必须具备 **Dolby Vision 硬件支持**（面板 + 处理芯片）
- 显示器 EDID 中必须包含 **Dolby Vision VSDB**（Vendor Specific Data Block，IEEE OUI 为 `0x000D046`）
- DV Capability 字节的 **Bit 0 = 0**（DV over HDMI 被禁用）—— 这就是本工具要修改的位

### 已测试显示器

| 显示器 | 状态 |
|--------|------|
| XIAOMI XMI27B3 | 已测试，可用 |
| 其他禁用 PC 模式的 Dolby Vision 显示器 | 应该可用（通用 OUI 检测） |

> **注意**：本工具**不会**为没有 Dolby Vision 硬件的显示器添加该功能。它只会在已有 DV 硬件的显示器上启用 PC 模式标志。

---

## 厂商为何不开放 DV PC 模式

### Dolby Vision 授权是分层的

| 模式 | 授权对象 | 费用 |
|------|----------|------|
| Dolby Vision TV Mode | 电视 / 投影仪厂商 | 较低，基础授权 |
| Dolby Vision PC Mode | 显示器 / PC 厂商 | **额外费用，需单独购买授权** |

许多显示器厂商的策略：
- 硬件完全支持 Dolby Vision（面板、处理芯片都有）
- 连接 PS5、Xbox 等主机时正常工作（"TV 模式"信号）
- 但 **在 EDID 中将 Bit 0 设为 0**，声明"我不是 DV PC 显示器"
- 这样可以**省下 Dolby Vision PC 模式的授权费**
- Windows 读取 EDID 后认为不支持 DV → 设置中不会出现 Dolby Vision PC 选项

有些厂商同时宣传两种模式，因为他们同时购买了两种授权：
- "Dolby Vision"（TV 模式，连接游戏主机等时激活）
- "Dolby Vision PC"（PC 模式，Windows HDR 设置下会多出一个开关）

**那些只宣传 "Dolby Vision" 而没有 "Dolby Vision PC" 的显示器，大概率没有购买 PC 授权。**

---

## 工作原理

本工具只修改 EDID 中的 **2 个字节**：

| 字节 | 修改前 | 修改后 | 说明 |
|------|--------|--------|------|
| DV Capability | `0x9E` | `0x9F` | 翻转 Bit 0（DV over HDMI = 1） |
| Block Checksum | 对应值 | 重新计算 | Block 1 前 127 字节之和 |

工作流程：
1. **导出** Windows 注册表中的当前 EDID
2. **定位** Dolby Vision VSDB（通用 IEEE OUI 检测 `46 D0 00`）
3. **翻转** DV Capability 字节的 Bit 0，从 `0` 变为 `1`
4. **重新计算** EDID Block 的校验和
5. **保存** 修改后的 EDID 为 `.bin` 文件，供 CRU 导入

---

## 下载

从 [Releases](https://github.com/MioruRin/DolbyVisionPayloadEditor/releases) 页面下载 `DV_Switcher.exe`。

无需安装 Python，独立 Windows 可执行文件。

---

## 使用方法

### 步骤 1：导出当前 EDID

运行工具选择 **选项 1**，或使用命令行：

```powershell
.\DV_Switcher.exe --export
```

这会将当前 EDID 保存为 `.bin` 文件，放在工具所在文件夹。

### 步骤 2：打补丁

运行工具选择 **选项 2**，或使用命令行：

```powershell
.\DV_Switcher.exe --patch "XMI27B3_4K_20250606_123456.bin"
```

工具会：
- 使用 OUI `46 D0 00` 自动检测 Dolby Vision VSDB
- 显示当前 DV Capability 字节值
- 翻转 Bit 0 启用 DV PC 模式
- 保存为 `*_DV_ON.bin`

### 步骤 3：用 CRU 应用

1. 下载 [CRU (Custom Resolution Utility)](https://www.monitortests.com/custom-resolution-utility)
2. 打开 CRU，选择你的显示器
3. 点击 **Import**，选择 `*_DV_ON.bin` 文件
4. 运行 `Restart64.exe`（CRU 自带）重启显卡驱动
5. 进入 **Windows 设置 → 系统 → 显示 → HDR** —— "使用 Dolby Vision" 开关应该出现了

### 步骤 4：验证

运行工具选择 **选项 3**，或使用命令行：

```powershell
.\DV_Switcher.exe --read
```

这会从注册表读取当前显示器的 DV 信息。

---

## Dolby Vision EDID 结构

### DV 数据在 EDID 中的位置

EDID（Extended Display Identification Data）是显示器用来向系统报告自身能力的二进制数据。在 Windows 中，它存储在注册表中：

```
HKLM\SYSTEM\CurrentControlSet\Enum\DISPLAY\<型号>\<实例>\Device Parameters\EDID
```

Dolby Vision 数据位于 CTA-861 扩展块（Block 1 及之后）的 Data Block Collection 中，通过 IEEE OUI 识别：

- **Dolby IEEE OUI**：`0x000D046`
- **小端存储**：`46 D0 00`
- 找到 OUI 后，紧随其后的 **7 字节** 就是 Dolby Vision Payload

```
46 D0 00 | 4D 0A 9F 58 98 AA 5C
OUI(3B)  |   Payload(7B)
```

### DV Payload 结构（7 字节）

| 字节 | 偏移 | 示例 | 含义 |
|------|------|------|------|
| Byte 0 | +0 | `0x4D` | Dolby Vision 版本 |
| Byte 1 | +1 | `0x0A` | 最低向后兼容版本 |
| **Byte 2** | **+2** | **`0x9F`** | **DV Capability（本工具修改此字节）** |
| Byte 3 | +3 | `0x58` | 支持亮度信息 |
| Byte 4-6 | +4~+6 | `98 AA 5C` | 保留 / 厂商特定数据 |

### DV Capability 字节逐位解析

以 `0x9F = 10011111` 为例：

| 位 | 名称 | 含义 |
|----|------|------|
| **0** | **DV over HDMI** | **标准 HDMI Dolby Vision 信号（PC 模式关键位）** |
| 1 | DV over MHL | MHL 接口 Dolby Vision |
| 2 | Backlight Control | 背光控制（Local Dimming） |
| 3 | Profile 8 | Profile 8（BL+RPU，最常见的流媒体格式） |
| 4 | Profile 7 | Profile 7（FEL 完整增强层） |
| 5 | Profile 5 | Profile 5（RGB 12-bit 无损） |
| 6 | Low Latency DV | 低延迟 Dolby Vision（游戏模式） |
| 7 | DV Version Report | Dolby Vision 版本报告 |

---

## 从源码构建

```bash
pip install pyinstaller
pyinstaller --console --onedir --name DV_Switcher dv_switcher.py
```

---

## 仓库文件说明

| 文件 | 说明 |
|------|------|
| `DV_Switcher.exe` | 独立 Windows 可执行文件 |
| `dv_switcher.py` | Python 源代码 |
| `dv_editor.py` | 原版完整 GUI/CLI 工具（含注册表写入） |
| `DolbyVision_EDID_Guide.md` | 详细技术文档 |
| `README.md` | 本文件（中文） |
| `README_EN.md` | 英文版说明 |

---

## 警告

- 修改前务必备份原始 EDID（工具会自动导出）
- 使用 CRU 的 `Restart64.exe` 应用更改 —— **不要**使用 AW EDID Editor (AWE)，因为它会重写整个 CTA-861 块，可能破坏 VRR/刷新率数据
- 本工具修改 EDID 数据，风险自负

## 许可证

MIT License

## 参考

- [balu100/dolby-vision-for-windows (GitHub)](https://github.com/balu100/dolby-vision-for-windows)
- CTA-861-H 标准
