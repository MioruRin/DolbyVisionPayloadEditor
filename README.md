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

## How It Works

Many monitor manufacturers disable Dolby Vision PC mode (Bit 0 of the DV Capability byte) in EDID to save on licensing fees, even though the hardware fully supports it. This tool:

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

## Dolby Vision Capability Byte

| Bit | Name | Description |
|-----|------|-------------|
| **0** | **DV over HDMI** | **PC mode key bit** — this tool flips it from 0 to 1 |
| 1 | DV over MHL | Mobile High-Definition Link |
| 2 | Backlight Control | Local dimming support |
| 3 | Profile 8 | BL+RPU (Netflix, Disney+, etc.) |
| 4 | Profile 7 | BL+FEL dual layer (4K UHD Blu-ray) |
| 5 | Profile 5 | RGB 4:4:4 (Apple TV+) |
| 6 | Low Latency DV | Gaming mode |
| 7 | DV Version Report | Version reporting |

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
