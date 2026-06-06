# DolbyVisionPayloadEditor

A universal Windows console tool to export and modify the Dolby Vision VSDB in any monitor's EDID, enabling Dolby Vision PC mode on displays that support it hardware-wise but have it disabled by the manufacturer.

![Platform](https://img.shields.io/badge/platform-Windows-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Applicable Scope

This tool works with **any monitor that has Dolby Vision hardware support but disables DV PC mode in EDID**.

### Requirements

- Monitor must have **Dolby Vision hardware support** (panel + processing chip)
- Monitor's EDID must contain a **Dolby Vision VSDB** (Vendor Specific Data Block with IEEE OUI `0x000D046`)
- The DV Capability byte must have **Bit 0 = 0** (DV over HDMI disabled) — this is what the tool patches

### Tested Monitors

| Monitor | Status |
|---------|--------|
| XIAOMI XMI27B3 | Tested & Working |
| Other Dolby Vision monitors with disabled PC mode | Should work (generic OUI detection) |

> **Note**: This tool does NOT add Dolby Vision to monitors that lack hardware support. It only enables the PC mode flag in EDID for monitors that already have DV hardware.

---

## Why Manufacturers Disable DV PC Mode

### Dolby Vision Licensing is Tiered

| Mode | Licensing Target | Fee |
|------|------------------|-----|
| Dolby Vision TV Mode | TV / projector manufacturers | Lower, base license |
| Dolby Vision PC Mode | Monitor / PC manufacturers | **Additional fee, separate license required** |

Many monitor manufacturers' strategy:
- Hardware fully supports Dolby Vision (panel, processing chip both present)
- Works normally when connected to PS5, Xbox, etc. ("TV mode" signal)
- But **sets Bit 0 to 0 in EDID**, declaring "I am not a DV PC monitor"
- This **saves on the Dolby Vision PC licensing fee**
- After Windows reads EDID and thinks DV is not supported, the Dolby Vision PC option does not appear in Settings

Some manufacturers advertise both modes because they licensed both:
- "Dolby Vision" (TV mode, activated when connected to game consoles, etc.)
- "Dolby Vision PC" (PC mode, an extra toggle appears under Windows HDR)

**Those that only advertise "Dolby Vision" without "Dolby Vision PC" most likely did not purchase the PC license.**

---

## How It Works

This tool modifies only **2 bytes** in your EDID:

| Byte | Before | After | Notes |
|------|--------|-------|-------|
| DV Capability | `0x9E` | `0x9F` | Flip Bit 0 (DV over HDMI = 1) |
| Block Checksum | Corresponding value | Recalculated | Sum of first 127 bytes of Block 1 |

Workflow:
1. **Exports** your current EDID from the Windows registry
2. **Locates** the Dolby Vision VSDB using generic IEEE OUI detection (`46 D0 00`)
3. **Flips Bit 0** of the DV Capability byte from `0` to `1`
4. **Recalculates** the EDID block checksum
5. **Saves** the modified EDID as a `.bin` file for import into CRU

---

## Download

Download `DV_Switcher.exe` from the [Releases](https://github.com/MioruRin/DolbyVisionPayloadEditor/releases) page.

No Python installation required. Standalone Windows executable.

---

## Usage

### Step 1: Export Current EDID

Run the tool and select **Option 1**, or use command line:

```powershell
.\DV_Switcher.exe --export
```

This saves your current EDID as a `.bin` file in the same folder as the tool.

### Step 2: Patch the EDID

Run the tool and select **Option 2**, or use command line:

```powershell
.\DV_Switcher.exe --patch "XMI27B3_4K_20250606_123456.bin"
```

The tool will:
- Auto-detect the Dolby Vision VSDB using OUI `46 D0 00`
- Show current DV Capability byte value
- Flip Bit 0 to enable DV PC mode
- Save as `*_DV_ON.bin`

### Step 3: Apply with CRU

1. Download [CRU (Custom Resolution Utility)](https://www.monitortests.com/custom-resolution-utility)
2. Open CRU, select your monitor
3. Click **Import**, select the `*_DV_ON.bin` file
4. Run `Restart64.exe` (bundled with CRU) to restart the GPU driver
5. Go to **Windows Settings → System → Display → HDR** — the "Use Dolby Vision" toggle should now appear

### Step 4: Verify

Run the tool and select **Option 3**, or use command line:

```powershell
.\DV_Switcher.exe --read
```

This reads your current monitor's DV info from the registry.

---

## Dolby Vision EDID Structure

### Where is DV Data in EDID?

EDID (Extended Display Identification Data) is binary data that a monitor uses to report its capabilities. On Windows, it is stored in the registry:

```
HKLM\SYSTEM\CurrentControlSet\Enum\DISPLAY\<model>\<instance>\Device Parameters\EDID
```

Dolby Vision data is located in the CTA-861 Extension Block (Block 1 and beyond), within the Data Block Collection. It is identified by its IEEE OUI:

- **Dolby IEEE OUI**: `0x000D046`
- **Little-endian storage**: `46 D0 00`
- After finding the OUI, the following **7 bytes** are the Dolby Vision Payload

```
46 D0 00 | 4D 0A 9F 58 98 AA 5C
OUI(3B)  |   Payload(7B)
```

### DV Payload Structure (7 Bytes)

| Byte | Offset | Example | Meaning |
|------|--------|---------|---------|
| Byte 0 | +0 | `0x4D` | Dolby Vision version |
| Byte 1 | +1 | `0x0A` | Minimum backward-compatible version |
| **Byte 2** | **+2** | **`0x9F`** | **DV Capability (this tool modifies this byte)** |
| Byte 3 | +3 | `0x58` | Supported brightness info |
| Byte 4-6 | +4~+6 | `98 AA 5C` | Reserved / vendor-specific |

### DV Capability Byte Breakdown

Using `0x9F = 10011111` as an example:

| Bit | Name | Meaning |
|-----|------|---------|
| **0** | **DV over HDMI** | **Standard HDMI Dolby Vision signaling (PC mode key)** |
| 1 | DV over MHL | MHL interface Dolby Vision |
| 2 | Backlight Control | Backlight control (Local Dimming) |
| 3 | Profile 8 | Profile 8 (BL+RPU, most common streaming) |
| 4 | Profile 7 | Profile 7 (FEL full enhancement layer) |
| 5 | Profile 5 | Profile 5 (RGB 12-bit lossless) |
| 6 | Low Latency DV | Low-latency Dolby Vision (gaming) |
| 7 | DV Version Report | Dolby Vision version reporting |

---

## Build from Source

```bash
pip install pyinstaller
pyinstaller --console --onedir --name DV_Switcher dv_switcher.py
```

---

## Files in This Repo

| File | Description |
|------|-------------|
| `DV_Switcher.exe` | Standalone Windows executable |
| `dv_switcher.py` | Python source code |
| `dv_editor.py` | Original full-featured GUI/CLI tool (with registry write) |
| `DolbyVision_EDID_Guide.md` | Detailed technical documentation |
| `README.md` | This file |

---

## Warning

- Always backup your original EDID before modifying (the tool exports it automatically)
- Use CRU's `Restart64.exe` to apply changes — do NOT use AW EDID Editor (AWE) as it rewrites the entire CTA-861 block and may break VRR/refresh rate data
- This tool modifies EDID data at your own risk

## License

MIT License

## References

- [balu100/dolby-vision-for-windows (GitHub)](https://github.com/balu100/dolby-vision-for-windows)
- CTA-861-H Standard
