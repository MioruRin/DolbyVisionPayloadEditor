#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DolbyVisionPayloadEditor — Dolby Vision EDID 通用修改工具
Universal tool to modify Dolby Vision VSDB in any monitor's EDID.

Usage:
  DolbyVisionPayloadEditor.exe                  # Launch GUI
  DolbyVisionPayloadEditor.exe --list          # List all monitors
  DolbyVisionPayloadEditor.exe --read          # Read DV Payload
  DolbyVisionPayloadEditor.exe --patch         # Auto patch (flip bit 0)
  DolbyVisionPayloadEditor.exe --export        # Export patched EDID as .bin (for CRU)
"""

import sys
import os
import json
import base64
import struct
import subprocess
import ctypes
import ctypes.wintypes
import winreg
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# ─── Frozen exe detection ───────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).parent
    IS_FROZEN = True
else:
    APP_DIR = Path(__file__).resolve().parent
    IS_FROZEN = False

# ─── Constants ──────────────────────────────────────────────────────────
REG_PATH = r"SYSTEM\CurrentControlSet\Enum\DISPLAY"
HKLM = 0x80000002

# Dolby IEEE OUI: 0x000D046 stored as little-endian: 46 D0 00
DOLBY_OUI_LE = bytes([0x46, 0xD0, 0x00])

# ─── DV Capability bit definitions ───────────────────────────────────────────────
DV_BITS = [
    ("Bit 0: DV over HDMI",       "Standard HDMI Dolby Vision signaling (PC mode key)"),
    ("Bit 1: DV over MHL",        "MHL interface Dolby Vision"),
    ("Bit 2: Backlight Control",  "Backlight control (Local Dimming)"),
    ("Bit 3: Profile 8",          "Profile 8 (BL+EL, most common)"),
    ("Bit 4: Profile 7",          "Profile 7 (FEL full enhancement layer)"),
    ("Bit 5: Profile 5",          "Profile 5 (RGB 12-bit lossless)"),
    ("Bit 6: Low Latency DV",     "Low-latency Dolby Vision (gaming)"),
    ("Bit 7: DV Version Report",   "Dolby Vision version reporting"),
]

# ─── Utility functions ───────────────────────────────────────────────────

def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def run_as_admin(extra_args=None):
    """Relaunch current process as admin via UAC"""
    params = " ".join(f'"{a}"' if ' ' in a else a for a in sys.argv)
    if extra_args:
        params += " " + " ".join(f'"{a}"' if ' ' in a else a for a in extra_args)
    if IS_FROZEN:
        exe = sys.executable
    else:
        exe = sys.executable + ' "' + str(Path(__file__).resolve()) + '"'
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", exe, params, str(APP_DIR), 1
    )
    sys.exit(0)

def read_reg_binary(path, value_name):
    """Read REG_BINARY from registry"""
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
        data, regtype = winreg.QueryValueEx(key, value_name)
        winreg.CloseKey(key)
        return bytes(data)
    except Exception as e:
        return None

def write_reg_binary(path, value_name, data: bytes):
    """Write REG_BINARY to registry (requires admin)"""
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WRITE)
        winreg.SetValueEx(key, value_name, 0, winreg.REG_BINARY, data)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_ALL_ACCESS)
            winreg.SetValueEx(key, value_name, 0, winreg.REG_BINARY, data)
            winreg.CloseKey(key)
            return True
        except Exception as e2:
            return False

def find_dolby_vsdb(edid: bytes):
    """
    Locate Dolby Vision VSDB in EDID.
    Strategy: scan ALL data blocks in CTA-861 extension blocks for Dolby OUI,
    regardless of block tag (some monitors store DV in non-tag-3 blocks).
    Falls back to raw byte scan if structured parsing finds nothing.
    Returns: (block_index, vsdb_start, payload_start) or None
    """
    if not edid or len(edid) < 256:
        return None

    total_blocks = len(edid) // 128

    # --- Pass 1: structured parsing of CTA-861 Data Block Collection ---
    for block_idx in range(1, total_blocks):
        start = block_idx * 128
        if edid[start] != 0x02:
            continue
        rev = edid[start + 1]
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

            # Scan payload area (after header byte) for Dolby OUI
            payload_start = pos + 1
            for k in range(payload_start, min(payload_start + block_len - 1, len(edid) - 2)):
                if edid[k:k + 3] == DOLBY_OUI_LE:
                    dv_payload_start = k + 3
                    return (block_idx, pos, dv_payload_start)
            pos += block_len

    # --- Pass 2: raw scan entire extension blocks (fallback) ---
    for block_idx in range(1, total_blocks):
        start = block_idx * 128
        if edid[start] != 0x02:
            continue
        idx = edid.find(DOLBY_OUI_LE, start + 4, start + 128)
        if idx >= 0:
            return (block_idx, idx - 3, idx + 3)

    return None

def parse_dv_payload(payload: bytes):
    """Parse 7-byte DV VSDB Payload, return dict or None"""
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
    """
    Modify DV Capability byte in EDID and recalculate checksum.
    Returns: (modified_edid, old_cap, new_cap)
    """
    result = find_dolby_vsdb(bytes(edid))
    if result is None:
        raise ValueError("Dolby Vision VSDB not found in EDID")
    block_idx, _, payload_offset = result
    old_cap = edid[payload_offset + 2]
    edid[payload_offset + 2] = new_cap & 0xFF

    # Recalculate checksum for this block
    block_start = block_idx * 128
    cs_offset = block_start + 127
    total = sum(edid[block_start:cs_offset])
    new_cs = (0x100 - (total % 0x100)) % 0x100
    edid[cs_offset] = new_cs

    return edid, old_cap, new_cap

def list_monitors():
    """Enumerate all monitors with EDID from registry"""
    monitors = []
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
                    dv = find_dolby_vsdb(edid)
                    monitors.append({
                        "model": model,
                        "instance": instance,
                        "reg_path": reg_path,
                        "edid": edid,
                        "has_dv": dv is not None,
                    })
            winreg.CloseKey(model_key)
        winreg.CloseKey(key)
    except Exception as e:
        pass
    return monitors

def backup_edid(edid: bytes, name: str) -> Path:
    """Backup EDID to temp directory"""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    p = Path(tempfile.gettempdir()) / f"DV_Editor_backup_{name}_{ts}.bin"
    p.write_bytes(edid)
    return p

def export_bin(edid: bytes, name: str) -> Path:
    """Export EDID as .bin to Desktop"""
    desktop = Path(os.path.expanduser("~")) / "Desktop"
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    p = desktop / f"{name}_DV_{ts}.bin"
    p.write_bytes(edid)
    return p

def admin_write_mode(json_file):
    """
    Called when relaunched with --admin-write <json_file>.
    Loads state from temp JSON, writes EDID to registry, shows GUI messagebox, then exits.
    """
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()

    try:
        with open(json_file, "r") as f:
            data = json.load(f)

        reg_path = data["reg_path"]
        original_edid = base64.b64decode(data["original_edid"])
        modified_edid = base64.b64decode(data["modified_edid"])
        model = data.get("model", "unknown")

        # Backup original EDID
        bak = backup_edid(original_edid, model)

        # Write modified EDID to registry
        ok = write_reg_binary(reg_path, "EDID", modified_edid)

        if ok:
            # Try to trigger PnP re-enumeration so Windows re-reads EDID
            try:
                ctypes.windll.user32.SendNotifyMessageW(
                    0xFFFF,   # HWND_BROADCAST
                    0x001A,  # WM_SETTINGCHANGE
                    0,
                    0
                )
            except Exception as e2:
                pass

            msg = (
                f"EDID written to registry successfully!\n\n"
                f"Backup saved to:\n{bak}\n\n"
                f"To apply changes, do ONE of:\n"
                f"  1. Unplug & re-plug display cable (HDMI/DP)\n"
                f"  2. Device Manager → Display adapters → right-click → Disable, then Enable\n"
                f"  3. Restart computer"
            )
            messagebox.showinfo("DolbyVisionPayloadEditor – Success", msg)
        else:
            msg = (
                f"Failed to write EDID to registry.\n\n"
                f"Try running as administrator manually."
            )
            messagebox.showerror("DolbyVisionPayloadEditor – Error", msg)

        # Clean up temp file
        try:
            os.unlink(json_file)
        except Exception:
            pass

    except Exception as e:
        msg = f"Admin write mode failed:\n\n{str(e)}"
        try:
            import traceback
            msg += f"\n\n{traceback.format_exc()[:500]}"
        except Exception:
            pass
        messagebox.showerror("DolbyVisionPayloadEditor – Error", msg)

    finally:
        try:
            root.destroy()
        except Exception:
            pass
        sys.exit(0)


# ─── GUI ───────────────────────────────────────────────────────────────

def launch_gui():
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog, scrolledtext

    # -- State --
    state = {
        "monitors": [],
        "sel_idx": None,
        "current_edid": None,      # bytearray (working copy)
        "original_edid": None,     # bytes (original backup)
        "current_reg": None,
        "bit_vars": [],
        "applied": False,         # patch applied to memory
    }

    root = tk.Tk()
    root.title("DolbyVisionPayloadEditor – Dolby Vision EDID Tool")
    root.geometry("780x720")
    root.minsize(600, 500)

    # ── Section 1: Monitor Selection ──
    sec1 = ttk.LabelFrame(root, text="  1. Select Monitor  ", padding=8)
    sec1.pack(fill="x", padx=10, pady=(10, 4))

    lb = tk.Listbox(sec1, height=4, font=("Consolas", 9), selectmode="browse")
    lb.pack(fill="x", padx=4, pady=2)

    row_btn1 = ttk.Frame(sec1)
    row_btn1.pack(fill="x", pady=4)
    ttk.Button(row_btn1, text="Refresh", command=lambda: refresh_list()).pack(side="left", padx=4)
    lbl_admin = ttk.Label(row_btn1, text="")
    lbl_admin.pack(side="right", padx=4)
    if is_admin():
        lbl_admin.config(text="[Admin]", foreground="green")
    else:
        lbl_admin.config(text="[Non-Admin – write needs UAC]", foreground="orange")

    # ── Section 2: DV Capability Editor ──
    sec2 = ttk.LabelFrame(root, text="  2. DV Capability Editor  ", padding=8)
    sec2.pack(fill="x", padx=10, pady=4)

    lbl_info = ttk.Label(sec2, text="Select a monitor with DV support above.", justify="left",
                         font=("Consolas", 9), wraplength=700)
    lbl_info.pack(anchor="w", padx=4, pady=4)

    grid_bits = ttk.Frame(sec2)
    grid_bits.pack(fill="x", padx=4, pady=4)
    for i in range(8):
        var = tk.BooleanVar()
        state["bit_vars"].append(var)
        name, desc = DV_BITS[i]
        chk = ttk.Checkbutton(grid_bits, text=name, variable=var)
        chk.grid(row=i // 2, column=(i % 2), sticky="w", padx=10, pady=2)
        chk.bind("<Enter>", lambda e, d=desc: lbl_info.config(text=d))

    row_quick = ttk.Frame(sec2)
    row_quick.pack(fill="x", pady=4)
    ttk.Button(row_quick, text="Enable DV PC (Bit 0)",
               command=lambda: enable_dv_pc()).pack(side="left", padx=4)
    ttk.Button(row_quick, text="Enable Low Latency (Bit 6)",
               command=lambda: enable_low_latency()).pack(side="left", padx=4)
    ttk.Button(row_quick, text="Restore Original",
               command=lambda: restore_original()).pack(side="left", padx=4)

    # ── Section 3: Actions ──
    sec3 = ttk.LabelFrame(root, text="  3. Actions  ", padding=8)
    sec3.pack(fill="both", expand=True, padx=10, pady=(4, 10))

    txt_log = scrolledtext.ScrolledText(sec3, height=12, font=("Consolas", 9), state="disabled")
    txt_log.pack(fill="both", expand=True, padx=4, pady=4)

    row_btn3 = ttk.Frame(sec3)
    row_btn3.pack(fill="x", pady=4)
    ttk.Button(row_btn3, text="Apply (Memory)", command=lambda: do_apply()).pack(side="left", padx=4)
    ttk.Button(row_btn3, text="Write Registry", command=lambda: do_write()).pack(side="left", padx=4)
    ttk.Button(row_btn3, text="Export .bin", command=lambda: do_export()).pack(side="left", padx=4)
    ttk.Button(row_btn3, text="Exit", command=root.quit).pack(side="right", padx=4)

    def log(msg):
        txt_log.config(state="normal")
        txt_log.insert(tk.END, msg + "\n")
        txt_log.see(tk.END)
        txt_log.config(state="disabled")

    def refresh_list():
        lb.delete(0, tk.END)
        state["monitors"] = list_monitors()
        state["sel_idx"] = None
        state["current_edid"] = None
        state["original_edid"] = None
        state["applied"] = False
        lbl_info.config(text="Select a monitor.")
        for v in state["bit_vars"]:
            v.set(False)
        if not state["monitors"]:
            lb.insert(tk.END, "No monitors found. Run as Admin.")
            return
        for i, m in enumerate(state["monitors"]):
            dv = "DV" if m["has_dv"] else "--"
            lb.insert(tk.END, f"[{dv}] {m['model']}  ({m['instance'][:24]})  {len(m['edid'])}B")

    def on_select(evt):
        sel = lb.curselection()
        if not sel or sel[0] >= len(state["monitors"]):
            return
        idx = sel[0]
        mon = state["monitors"][idx]
        state["sel_idx"] = idx
        state["current_edid"] = bytearray(mon["edid"])
        state["original_edid"] = bytes(mon["edid"])
        state["current_reg"] = mon["reg_path"]
        state["applied"] = False

        if not mon["has_dv"]:
            lbl_info.config(text="No Dolby Vision VSDB found in this monitor's EDID.")
            for v in state["bit_vars"]:
                v.set(False)
            return

        dv = find_dolby_vsdb(mon["edid"])
        _, _, po = dv
        payload = mon["edid"][po:po + 7]
        parsed = parse_dv_payload(payload)

        for i in range(8):
            state["bit_vars"][i].set(parsed["bits"][i])

        dv_pc = "ON" if parsed["bits"][0] else "OFF"
        ll = "ON" if parsed["bits"][6] else "OFF"
        lbl_info.config(
            text=f"Payload: {parsed['payload']}  |  Cap: {parsed['cap_hex']} = {parsed['cap_bin']}  |  DV PC: {dv_pc}  |  Low Latency: {ll}"
        )

    def enable_dv_pc():
        state["bit_vars"][0].set(True)
        log("[+] Bit 0 (DV over HDMI) = 1")

    def enable_low_latency():
        state["bit_vars"][6].set(True)
        log("[+] Bit 6 (Low Latency DV) = 1")

    def restore_original():
        if state["original_edid"] is None:
            return
        state["current_edid"] = bytearray(state["original_edid"])
        state["applied"] = False
        log("[*] Restored original EDID in memory.")
        on_select(None)

    def do_apply():
        if state["current_edid"] is None:
            messagebox.showwarning("Warning", "Select a monitor first.")
            return
        new_cap = 0
        for i in range(8):
            if state["bit_vars"][i].get():
                new_cap |= (1 << i)
        try:
            edid_new, old_cap, _ = patch_capability(bytearray(state["current_edid"]), new_cap)
            state["current_edid"] = edid_new
            state["applied"] = True
            log(f"[OK] Patch applied: 0x{old_cap:02X} -> 0x{new_cap:02X}")
            log(f"     Binary: {old_cap:08b} -> {new_cap:08b}")
        except ValueError as e:
            log(f"[ERR] {e}")

    def do_write():
        if state["current_edid"] is None:
            messagebox.showwarning("Warning", "Select a monitor first.")
            return
        if not state["applied"]:
            messagebox.showwarning("Warning", "Apply changes first.")
            return

        if not is_admin():
            # Save state to temp JSON, then relaunch with --admin-write
            temp_dir = tempfile.gettempdir()
            json_file = os.path.join(temp_dir, "dv_editor_admin_write.json")
            data = {
                "reg_path": state["current_reg"],
                "original_edid": base64.b64encode(state["original_edid"]).decode("ascii"),
                "modified_edid": base64.b64encode(bytes(state["current_edid"])).decode("ascii"),
                "model": state["monitors"][state["sel_idx"]]["model"]
            }
            with open(json_file, "w") as f:
                json.dump(data, f)
            log(f"[*] Not admin. State saved to: ...{os.path.basename(json_file)}")
            log("[*] Relaunching as admin...")
            run_as_admin([f"--admin-write={json_file}"])
            # run_as_admin calls sys.exit(), so we don't reach here
            return

        # --- Admin path: write directly ---
        bak = backup_edid(state["original_edid"], state["monitors"][state["sel_idx"]]["model"])
        ok = write_reg_binary(state["current_reg"], "EDID", bytes(state["current_edid"]))
        if ok:
            log(f"[OK] Written to registry. Backup: {bak}")
            # Try to trigger PnP re-enumeration
            try:
                ctypes.windll.user32.SendNotifyMessageW(
                    0xFFFF, 0x001A, 0, 0
                )
                log("[OK] Sent WM_SETTINGCHANGE broadcast.")
            except Exception as e2:
                log(f"[!] Could not send notify: {e2}")
            messagebox.showinfo(
                "Success",
                "EDID written to registry successfully!\n\n"
                "To apply changes, do ONE of:\n"
                "  1. Unplug & re-plug display cable (HDMI/DP)\n"
                "  2. Device Manager → Display adapters → right-click → Disable, then Enable\n"
                "  3. Restart computer"
            )
        else:
            log("[ERR] Write failed. Check admin permissions.")
            messagebox.showerror("Error", "Write failed.")

    def do_export():
        if state["current_edid"] is None:
            messagebox.showwarning("Warning", "Select a monitor first.")
            return
        dst = filedialog.asksaveasfilename(
            )
        if dst:
            p = Path(dst)
            if state["applied"]:
                p.write_bytes(bytes(state["current_edid"]))
            else:
                p.write_bytes(bytes(state["original_edid"]))
            log(f"[OK] Exported: {p}")
            messagebox.showinfo("Export", f"Saved to:\n{p}")

    lb.bind("<<ListboxSelect>>", on_select)
    refresh_list()
    root.mainloop()


# ─── CLI Commands ──────────────────────────────────────────────────────

def cmd_list():
    print("=" * 60)
    print("  Monitor List")
    print("=" * 60)
    monitors = list_monitors()
    if not monitors:
        print("[-] No monitors found.")
        return
    for i, m in enumerate(monitors):
        print(f"\n[{i}] Model: {m['model']}")
        print(f"    Instance: {m['instance']}")
        print(f"    EDID: {len(m['edid'])} bytes")
        print(f"    DV VSDB: {'Yes' if m['has_dv'] else 'No'}")
    print(f"\nTotal: {len(monitors)} monitor(s)")

def cmd_read():
    monitors = list_monitors()
    target = None
    for m in monitors:
        if m["has_dv"]:
            target = m
    if not target:
        print("[-] No DV-capable monitor found.")
        return
    dv = find_dolby_vsdb(target["edid"])
    _, _, po = dv
    payload = target["edid"][po:po + 7]
    parsed = parse_dv_payload(payload)
    print(f"Monitor: {target['model']}")
    print(f"Payload: {parsed['payload']}")
    print(f"Capability: {parsed['cap_hex']} = {parsed['cap_bin']}")
    print()
    for i, (name, desc) in enumerate(DV_BITS):
        s = "ON" if parsed["bits"][i] else "OFF"
        print(f"  [{i}] {name}: {s}")

def cmd_patch():
    """Auto-enable DV PC mode (flip bit 0), with admin auto-write"""
    monitors = list_monitors()
    target = None
    for m in monitors:
        if m["has_dv"]:
            target = m
    if not target:
        print("[-] No DV-capable monitor found.")
        return

    edid = bytearray(target["edid"])
    dv = find_dolby_vsdb(bytes(edid))
    _, _, po = dv
    old_cap = edid[po + 2]
    new_cap = old_cap | 0x01

    print(f"Monitor: {target['model']}")
    print(f"Capability: 0x{old_cap:02X} -> 0x{new_cap:02X}")
    print(f"Bit 0 (DV over HDMI): {old_cap & 1} -> {new_cap & 1}")
    print()

    # Patch in memory first
    edid_new, _, _ = patch_capability(edid, new_cap)

    if not is_admin():
        # Save state to temp JSON, then relaunch with --admin-write
        import json, base64, tempfile
        temp_dir = tempfile.gettempdir()
        json_file = os.path.join(temp_dir, "dv_editor_admin_write.json")
        data = {
            "reg_path": target["reg_path"],
            "original_edid": base64.b64encode(target["edid"]).decode("ascii"),
            "modified_edid": base64.b64encode(bytes(edid_new)).decode("ascii"),
            "model": target["model"]
        }
        with open(json_file, "w") as f:
            json.dump(data, f)
        print(f"[*] Not admin. State saved to: {json_file}")
        print("[*] Relaunching as admin...")
        run_as_admin([f"--admin-write={json_file}"])
        # run_as_admin calls sys.exit(), so we don't reach here
        return

    # Admin path: patch and write directly
    bak = backup_edid(target["edid"], target["model"])
    print(f"Backup: {bak}")

    ok = write_reg_binary(target["reg_path"], "EDID", bytes(edid_new))
    if ok:
        print("[OK] Written to registry.")
        # Try to trigger PnP re-enumeration
        try:
            ctypes.windll.user32.SendNotifyMessageW(
                0xFFFF, 0x001A, 0, 0
            )
            print("[OK] Sent WM_SETTINGCHANGE broadcast.")
        except Exception as e2:
            print(f"[!] Could not send notify: {e2}")
        print("[*] ACTION REQUIRED:")
        print("    Re-plug the display cable (HDMI/DP), OR")
        print("    Go to Device Manager → Display adapters → right-click → Disable, then Enable.")
    else:
        print("[ERR] Write failed.")

def cmd_export():
    """Export patched EDID as .bin for CRU"""
    monitors = list_monitors()
    target = None
    for m in monitors:
        if m["has_dv"]:
            target = m
    if not target:
        print("[-] No DV-capable monitor found.")
        return

    edid = bytearray(target["edid"])
    dv = find_dolby_vsdb(bytes(edid))
    _, _, po = dv
    old_cap = edid[po + 2]
    new_cap = old_cap | 0x01

    edid_new, _, _ = patch_capability(edid, new_cap)
    p = export_bin(bytes(edid_new), target["model"])
    print(f"[OK] Exported to: {p}")
    print("     Import this .bin in CRU, then run Restart64.exe")


# ─── Main ───────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="DolbyVisionPayloadEditor – Universal Dolby Vision EDID Tool",
        epilog="Examples:\n"
               "  DolbyVisionPayloadEditor.exe          # GUI\n"
               "  DolbyVisionPayloadEditor.exe --list    # List monitors\n"
               "  DolbyVisionPayloadEditor.exe --patch   # Auto enable DV PC\n"
               "  DolbyVisionPayloadEditor.exe --export  # Export .bin for CRU",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--list",   action="store_true")
    parser.add_argument("--read",   action="store_true")
    parser.add_argument("--patch",  action="store_true")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--cli",    action="store_true", help="Force CLI mode")
    parser.add_argument("--admin-write", metavar="FILE", help="Admin write mode (internal use)")
    # Hidden flag: if set, skips admin relaunch (used internally)
    parser.add_argument("--skip-admin-relaunch", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args()

    # --admin-write: called from admin-relaunched process, does the actual registry write
    if args.admin_write:
        admin_write_mode(args.admin_write)

    if args.list:
        cmd_list()
    elif args.read:
        cmd_read()
    elif args.patch:
        cmd_patch()
    elif args.export:
        cmd_export()
    else:
        # Default: GUI
        try:
            launch_gui()
        except Exception as e:
            import traceback
            detail = traceback.format_exc()
            print(f"[!] GUI failed: {e}")
            print(detail)
            print("    Try: DolbyVisionPayloadEditor.exe --list")
            # Show error dialog even in windowed mode
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("DolbyVisionPayloadEditor Error",
                    f"GUI failed to start:\n\n{e}\n\nTry running with --list first.\n\n{detail}")
                root.destroy()
            except Exception:
                pass


if __name__ == "__main__":
    main()
