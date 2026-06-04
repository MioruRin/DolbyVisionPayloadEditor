# DolbyVisionPayloadEditor

A universal Windows tool to modify the Dolby Vision VSDB in any monitor's EDID, enabling Dolby Vision PC mode on displays that support it hardware-wise but have it disabled by the manufacturer.

![Platform](https://img.shields.io/badge/platform-Windows-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/Python-3.13-yellow)

---

## Table of Contents

- [Features](#features)
- [Download](#download)
- [Usage](#usage)
- [Dolby Vision EDID Technical Details](#dolby-vision-edid-technical-details)
- [Build from Source](#build-from-source)
- [How It Works](#how-it-works)
- [Warning](#warning)
- [License](#license)
- [References](#references)

---

## Features

- Auto-scan all monitors for Dolby Vision VSDB (IEEE OUI `0x000D046`)
- Visual 8-bit checkbox editor for Dolby Vision Capability byte
- One-click enable DV PC Mode (Bit 0) and Low Latency Mode (Bit 6)
- Automatic EDID backup + checksum recalculation
- UAC auto-elevation for registry writes
- Export `.bin` for CRU (Custom Resolution Utility) import
- CLI mode for scripting

## Download

Download the latest release (`DolbyVisionPayloadEditor.exe`) from the [Releases](https://github.com/MioruRin/DolbyVisionPayloadEditor/releases) page.

## Usage

### GUI Mode

```bat
DolbyVisionPayloadEditor.exe
```

1. Select your monitor from the list
2. Toggle DV capability bits as needed
3. Click **Apply (Memory)** then **Write Registry** (requires admin)
4. Re-plug your display cable or restart the GPU driver (`Restart64.exe`)

### CLI Mode

```bash
# List all monitors
DolbyVisionPayloadEditor.exe --list

# Read Dolby Vision payload
DolbyVisionPayloadEditor.exe --read

# Auto-patch (enable DV PC mode, flip Bit 0)
DolbyVisionPayloadEditor.exe --patch

# Export patched EDID as .bin (for CRU import)
DolbyVisionPayloadEditor.exe --export
```

---

## Dolby Vision EDID Technical Details

> This section documents the EDID data structure for Dolby Vision, the meaning of each field, and how to force-enable Dolby Vision PC mode on Windows by modifying the EDID.

### 1. Where is Dolby Vision Data in EDID?

#### EDID Basic Structure

EDID (Extended Display Identification Data) is binary data that a monitor uses to report its capabilities to the system. On Windows, it is stored in the registry:

```
HKLM\SYSTEM\CurrentControlSet\Enum\DISPLAY\<model>\<instance ID>\Device Parameters\EDID
```

- Data type: `REG_BINARY`
- Common sizes: 128 / 256 / 384 bytes
- Every 128 bytes is one Block; the last byte of each block is its checksum
- Checksum rule: sum of first 127 bytes of a block mod 256 = 0 (checksum makes the total a multiple of 256)

#### CTA-861 Extension Block

Dolby Vision data is located in the CTA-861 Extension Block (Block 1 and beyond):

| Offset (relative to Block start) | Meaning |
|---|---|
| +0 | Tag = `0x02` (CTA-861 Extension) |
| +1 | Revision (usually `0x03`) |
| +2 | DTD Start Offset (Detailed Timing Descriptor start offset) |
| +3 | Byte count of native data block |
| +4 ~ +DTD Offset | Data Block Collection (all vendor data blocks here) |

#### Dolby Vision VSDB

Within the Data Block Collection, Dolby Vision's Vendor Specific Data Block is identified by its IEEE OUI (Organizationally Unique Identifier):

- **Dolby IEEE OUI**: `0x000D046`
- **Little-endian storage**: `46 D0 00`
- After finding the OUI, the following **7 bytes** are the Dolby Vision Payload

```
46 D0 00 | 4D 0A 9F 58 98 AA 5C
OUI(3B)  |   Payload(7B)
```

---

### 2. Dolby Vision Payload Structure (7 Bytes)

Using Payload `4D 0A 9F 58 98 AA 5C` as an example:

| Byte | Offset | Value | Meaning |
|---|---|---|---|
| Byte 0 | +0 | `0x4D` | Dolby Vision version (0x4D = Dolby Vision Version 4) |
| Byte 1 | +1 | `0x0A` | Minimum backward-compatible version/profile flag |
| **Byte 2** | **+2** | **`0x9F`** | **Dolby Vision Capability (core field, 8 bits)** |
| Byte 3 | +3 | `0x58` | Supported brightness info (forward compatible) |
| Byte 4-6 | +4~+6 | `98 AA 5C` | Reserved / vendor-specific data |

**Byte 2 (Dolby Vision Capability) is the most critical field. Windows uses it to determine the monitor's DV capabilities.**

---

### 3. Dolby Vision Capability Bit-by-Bit Explanation

Using `0x9F = 10011111` as an example:

| Bit | Name | Meaning | Notes |
|---|---|---|---|
| **Bit 0** | **DV over HDMI** | **Standard HDMI Dolby Vision signaling** | **The key bit for Windows Dolby Vision PC mode. Set to 1 → system recognizes DV support → "Use Dolby Vision" toggle appears in Settings → Display → HDR. Set to 0 → manufacturer's way to save on DV PC licensing fees.** |
| Bit 1 | DV over MHL | MHL interface Dolby Vision | Transmits DV over MHL (Mobile High-Definition Link), for mobile device interfaces; no effect on PC HDMI connections |
| Bit 2 | Backlight Control | Backlight control (Local Dimming) | Declares monitor supports backlight control via DV metadata; system can coordinate with the panel for more precise brightness adjustment |
| Bit 3 | Profile 8 | Profile 8 (BL+RPU) | Mainstream streaming Profile. Base layer is HDR10 (10-bit YUV 4:2:2), enhancement layer only contains RPU metadata (MEL), no extra video bandwidth. Used by Netflix, Disney+, Amazon Prime Video, etc. |
| Bit 4 | Profile 7 | Profile 7 (BL+FEL dual layer) | Full dual-layer structure, enhancement layer contains complete 12-bit video data (FEL). Base layer is HDR10-compatible. Best picture quality but highest bandwidth requirement. Used by 4K UHD Blu-ray Dolby Vision discs |
| Bit 5 | Profile 5 | Profile 5 (RGB 4:4:4) | RGB 4:4:4 12-bit lossless, no HDR10 base layer, **NOT HDR10-compatible** (device must natively support DV to decode). Better color than P8 but highest bandwidth requirement. Used by Apple TV+ native Dolby content (Apple TV 4K only) |
| Bit 6 | Low Latency Dolby Vision | Low Latency Dolby Vision (LLDV) | For gaming scenarios; sacrifices metadata precision (12-bit → 10-bit) in exchange for lower video processing latency. Not recommended for monitors prioritizing picture quality |
| Bit 7 | DV Version Report | Dolby Vision version report | Declares support for reporting DV version number via VSDB; drivers/system use this to read subsequent version fields |

---

### 4. Dolby Vision Profiles Comparison

| Profile | Signal Method | Bit Depth | Color Format | Bandwidth Req. | HDR10 Backward Compat. | Content Sources | Target Audience |
|---|---|---|---|---|---|---|---|
| **Profile 5** | BL + RPU (no video EL) | 12-bit | RGB 4:4:4 (IPTPQ) | Highest ~20 Gbps @4K60 | **No** | Apple TV+ native DV content, some UHD Blu-rays | Apple TV 4K users |
| **Profile 7** | BL + FEL dual layer (full EL) | 12-bit | YUV 4:2:2 | High | Yes (base = HDR10) | 4K UHD Blu-ray Dolby Vision discs | Home theater / disc players |
| **Profile 8** | BL + RPU (no video EL) | 12-bit processing / 10-bit base | YUV 4:2:2 or 4:2:0 | Moderate | Yes (base = HDR10) | Netflix, Disney+, Amazon Prime Video, etc. | Mainstream consumers |

> **P5 vs P8 core difference**: P5 uses RGB 4:4:4 (IPTPQ) color encoding with minimal color loss, but is NOT HDR10-compatible (device must natively support DV to decode); P8 uses YUV 4:2:2 (or 4:2:0), with slight color loss but the base layer can be directly decoded as HDR10, offering better compatibility.

> **Why don't streaming services use P5?** P5's RGB 4:4:4 signal has extremely high bandwidth demands, putting great pressure on streaming transmission; P8's YUV 4:2:2 can significantly reduce bitrate while maintaining picture quality. Apple TV+ is an exception — it only plays on Apple TV 4K devices with a controlled hardware environment, so it uses P5 directly.

> **For daily use, only Profile 7 and Profile 8 matter.** Profile 5 is only used by a few content sources like Apple TV+, and requires Apple TV 4K for the full experience.

---

### 5. Why Some Monitors Have Hardware DV Support But Windows Doesn't Show PC Mode

#### Dolby Licensing Mechanism

Dolby Vision licensing is **tiered by fee**:

| Mode | Licensing Target | Fee |
|---|---|---|
| Dolby Vision TV Mode | TV / projector manufacturers | Lower, base license |
| Dolby Vision PC Mode | Monitor / PC manufacturers | **Additional fee, separate license required** |

Many monitor manufacturers' strategy:
- Hardware fully supports Dolby Vision (panel, processing chip both present)
- Works normally when connected to PS5, Xbox, etc. ("TV mode" signal)
- But **sets Bit 0 to 0 in EDID**, declaring "I am not a DV PC monitor"
- This **saves on the Dolby Vision PC licensing fee**
- After Windows reads EDID and thinks DV is not supported → Dolby Vision PC option does not appear

#### Other Manufacturers' Labeling

Some manufacturers advertise both modes because they licensed both:
- "Dolby Vision" (TV mode, activated when connected to game consoles, etc.)
- "Dolby Vision PC" (PC mode, an extra toggle appears under Windows HDR)

**Those that only advertise "Dolby Vision" without "Dolby Vision PC" most likely did not purchase the PC license.**

---

### 6. How to Enable Dolby Vision PC Mode

#### Overview

Only need to modify **Bit 0** of the Dolby Vision Capability in EDID (change from 0 to 1), and recalculate the checksum of the corresponding Block.

#### Actual Modification (2 Bytes)

| Byte | Before | After | Notes |
|---|---|---|---|
| DV Capability | `0x9E` | `0x9F` | Flip Bit 0 (DV over HDMI = 1) |
| Block Checksum | Corresponding value | `0x100 - (sum mod 256)` | Recalculate first 127 bytes of Block 1 |

#### Modification Methods

1. **CRU (Custom Resolution Utility)** — Recommended; import the modified `.bin` file, then run `Restart64.exe` to restart the GPU driver
2. **Direct registry write** — Use administrator privileges to write the EDID key value, then re-plug the display cable or restart
3. **DV Payload Editor tool** — See below

---

### 7. Precautions

- After modifying EDID, you need to re-plug the display cable or restart the GPU driver (`Restart64.exe` bundled with CRU) for changes to take effect
- Always back up the original EDID before modifying (the tool automatically backs up to `%TEMP%`)
- When using AW EDID Editor (AWE) or similar tools to modify EDID, note: it re-serializes the entire CTA-861 extension block, which may break VRR, refresh rate, and other data. It is recommended to only perform single-byte precise modifications
- Dolby Vision toggle location on Windows 11: **Settings → System → Display → HDR → Use Dolby Vision**
- Windows does not have a separate Low Latency Dolby Vision toggle; only the main Dolby Vision on/off switch exists

---

## How It Works

1. Reads EDID from Windows registry (`HKLM\...\DISPLAY\...\Device Parameters\EDID`)
2. Locates Dolby Vision VSDB by searching for IEEE OUI `46 D0 00` in CTA-861 extension blocks
3. Modifies the DV Capability byte (3rd byte of the VSDB payload)
4. Recalculates the 128-byte block checksum
5. Writes back to registry or exports as `.bin`

## Build from Source

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name DolbyVisionPayloadEditor DolbyVisionPayloadEditor.py
```

## Warning

- Always backup your EDID before modifying (the tool does this automatically to `%TEMP%`)
- For CRU method: use the exported `.bin` and run `Restart64.exe` after importing
- **DO NOT** use AW EDID Editor (AWE) for DV modifications — it rewrites the entire CTA-861 block, potentially breaking VRR and refresh rate data

## License

MIT License

## References

- [balu100/dolby-vision-for-windows (GitHub)](https://github.com/balu100/dolby-vision-for-windows)
- CTA-861-H Standard
- Dolby Vision Licensing
