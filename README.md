# DolbyVisionPayloadEditor

A universal Windows tool to modify Dolby Vision VSDB in any monitor's EDID, enabling Dolby Vision PC mode on displays that support it hardware-wise but have it disabled by the manufacturer.

![Platform](https://img.shields.io/badge/platform-Windows-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/Python-3.13-yellow)

## What It Does

Many monitors support Dolby Vision hardware-wise but have Bit 0 of the DV Capability byte set to 0 in their EDID to save on Dolby Vision PC licensing fees. This tool lets you flip that bit, enabling Dolby Vision PC mode in Windows.

## Features

- Auto-scan all monitors for Dolby Vision VSDB (IEEE OUI `0x000D046`)
- Visual 8-bit checkbox editor for Dolby Vision Capability
- One-click enable DV PC Mode (Bit 0) and Low Latency Mode (Bit 6)
- Automatic EDID backup + checksum recalculation
- UAC auto-elevation for registry writes
- Export `.bin` for CRU (Custom Resolution Utility) import
- CLI mode for scripting

## Download

Download the latest release from [Releases](https://github.com/MioruRin/DolbyVisionPayloadEditor/releases).

## Usage

### GUI Mode

```
DolbyVisionPayloadEditor.exe
```

1. Select your monitor from the list
2. Toggle DV capability bits as needed
3. Click **Apply (Memory)** then **Write Registry** (requires admin)
4. Re-plug your display cable or restart the GPU driver

### CLI Mode

```bash
# List all monitors
DolbyVisionPayloadEditor.exe --list

# Read Dolby Vision payload
DolbyVisionPayloadEditor.exe --read

# Auto-patch (enable DV PC mode)
DolbyVisionPayloadEditor.exe --patch

# Export patched EDID as .bin for CRU
DolbyVisionPayloadEditor.exe --export
```

## Documentation

See [DolbyVision_EDID_Guide.md](DolbyVision_EDID_Guide.md) for a detailed guide on Dolby Vision EDID structure, payload bits, profiles, and licensing.

## Build from Source

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name DolbyVisionPayloadEditor DolbyVisionPayloadEditor.py
```

## How It Works

1. Reads EDID from Windows registry (`HKLM\...\DISPLAY\...\Device Parameters\EDID`)
2. Locates Dolby Vision VSDB by searching for IEEE OUI `46 D0 00` in CTA-861 extension blocks
3. Modifies the DV Capability byte (7th byte of the VSDB payload)
4. Recalculates the 128-byte block checksum
5. Writes back to registry or exports as `.bin`

## Warning

- Always backup your EDID before modifying (the tool does this automatically to `%TEMP%`)
- For CRU method: use the exported `.bin` and run `Restart64.exe` after importing
- Do NOT use AW EDID Editor (AWE) for DV modifications -- it rewrites the entire CTA-861 block, potentially breaking VRR and refresh rate data

## License

MIT License
