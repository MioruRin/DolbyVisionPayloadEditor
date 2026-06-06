#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DolbyVisionPayloadEditor - Dolby Vision EDID Export & Patch Tool (Console)
"""

import sys
import os
import subprocess
import winreg
from pathlib import Path
from datetime import datetime

if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).resolve().parent

REG_PATH = r"SYSTEM\CurrentControlSet\Enum\DISPLAY"
DOLBY_OUI_LE = bytes([0x46, 0xD0, 0x00])

def read_reg_binary(path, value_name):
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
        data, regtype = winreg.QueryValueEx(key, value_name)
        winreg.CloseKey(key)
        return bytes(data)
    except Exception:
        return None

def get_monitor_name():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REG_PATH)
        models = winreg.QueryInfoKey(key)[0]
        for i in range(models):
            model = winreg.EnumKey(key, i)
            model_key = winreg.OpenKey(key, model)
            instances = winreg.QueryInfoKey(model_key)[0]
            for j in range(instances):
                instance = winreg.EnumKey(model_key, j)
                reg_path = f"{REG_PATH}\\{model}\\{instance}\\Device Parameters"
                edid = read_reg_binary(reg_path, "EDID")
                if edid and len(edid) >= 128:
                    name = model
                    try:
                        fn_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                        fn, _ = winreg.QueryValueEx(fn_key, "FriendlyName")
                        winreg.CloseKey(fn_key)
                        if fn:
                            name = fn
                    except Exception:
                        pass
                    winreg.CloseKey(model_key)
                    winreg.CloseKey(key)
                    return name, edid
            winreg.CloseKey(model_key)
        winreg.CloseKey(key)
    except Exception:
        pass
    return None, None

def get_mode_suffix():
    try:
        ps = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance -ClassName Win32_VideoController | Select-Object -First 1 -ExpandProperty VideoModeDescription"],
            capture_output=True, text=True, timeout=5
        )
        mode = ps.stdout.strip()
        if mode:
            import re
            m = re.search(r'(\d+)\s*x\s*(\d+)', mode)
            if m:
                w, h = int(m.group(1)), int(m.group(2))
                if w >= 3840:
                    return "4K"
                elif w >= 2560:
                    return "1440p"
                else:
                    return "1080p"
    except Exception:
        pass
    return "current"

def find_dolby_vsdb(edid: bytes):
    if not edid or len(edid) < 256:
        return None
    total_blocks = len(edid) // 128
    for block_idx in range(1, total_blocks):
        start = block_idx * 128
        if edid[start] != 0x02:
            continue
        dtd_offset = edid[start + 2]
        if dtd_offset == 0:
            continue
        collection_start = start + 4
        collection_end = start + dtd_offset
        pos = collection_start
        while pos < collection_end:
            if pos >= len(edid):
                break
            header = edid[pos]
            block_len = (header & 0x1F) + 1
            payload_start = pos + 1
            for k in range(payload_start, min(payload_start + block_len - 1, len(edid) - 2)):
                if edid[k:k + 3] == DOLBY_OUI_LE:
                    return (block_idx, pos, k + 3)
            pos += block_len
    for block_idx in range(1, total_blocks):
        start = block_idx * 128
        if edid[start] != 0x02:
            continue
        idx = edid.find(DOLBY_OUI_LE, start + 4, start + 128)
        if idx >= 0:
            return (block_idx, idx - 3, idx + 3)
    return None

def parse_dv_payload(payload: bytes):
    if len(payload) < 7:
        return None
    cap = payload[2]
    return {
        "payload": payload[:7].hex().upper(),
        "cap_byte": cap,
        "cap_hex": f"0x{cap:02X}",
        "cap_bin": f"{cap:08b}",
        "bits": [bool(cap & (1 << b)) for b in range(8)],
    }

def patch_capability(edid: bytearray, new_cap: int):
    result = find_dolby_vsdb(bytes(edid))
    if result is None:
        raise ValueError("Dolby Vision VSDB not found in EDID")
    block_idx, _, payload_offset = result
    old_cap = edid[payload_offset + 2]
    edid[payload_offset + 2] = new_cap & 0xFF
    block_start = block_idx * 128
    cs_offset = block_start + 127
    total = sum(edid[block_start:cs_offset])
    new_cs = (0x100 - (total % 0x100)) % 0x100
    edid[cs_offset] = new_cs
    return edid, old_cap, new_cap

def action_export():
    name, edid = get_monitor_name()
    if not edid:
        print("[-] No monitor with EDID found in registry.", flush=True)
        return
    mode = get_mode_suffix()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{mode}_{ts}.bin"
    filepath = APP_DIR / filename
    filepath.write_bytes(edid)
    print(f"[OK] Exported EDID: {filepath}", flush=True)
    print(f"     Size: {len(edid)} bytes", flush=True)
    dv = find_dolby_vsdb(edid)
    if dv:
        _, _, po = dv
        payload = edid[po:po + 7]
        parsed = parse_dv_payload(payload)
        print(f"     DV Payload: {parsed["payload"]}", flush=True)
        print(f"     DV Capability: {parsed["cap_hex"]} = {parsed["cap_bin"]}", flush=True)
        dv_pc = "ON" if parsed["bits"][0] else "OFF"
        print(f"     DV PC Mode: {dv_pc}", flush=True)
    else:
        print("     [!] No Dolby Vision VSDB found.", flush=True)

def action_patch_file():
    print("\n--- Patch EDID File ---", flush=True)
    print("Enter path to .bin file (or drag & drop):", flush=True)
    user_input = input("> ").strip().strip('"').strip("'")
    filepath = Path(user_input)
    if not filepath.exists():
        print(f"[-] File not found: {filepath}", flush=True)
        return
    edid = bytearray(filepath.read_bytes())
    if len(edid) < 256:
        print(f"[-] Invalid EDID: only {len(edid)} bytes (need >= 256)", flush=True)
        return
    dv = find_dolby_vsdb(bytes(edid))
    if not dv:
        print("[-] No Dolby Vision VSDB found in this EDID.", flush=True)
        return
    _, _, po = dv
    payload = edid[po:po + 7]
    parsed = parse_dv_payload(payload)
    print(f"\n[+] Found Dolby Vision VSDB:", flush=True)
    print(f"     Payload: {parsed["payload"]}", flush=True)
    print(f"     Capability: {parsed["cap_hex"]} = {parsed["cap_bin"]}", flush=True)
    dv_pc = "ON" if parsed["bits"][0] else "OFF"
    print(f"     DV PC Mode: {dv_pc}", flush=True)
    if parsed["bits"][0]:
        print("\n[*] DV PC mode is already enabled. No change needed.", flush=True)
        return
    old_cap = edid[po + 2]
    new_cap = old_cap | 0x01
    edid_new, _, _ = patch_capability(edid, new_cap)
    stem = filepath.stem
    new_name = f"{stem}_DV_ON.bin"
    new_path = APP_DIR / new_name
    new_path.write_bytes(bytes(edid_new))
    print(f"\n[OK] Patched EDID saved: {new_path}", flush=True)
    print(f"     Capability: 0x{old_cap:02X} -> 0x{new_cap:02X}", flush=True)
    print(f"     DV PC Mode: OFF -> ON", flush=True)
    print(f"\n[*] Next step: Import this .bin into CRU, then run Restart64.exe", flush=True)

def action_read():
    name, edid = get_monitor_name()
    if not edid:
        print("[-] No monitor with EDID found in registry.", flush=True)
        return
    print(f"Monitor: {name}", flush=True)
    print(f"EDID Size: {len(edid)} bytes", flush=True)
    dv = find_dolby_vsdb(edid)
    if not dv:
        print("[-] No Dolby Vision VSDB found.", flush=True)
        return
    _, _, po = dv
    payload = edid[po:po + 7]
    parsed = parse_dv_payload(payload)
    print(f"\nDV Payload: {parsed["payload"]}", flush=True)
    print(f"DV Capability: {parsed["cap_hex"]} = {parsed["cap_bin"]}", flush=True)
    print(f"\nBit breakdown:", flush=True)
    bit_names = [
        "Bit 0: DV over HDMI (PC mode)",
        "Bit 1: DV over MHL",
        "Bit 2: Backlight Control",
        "Bit 3: Profile 8",
        "Bit 4: Profile 7",
        "Bit 5: Profile 5",
        "Bit 6: Low Latency DV",
        "Bit 7: DV Version Report",
    ]
    for i, name in enumerate(bit_names):
        s = "ON" if parsed["bits"][i] else "OFF"
        print(f"  [{i}] {name}: {s}", flush=True)

def show_menu():
    print("=" * 60, flush=True)
    print("  DolbyVisionPayloadEditor", flush=True)
    print("  Dolby Vision EDID Export & Patch Tool", flush=True)
    print("=" * 60, flush=True)
    print("", flush=True)
    print("  [1] Export current EDID to .bin", flush=True)
    print("  [2] Patch .bin file (enable DV PC mode)", flush=True)
    print("  [3] Read current monitor DV info", flush=True)
    print("  [0] Exit", flush=True)
    print("", flush=True)

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="DolbyVisionPayloadEditor - DV EDID Export & Patch Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--export", action="store_true", help="Quick export current EDID")
    parser.add_argument("--read", action="store_true", help="Read current monitor DV info")
    parser.add_argument("--patch", metavar="FILE", help="Patch EDID file (enable DV PC mode)")
    args = parser.parse_args()

    if args.export:
        action_export()
        return
    if args.read:
        action_read()
        return
    if args.patch:
        filepath = Path(args.patch)
        if not filepath.exists():
            print(f"[-] File not found: {filepath}", flush=True)
            return
        edid = bytearray(filepath.read_bytes())
        if len(edid) < 256:
            print("[-] Invalid EDID", flush=True)
            return
        dv = find_dolby_vsdb(bytes(edid))
        if not dv:
            print("[-] No Dolby Vision VSDB found.", flush=True)
            return
        _, _, po = dv
        old_cap = edid[po + 2]
        new_cap = old_cap | 0x01
        edid_new, _, _ = patch_capability(edid, new_cap)
        stem = filepath.stem
        new_path = APP_DIR / f"{stem}_DV_ON.bin"
        new_path.write_bytes(bytes(edid_new))
        print(f"[OK] Patched: {new_path}", flush=True)
        print(f"     0x{old_cap:02X} -> 0x{new_cap:02X}", flush=True)
        return

    while True:
        show_menu()
        try:
            choice = input("Select: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.", flush=True)
            break
        if choice == "1":
            action_export()
        elif choice == "2":
            action_patch_file()
        elif choice == "3":
            action_read()
        elif choice == "0":
            print("Bye.", flush=True)
            break
        else:
            print("Invalid choice.", flush=True)
        print("", flush=True)
        input("Press Enter to continue...")
        print("", flush=True)

if __name__ == "__main__":
    main()
