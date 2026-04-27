#!/usr/bin/env python3
VERSION = "1.0.3"
BUILD   = "2026-04-05-1"

import sys
import os
import json
import argparse
import urllib.request
import urllib.parse

# https://github.com/sidchoudhuri/assembly64_cli
BASE         = "https://hackerswithstyle.se/leet/"
HEADERS      = {"client-id": "assembly64_cli", "Accept": "application/json"}
CONFIG_DIR  = os.path.expanduser("~/.assembly64")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

CATEGORIES = {
    "demos":    "demos",
    "games":    "games",
    "graphics": "graphics",
    "music":    "music",
    "discmags": "discmags",
    "tools":    "tools",
    "sid":      "hvscmusic",
    "hvsc":     "hvscmusic",
    "misc":     "c64misc",
    "intros":   "intros",
    "c128":     "c128stuff",
    "bbs":      "bbs",
    "charts":   "charts",
}

CAT_IDS = {
    "demos": 1, "games": 0, "graphics": 3, "music": 4,
    "discmags": 5, "tools": 8, "sid": 18, "hvsc": 18,
    "misc": 7, "intros": 11, "c128": 2, "bbs": 6, "charts": 9,
}

REPOS = {
    "csdb", "gamebase64", "guybrush", "hvsc", "mayhem",
    "oneload", "pres", "seuck", "tapes", "c64com",
    "c64orgintro", "commodore", "utape",
}

ULTIMATE_RUNNERS = {
    ".prg": "run_prg",
    ".crt": "run_crt",
    ".sid": "sidplay",
}

DISK_TYPES = {".d64": "d64", ".g64": "g64", ".d71": "d71", ".g71": "g71", ".d81": "d81"}

# ---------- Config ------------------------------------------------------------

def load_config():
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
    except Exception:
        config = {}

    # Check if ultimate_ip is missing or blank
    if not config.get("ultimate_ip"):
        env_ip = os.environ.get("C64_ULTIMATE_IP")
        if env_ip:
            config["ultimate_ip"] = env_ip

    return config
    
def save_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

# ---------- HTTP --------------------------------------------------------------

def get(path):
    url = BASE + path
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(body)
            sys.exit(f"API error {err.get('errorCode', e.code)}  ({url})")
        except Exception:
            sys.exit(f"HTTP {e.code}  ({url})")
    except urllib.error.URLError as e:
        sys.exit(f"Network error: {e.reason}")


def aql(query, offset=0, limit=50):
    qs = urllib.parse.urlencode({"query": query})
    return get(f"search/aql/{offset}/{limit}?{qs}")

_cols, _rows = 80, 25
PAGE_SIZE = 20
try:
    _cols, _rows = os.get_terminal_size()
    PAGE_SIZE = max(5, _rows - 7)
except Exception:
    pass

C64_TERMINAL = _cols <= 40

# ---------- Formatting --------------------------------------------------------

SEP_WIDTH = min(_cols, 62) if _cols <= 40 else 62

# ANSI colors -- empty strings if not a real terminal
if sys.stdout.isatty():
    _CYAN   = "\033[36m"
    _GREEN  = "\033[32m"
    _YELLOW = "\033[33m"
    _RESET  = "\033[0m"
else:
    _CYAN = _GREEN = _YELLOW = _RESET = ""


class ColoredHelpFormatter(argparse.HelpFormatter):
    """Argparse formatter with ANSI colors and terminal-width awareness."""
    def __init__(self, prog):
        super().__init__(prog, width=_cols, max_help_position=24)

    def start_section(self, heading):
        super().start_section(f"{_YELLOW}{heading}{_RESET}" if heading else heading)

    def _format_action(self, action):
        result = super()._format_action(action)
        # Color subcommand names cyan
        if action.option_strings:
            for opt in action.option_strings:
                result = result.replace(opt, f"{_GREEN}{opt}{_RESET}", 1)
        elif action.dest and action.dest != "==SUPPRESS==":
            result = result.replace(action.dest, f"{_CYAN}{action.dest}{_RESET}", 1)
        return result

def sep():
    print("-" * SEP_WIDTH)

def header(t):
    sep()
    print(f"  {t}")
    sep()

def field(label, value, width=16):
    if value not in (None, "", 0, 0.0):
        print(f"  {label:<{width}} {value}")

def cat_label(cat_id):
    for name, cid in CAT_IDS.items():
        if cid == cat_id:
            return f"{cat_id} ({name})"
    return str(cat_id)

def resolve_cat_id(val):
    """Resolve a --cat value to (cat_id, repo_type).
    Checks CAT_IDS first, then fetches full category list."""
    key = val.lower()
    if key in CAT_IDS:
        return CAT_IDS[key], key  # repo type same as key for known cats
    try:
        return int(val), None
    except ValueError:
        pass
    try:
        data = get("search/categories")
        if isinstance(data, list):
            for c in data:
                if (c.get("name","").lower() == key or
                    c.get("description","").lower() == key or
                    c.get("type","").lower() == key):
                    return c["id"], c.get("type", key)
    except Exception:
        pass
    return None, None

# ---------- Ultimate API ------------------------------------------------------

def ultimate_post(ip, path, data, params=None):
    qs  = ("?" + urllib.parse.urlencode(params)) if params else ""
    url = f"http://{ip}/v1/{path}{qs}"
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/octet-stream"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status

def ultimate_put(ip, path, params=None):
    qs  = ("?" + urllib.parse.urlencode(params)) if params else ""
    url = f"http://{ip}/v1/{path}{qs}"
    req = urllib.request.Request(url, method="PUT")
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status

def inject_keyboard(ip, text):
    """
    Inject text into the C64 keyboard buffer at $0277.
    Buffer max is 10 bytes. All chars sent as-is (uppercase ASCII = correct PETSCII).
    \r = Return (0x0D).
    If text is longer than 10 bytes, inject in chunks with a small delay.
    """
    import time
    petscii = []
    for ch in text:
        if ch in ("\r", "\n"):
            petscii.append(0x0D)
        else:
            petscii.append(ord(ch))

    chunk_size = 10
    for i in range(0, len(petscii), chunk_size):
        chunk     = petscii[i:i + chunk_size]
        data_hex  = "".join(f"{b:02X}" for b in chunk)
        count_hex = f"{len(chunk):02X}"
        ultimate_put(ip, "machine:writemem", {"address": "0277", "data": data_hex})
        ultimate_put(ip, "machine:writemem", {"address": "00C6", "data": count_hex})
        if i + chunk_size < len(petscii):
            time.sleep(1)

def wait_for_load(ip, timeout=90, stable_count=4, poll_interval=0.5):
    """
    Poll $2D/$2E until:
    1. Value changes away from the initial BASIC value (load has started)
    2. Value stabilises (same value N times in a row -- load is done)
    Returns True when stable, False if timeout reached.
    """
    import time

    # Read initial value (BASIC prompt state)
    initial_val = None
    try:
        url = f"http://{ip}/v1/machine:readmem?address=002D&length=2"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as r:
            initial_val = r.read()
    except Exception:
        pass

    last_val = initial_val
    stable   = 0
    waited   = 0
    loading  = False  # have we seen the value change yet?

    print("  Waiting for load to complete ...", end="", flush=True)
    while waited < timeout:
        try:
            url = f"http://{ip}/v1/machine:readmem?address=002D&length=2"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as r:
                val = r.read()

            if not loading:
                # Waiting for value to change from initial BASIC state
                if val != initial_val:
                    loading  = True
                    last_val = val
                    stable   = 1
            else:
                # Loading started -- wait for value to stabilise
                if val == last_val:
                    stable += 1
                    if stable >= stable_count:
                        print(f" done  ({val.hex()})")
                        return True
                else:
                    stable   = 1
                    last_val = val
        except Exception:
            pass
        time.sleep(poll_interval)
        waited += poll_interval

    print(" timed out")
    return False


def mount_and_run(ip, filename, data, drive="a"):
    """Upload and mount a disk image, reset, inject LOAD+RUN, wait for load to complete.
    Returns load detection time in seconds, or 0 if load detection failed."""
    import time
    ext    = "." + filename.lower().rsplit(".", 1)[-1]
    dtype  = DISK_TYPES.get(ext, "d64")
    params = {"type": dtype, "mode": "unlinked"}
    print(f"  Uploading and mounting {filename} ...", end=" ", flush=True)
    try:
        qs  = "?" + urllib.parse.urlencode(params)
        url = f"http://{ip}/v1/drives/{drive}:mount{qs}"
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/octet-stream"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read().decode("utf-8"))
        temp_path = resp.get("file", "")
        print(f"done  -> {temp_path}")
    except Exception as e:
        print(f"FAILED: {e}")
        return 0

    print(f"  Resetting machine ...", end=" ", flush=True)
    try:
        ultimate_put(ip, "machine:reset")
        print("done")
    except Exception as e:
        print(f"FAILED: {e}")
        return 0

    time.sleep(3)
    print('  Injecting LOAD"*",8,1 + RUN ...')
    inject_keyboard(ip, 'LOAD"*",8,1\rRUN\r')
    t = time.time()
    wait_for_load(ip)
    load_time = time.time() - t
    print(f"  Load detection took {load_time:.1f}s")
    return load_time


def mount_disk(ip, filename, data, drive="a"):
    """Mount a disk image only, no reset or autorun."""
    ext    = "." + filename.lower().rsplit(".", 1)[-1]
    dtype  = DISK_TYPES.get(ext, "d64")
    params = {"type": dtype, "mode": "unlinked"}
    print(f"  Mounting {filename} on drive {drive.upper()}: ...", end=" ", flush=True)
    try:
        status = ultimate_post(ip, f"drives/{drive}:mount", data, params)
        print(f"done  ({status})")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

def is_idun():
    """True if running on the Idun cartridge (local shell or SSH)."""
    return os.environ.get("IDUN_SYS_DIR") is not None



def run_on_ultimate(filename, data, ip):
    ext    = "." + filename.lower().rsplit(".", 1)[-1]
    runner = ULTIMATE_RUNNERS.get(ext)
    if runner:
        url = f"http://{ip}/v1/runners:{runner}"
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/octet-stream",
                     "X-Filename": filename}
        )
        print(f"  Sending {filename} to Ultimate at {ip} ...", end=" ", flush=True)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                print(f"done  ({r.status})")
        except urllib.error.HTTPError as e:
            print(f"FAILED: HTTP {e.code}")
        except urllib.error.URLError as e:
            print(f"FAILED: {e.reason}")
    elif ext in DISK_TYPES:
        mount_and_run(ip, filename, data)
    else:
        print(f"  Ultimate: no runner for {ext} files")

# ---------- File ops ----------------------------------------------------------

def fetch_file_data(item_id, cat, f):
    file_id = f.get("id")
    url     = BASE + f"search/bin/{urllib.parse.quote(str(item_id))}/{cat}/{file_id}"
    req     = urllib.request.Request(url, headers={"client-id": "assembly64_cli"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def slugify(name):
    """Convert a release name to a safe directory name."""
    import re
    name = name.lower().strip()
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[\s_]+', '-', name)
    name = re.sub(r'-+', '-', name).strip('-')
    return name or "release"


def prompt_download_dir(item_name, item_id, category=None, multi_file=False):
    """Ask user where to download. Returns target dir."""
    cfg        = load_config()
    folder     = slugify(item_name)
    demos_dir  = cfg.get("download_dir_demos", "")
    sids_dir   = cfg.get("download_dir_sids", "")

    # Pick the relevant configured dir based on category
    configured_dir = ""
    configured_label = ""
    if category in (18, 4) and sids_dir:
        configured_dir   = sids_dir
        configured_label = f"SIDs dir ({sids_dir})"
    elif category in (18, 4) and demos_dir:
        configured_dir   = demos_dir
        configured_label = f"Demos dir ({demos_dir})"
    elif demos_dir:
        configured_dir   = demos_dir
        configured_label = f"Demos dir ({demos_dir})"

    if configured_dir and multi_file:
        configured_label += f" -> {folder}/"

    # Build ordered options
    options = []
    if configured_dir:
        options.append(("configured", configured_label))
    options.append(("browse",  "Browse local filesystem"))
    options.append(("current", "Current directory"))
    options.append(("folder",  f"Create folder: {folder}/"))

    print(f"\n  Download to:")
    for i, (_, label) in enumerate(options, 1):
        print(f"  [{i}] {label}")

    # Show tip if dirs not configured
    if not demos_dir and not sids_dir:
        print()
        print("  ** assembly64 config --help to set dirs")

    print()
    choice = input("  Choose (or Enter for current directory): ").strip()

    try:
        n = int(choice) - 1
        key, _ = options[n]
    except (ValueError, IndexError):
        return "."

    if key == "configured":
        target = os.path.join(configured_dir, folder) if multi_file else configured_dir
        os.makedirs(target, exist_ok=True)
        if multi_file:
            print(f"  Using: {target}/")
        return target

    if key == "browse":
        target = browse_local_dir()
        if target is None:
            return "."
        return target

    if key == "current":
        return "."

    if key == "folder":
        os.makedirs(folder, exist_ok=True)
        print(f"  Created folder: {folder}/")
        return folder

    return "."


def browse_local_dir():
    """Browse local filesystem to pick a destination directory.
    Returns chosen path or None if cancelled."""
    path = os.getcwd()
    while True:
        entries = sorted(
            [e for e in os.listdir(path) if os.path.isdir(os.path.join(path, e))],
            key=str.lower
        )
        rows = [f"  {i:>3}. {e}/" for i, e in enumerate(entries, 1)]
        print()
        header(f"Local: {path}")
        print(f"  Enter=select this directory")
        idx = paginated_list(rows, "Number to descend", can_mkdir=True, can_modify=path != os.path.dirname(path), can_upload=False)
        if idx is None:
            return path
        if idx == "up":
            parent = os.path.dirname(path)
            if parent != path:
                path = parent
            continue
        if idx == "mkdir":
            dirname = input("  New directory name: ").strip()
            if dirname:
                new_path = os.path.join(path, dirname)
                os.makedirs(new_path, exist_ok=True)
                print(f"  Created: {new_path}/")
                path = new_path
            continue
        if idx in ("rename", "delete", "upload"):
            continue
        if 0 <= idx < len(entries):
            path = os.path.join(path, entries[idx])


def local_browse(remote_ip, remote_path, hostname):
    """Full local filesystem browser with upload capability.
    remote_path is the current remote directory to upload into."""
    import subprocess, shutil

    path = os.getcwd()

    while True:
        # Build listing
        try:
            raw = sorted(os.listdir(path), key=str.lower)
        except PermissionError:
            print(f"  Permission denied: {path}")
            path = os.path.dirname(path)
            continue

        dirs  = [(e, True,  0)                          for e in raw if os.path.isdir(os.path.join(path, e))]
        files = [(e, False, os.path.getsize(os.path.join(path, e)))
                 for e in raw if os.path.isfile(os.path.join(path, e))]
        all_entries = dirs + files

        rows = []
        for i, (name, is_dir, sz) in enumerate(all_entries, 1):
            if is_dir:
                rows.append(f"  {i:>3}. [DIR]  {name}/")
            else:
                rows.append(f"  {i:>3}. {name}  ({sz:,} bytes)")

        can_modify = path != os.path.dirname(path)
        header(f"Local: {path}")
        idx = paginated_list(rows, "Number to select",
                             can_mkdir=can_modify, can_modify=can_modify,
                             can_upload=False)

        if idx is None:
            return
        if idx == "up":
            parent = os.path.dirname(path)
            if parent != path:
                path = parent
            continue
        if idx == "mkdir":
            dirname = input("  New directory name: ").strip()
            if dirname:
                new_path = os.path.join(path, dirname)
                os.makedirs(new_path, exist_ok=True)
                print(f"  Created: {new_path}/")
            continue
        if idx == "rename":
            num = input("  Number to rename: ").strip()
            try:
                entry_name, _, _ = all_entries[int(num) - 1]
            except (ValueError, IndexError):
                print("  Invalid number.")
                continue
            new_name = input(f"  Rename '{entry_name}' to: ").strip()
            if new_name:
                os.rename(os.path.join(path, entry_name), os.path.join(path, new_name))
                print(f"  Renamed.")
            continue
        if idx == "delete":
            num = input("  Number to delete: ").strip()
            try:
                entry_name, entry_is_dir, _ = all_entries[int(num) - 1]
            except (ValueError, IndexError):
                print("  Invalid number.")
                continue
            full = os.path.join(path, entry_name)
            if entry_is_dir:
                contents = os.listdir(full)
                if contents:
                    print(f"  {entry_name}/ has {len(contents)} items.")
                    ans = input("  Delete recursively? [y/N]: ").strip().lower()
                    if ans == "y":
                        shutil.rmtree(full)
                        print("  Done.")
                    else:
                        print("  Cancelled.")
                else:
                    ans = input(f"  Delete {entry_name}/? [y/N]: ").strip().lower()
                    if ans == "y":
                        os.rmdir(full)
                        print("  Done.")
            else:
                ans = input(f"  Delete {entry_name}? [y/N]: ").strip().lower()
                if ans == "y":
                    os.unlink(full)
                    print("  Done.")
            continue

        # File or dir selected
        entry_name, entry_is_dir, entry_size = all_entries[idx]
        full_local = os.path.join(path, entry_name)

        if entry_is_dir:
            # Count for info panel
            file_count = sum(len(_fs) for _, _ds, _fs in os.walk(full_local))
            dir_count  = sum(len(_ds) for _, _ds, _fs in os.walk(full_local))
            total_size = sum(
                os.path.getsize(os.path.join(r, fn))
                for r, _, _fs in os.walk(full_local) for fn in _fs
            )
            mb = total_size / (1024 * 1024)
            if mb >= 1:
                size_str = f"~{mb:.1f} MB" if dir_count else f"{mb:.1f} MB"
            else:
                kb = total_size / 1024
                size_str = f"~{kb:.0f} KB" if dir_count else f"{kb:.0f} KB"

            print(f"\n  Selected: {entry_name}/")
            parts = []
            if dir_count:  parts.append(f"{dir_count} dirs")
            parts.append(f"{file_count} files")
            parts.append(size_str)
            print(f"  {', '.join(parts)}")
            print()
            print(f"  [1] Enter directory")
            print(f"  [2] Upload all to /{remote_path.strip('/')}/")
            print(f"  [3] Go back")
            print()
            ch = input("  Choose: ").strip()
            if ch == "2":
                # Warnings
                warns = []
                if dir_count:   warns.append("Has subdirs")
                if mb >= 50:    warns.append("Very large")
                if warns:
                    print(f"  ** {' - '.join(warns)}, true size may be larger")
                    ans = input("  Upload anyway? [y/N]: ").strip().lower()
                    if ans != "y":
                        continue
                uploads, err = get_upload_files(full_local)
                if err:
                    print(f"  {err}")
                    continue
                rbase = remote_path.strip("/")
                print(f"  Uploading {entry_name}/ -> /{rbase}/{entry_name}/ ...")
                ok = True
                for local_file, rel_path in uploads:
                    remote_file = f"{rbase}/{rel_path}" if rbase else rel_path
                    url = ftp_url(remote_ip, remote_file)
                    sz  = os.path.getsize(local_file)
                    print(f"    {rel_path} ...", end=" ", flush=True)
                    res = subprocess.run(["curl", "-s", "--ftp-create-dirs",
                                          "-T", local_file, url],
                                         capture_output=True, text=True)
                    if res.returncode == 0:
                        print(f"done ({sz:,} bytes)")
                    else:
                        print("FAILED")
                        ok = False
                print("  Done." if ok else "  Completed with errors.")
            elif ch == "1" or not ch:
                path = full_local
            continue

        # File selected
        ext = "." + entry_name.lower().rsplit(".", 1)[-1]
        print(f"\n  Selected: {entry_name}")
        options = []
        if ext in DISK_TYPES or ext in ULTIMATE_RUNNERS:
            options.append(("run",    "Run on Ultimate (sid player)" if ext == ".sid" else "Run on Ultimate"))
            if ext in DISK_TYPES:
                options.append(("mount", "Mount on drive A"))
        options.append(("upload", f"Upload to /{remote_path.strip('/')}/"))
        options.append(("back",   "Go back"))

        print()
        for i, (_, lbl) in enumerate(options, 1):
            print(f"  [{i}] {lbl}")
        print()
        ch = input("  Choose (or Enter to go back): ").strip()
        if not ch:
            continue
        try:
            key, _ = options[int(ch) - 1]
        except (ValueError, IndexError):
            continue

        if key == "back":
            continue
        elif key == "run":
            with open(full_local, "rb") as f:
                data = f.read()
            run_on_ultimate(entry_name, data, remote_ip)
        elif key == "mount":
            with open(full_local, "rb") as f:
                data = f.read()
            mount_disk(remote_ip, entry_name, data)
        elif key == "upload":
            rbase = remote_path.strip("/")
            remote_file = f"{rbase}/{entry_name}" if rbase else entry_name
            url  = ftp_url(remote_ip, remote_file)
            sz   = os.path.getsize(full_local)
            print(f"  Uploading {entry_name} ({sz:,} bytes) ...")
            res = subprocess.run(["curl", "-s", "--ftp-create-dirs",
                                  "-T", full_local, url],
                                 capture_output=True, text=True)
            if res.returncode == 0:
                print(f"  Done.")
            else:
                print(f"  FAILED: {res.stderr.strip() or 'unknown error'}")


def download_file(item_id, cat, f, run_ip=None, target_dir="."):
    file_id  = f.get("id")
    filename = f.get("path", f"file_{file_id}").replace("\\", "/").split("/")[-1]
    print(f"  Downloading {filename} ...", end=" ", flush=True)
    try:
        data = fetch_file_data(item_id, cat, f)
        print(f"done  ({len(data):,} bytes)")
        if run_ip:
            run_on_ultimate(filename, data, run_ip)
        else:
            filepath = os.path.join(target_dir, filename)
            with open(filepath, "wb") as out:
                out.write(data)
            print(f"  Saved  ->  {filepath}")
    except Exception as e:
        print(f"FAILED: {e}")

# ---------- Flip info ---------------------------------------------------------

def get_flipinfo(item_id, category):
    """Fetch flip disk info for a release. Returns ordered list of flipinfo entries or []."""
    data = get("metadata/flipinfo")
    if not isinstance(data, list):
        return []
    return [e for e in data
            if str(e.get("id","")) == str(item_id) and e.get("category") == category]


# ---------- Action prompt -----------------------------------------------------

def action_prompt(run_ip, flipinfo=None, can_back=False):
    """Ask user what to do. Returns ('run', ip), ('autodisk', ip), ('download',), 'back', or None."""
    cfg = load_config()
    saved_ip     = cfg.get("ultimate_ip", "")
    effective_ip = run_ip or saved_ip
    has_flip     = bool(flipinfo)

    options = []
    if effective_ip:
        options.append(("run",      f"Run on Ultimate ({effective_ip})"))
        if has_flip:
            options.append(("autodisk", f"Run with auto disk flip ({effective_ip})"))
    else:
        options.append(("run",      "Run on Ultimate (you'll be asked for IP)"))
        if has_flip:
            options.append(("autodisk", "Run with auto disk flip (you'll be asked for IP)"))
    options.append(("download", "Download"))
    if can_back:
        options.append(("refine",   "Refine query"))

    print()
    for i, (_, label) in enumerate(options, 1):
        print(f"  [{i}] {label}")
    if can_back:
        print(f"  b=back  q=quit")
    print()
    choice = input("  Choose action (or Enter to quit): ").strip().lower()
    if not choice or choice == "q":
        return None
    if choice == "b" and can_back:
        return "back"
    try:
        key, _ = options[int(choice) - 1]
        if key == "refine":
            return "refine"
        if key == "download":
            return ("download",)
        if key in ("run", "autodisk"):
            ip = effective_ip
            if not ip:
                ip = input("  Ultimate IP address (or Enter to download instead): ").strip()
                if not ip:
                    print("  No IP given -- downloading instead.")
                    return ("download",)
                save = input(f"  Save {ip} as default? [y/N]: ").strip().lower()
                if save == "y":
                    cfg["ultimate_ip"] = ip
                    save_config(cfg)
            return (key, ip)
    except (ValueError, IndexError):
        print("  Invalid choice.")
    return None

# ---------- Display -----------------------------------------------------------

def show_metadata(item):
    iid = item.get("id", "")
    cat = item.get("category", "")
    if not iid:
        return
    meta = get(f"metadata/{urllib.parse.quote(str(iid))}/{cat}")
    if not meta or not isinstance(meta, dict):
        return
    url      = meta.get("url") or ""
    site_img = meta.get("siteImage") or ""
    images   = meta.get("images") or []
    if url:
        field("CSDb URL:", url)
    if site_img:
        field("Screenshot:", site_img)
    elif images:
        first = images[0].get("path", "") if isinstance(images[0], dict) else ""
        if first:
            field("Screenshot:", first)



def run_autodisk(ip, disk_cache, flipinfo):
    """Mount and run disk 0, then auto-flip through remaining disks using flipinfo timings."""
    import time, threading
    cache_map = {fn.lower(): (fn, data) for fn, data in disk_cache}
    ordered   = []
    for entry in flipinfo:
        dn = entry.get("diskName", "").replace("\\", "/").split("/")[-1].lower()
        if dn in cache_map:
            ordered.append((cache_map[dn][0], cache_map[dn][1], entry.get("length", 0)))
    if not ordered:
        ordered = [(fn, data, 0) for fn, data in disk_cache]

    fn, data, duration = ordered[0]
    load_time = mount_and_run(ip, fn, data)
    if load_time == 0 and not isinstance(load_time, float):
        return

    import select, sys, termios

    # Flush any pending stdin input before starting countdown
    try:
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except Exception:
        pass

    def check_input():
        """Non-blocking stdin check.
        Returns 'quit' if user typed q, 'flip' if user pressed Enter, None otherwise."""
        if select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline().strip().lower()
            if line == "q":
                return "quit"
            return "flip"
        return None

    print("\n  Press Enter to flip immediately, q+Enter to stop.")

    # Each disk's 'duration' is how long IT plays before the next disk is needed.
    # So we count down disk[i]'s duration, then mount disk[i+1].
    for i in range(len(ordered) - 1):
        fn_next, data_next, _ = ordered[i + 1]
        _, _, duration        = ordered[i]

        if duration == 0:
            print(f"\n  No timing for disk {i+2} ({fn_next}) -- mounting now.")
            mount_disk(ip, fn_next, data_next)
            continue

        flipped = False
        for remaining in range(duration, 0, -1):
            m, s = divmod(remaining, 60)
            print(f"\r  Auto-flip: disk {i+2} ({fn_next}) in {m}m {s:02d}s ...", end="", flush=True)
            time.sleep(1)
            action = check_input()
            if action == "quit":
                print()
                print("  Auto-flip stopped.")
                return
            if action == "flip":
                flipped = True
                break

        print()
        if data_next:
            if flipped:
                print(f"  Manual flip to disk {i+2}: {fn_next}")
            else:
                print(f"  Auto-flip to disk {i+2}: {fn_next}")
            mount_disk(ip, fn_next, data_next)
            try:
                termios.tcflush(sys.stdin, termios.TCIFLUSH)
            except Exception:
                pass
        else:
            print(f"  Disk {i+2} data missing, skipping.")

    print("\n  All disks played.")


def write_flip_file(flipinfo, disk_filenames, target_dir=".", item_id=None):
    """Write a flip-info.txt file from API flipinfo data."""
    flip_filename = f"{item_id}-flip-info.txt" if item_id else "flip-info.txt"
    flip_path     = os.path.join(target_dir, flip_filename)

    # Check if any flip file already exists in target dir
    existing = find_flip_file(target_dir)
    if existing:
        answer = input(f"  Flip file {os.path.basename(existing)} already exists. Overwrite with API data? [y/N]: ").strip().lower()
        if answer != "y":
            return
    # Build a map from bare filename to duration
    flip_map = {}
    for entry in flipinfo:
        dn  = entry.get("diskName", "").replace("\\", "/").split("/")[-1]
        dur = entry.get("length", 0)
        flip_map[dn.lower()] = dur

    lines = []
    for fn in disk_filenames:
        dur = flip_map.get(fn.lower(), 0)
        if dur:
            lines.append(f"{fn};{dur}")
        else:
            lines.append(fn)

    try:
        with open(flip_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"  Saved  ->  {flip_path}")
    except Exception as e:
        print(f"  Warning: could not write flip file: {e}")


def handle_files(iid, cat, entries, run_ip, download, flipinfo=None, item_name=None, item_id=None, target_dir="."):
    """Handle file listing, download, or run for a set of entries."""
    disk_exts = set(DISK_TYPES.keys())
    disks     = [f for f in entries
                 if "." + f.get("path","").lower().rsplit(".",1)[-1] in disk_exts]

    if run_ip and len(disks) > 1:
        print(f"\n  Multi-disk release -- {len(disks)} disk image(s):")
        for i, f in enumerate(disks, 1):
            print(f"    {i}. {f.get('path','')}  ({f.get('size',0):,} bytes)")
        print()
        print("  Downloading all disks...", flush=True)
        disk_cache = []
        for f in disks:
            fn = f.get("path","").replace("\\","/").split("/")[-1]
            print(f"  Fetching {fn} ...", end=" ", flush=True)
            try:
                data = fetch_file_data(iid, cat, f)
                disk_cache.append((fn, data))
                print(f"done  ({len(data):,} bytes)")
            except Exception as e:
                print(f"FAILED: {e}")
                disk_cache.append((fn, None))

        if disk_cache and disk_cache[0][1]:
            if flipinfo:
                run_autodisk(run_ip, disk_cache, flipinfo)
            else:
                fn, data = disk_cache[0]
                if mount_and_run(run_ip, fn, data):
                    print()
                    print("  Press Enter when the demo asks for the next disk,")
                    print("  type a disk number to mount a specific one, or q to quit.")
                    disk_idx = 1
                    while disk_idx < len(disk_cache):
                        prompt = input(f"  [Enter=disk {disk_idx+1}, number, or q]: ").strip()
                        if prompt.lower() == "q":
                            break
                        if prompt.isdigit():
                            idx = int(prompt) - 1
                            if 0 <= idx < len(disk_cache):
                                disk_idx = idx
                            else:
                                print(f"  Invalid -- valid range 1-{len(disk_cache)}")
                                continue
                        fn, data = disk_cache[disk_idx]
                        if data:
                            mount_disk(run_ip, fn, data)
                        else:
                            print(f"  Disk {disk_idx+1} failed to download, skipping.")
                        disk_idx += 1
        return

    if len(entries) == 1:
        if not run_ip and target_dir == ".":
            target_dir = prompt_download_dir(item_name or "release", item_id, category=cat, multi_file=False)
        download_file(iid, cat, entries[0], run_ip=run_ip, target_dir=target_dir)
    else:
        if not run_ip and target_dir == ".":
            target_dir = prompt_download_dir(item_name or "release", item_id, category=cat, multi_file=True)
        print("\n  Files:")
        for i, f in enumerate(entries, 1):
            print(f"    {i:>3}. {f.get('path','')}  ({f.get('size',0):,} bytes)")
        print()
        action = "send to Ultimate" if run_ip else "download"
        choice = input(f"  Enter number to {action} (or Enter for all): ").strip()
        if choice:
            try:
                entries = [entries[int(choice) - 1]]
            except (ValueError, IndexError):
                print("  Invalid -- processing all.")
        for f in entries:
            download_file(iid, cat, f, run_ip=run_ip, target_dir=target_dir)
        # Write flip-info.txt if downloading all disks for a multi-disk release
        if not run_ip and flipinfo and len(disks) > 1 and not choice:
            disk_filenames = [f.get("path","").replace("\\","/").split("/")[-1]
                              for f in disks]
            write_flip_file(flipinfo, disk_filenames, target_dir=target_dir, item_id=item_id)


def show_item(item, run_ip=None, download=False, show_files=False, autodisk=False, can_back=False):
    name     = item.get("name", "-")
    iid      = item.get("id", "")
    group    = item.get("group") or ""
    handle   = item.get("handle") or ""
    year     = item.get("year") or ""
    released = item.get("released") or ""
    rating   = item.get("siteRating") or item.get("rating") or ""
    cat      = item.get("category", "")
    event    = item.get("event") or ""
    compo    = item.get("compo") or ""
    place    = item.get("place") or ""
    country  = item.get("country") or ""

    header(name)
    field("ID:",       iid)
    field("Category:", cat_label(cat) if isinstance(cat, int) else cat)
    field("Group:",    group)
    field("Handle:",   handle)
    field("Country:",  country)
    field("Year:",     str(year) if year else "")
    field("Released:", released)
    field("Rating:",   str(rating) if rating else "")
    field("Event:",    event)
    if compo:
        field("Compo:", f"{compo}  (place #{place})" if place else str(compo))

    show_metadata(item)
    sep()

    if not iid:
        return

    resp    = get(f"search/entries/{urllib.parse.quote(str(iid))}/{cat}")
    entries = resp.get("contentEntry", []) if isinstance(resp, dict) else []
    if not entries:
        return

    # Fetch flipinfo if this is a multi-disk release
    disk_exts = set(DISK_TYPES.keys())
    disks     = [f for f in entries
                 if "." + f.get("path","").lower().rsplit(".",1)[-1] in disk_exts]
    flipinfo  = get_flipinfo(iid, cat) if len(disks) > 1 else []
    if flipinfo:
        print(f"\n  Flip info available -- {len(flipinfo)} disks with auto-flip timings.")

    if show_files and not download and not run_ip:
        print("\n  Files:")
        for i, f in enumerate(entries, 1):
            print(f"    [{i}] {f.get('path','')}  ({f.get('size',0):,} bytes)")
        return

    if download:
        target_dir = prompt_download_dir(name, iid, category=cat, multi_file=len(entries) > 1) if len(entries) > 1 else "."
        handle_files(iid, cat, entries, run_ip=None, download=True, flipinfo=flipinfo,
                     item_name=name, item_id=iid, target_dir=target_dir)
        return

    if run_ip:
        fi = flipinfo if autodisk else None
        handle_files(iid, cat, entries, run_ip=run_ip, download=False, flipinfo=fi,
                     item_name=name, item_id=iid)
        return

    # Interactive action prompt
    print("\n  Files:")
    for i, f in enumerate(entries, 1):
        print(f"    {i:>3}. {f.get('path','')}  ({f.get('size',0):,} bytes)")

    action = action_prompt(run_ip=None, flipinfo=flipinfo, can_back=can_back)
    if action is None:
        return
    if action in ("back", "refine"):
        return action
    if action[0] in ("run", "autodisk"):
        ip = action[1]
        fi = flipinfo if action[0] == "autodisk" else None
        handle_files(iid, cat, entries, run_ip=ip, download=False, flipinfo=fi,
                     item_name=name, item_id=iid)
    elif action[0] == "download":
        target_dir = prompt_download_dir(name, iid, category=cat, multi_file=len(entries) > 1) if len(entries) > 1 else "."
        if len(entries) == 1:
            download_file(iid, cat, entries[0], target_dir=target_dir)
        else:
            choice = input("\n  Enter number to download (or Enter for all): ").strip()
            if choice:
                try:
                    entries = [entries[int(choice) - 1]]
                except (ValueError, IndexError):
                    print("  Invalid -- downloading all.")
            for f in entries:
                download_file(iid, cat, f, target_dir=target_dir)
            if flipinfo and len(disks) > 1 and not choice:
                disk_filenames = [f.get("path","").replace("\\","/").split("/")[-1]
                                  for f in disks]
                write_flip_file(flipinfo, disk_filenames, target_dir=target_dir, item_id=iid)

# ---------- List helpers ------------------------------------------------------


def read_input(prompt):
    """Read input, intercepting arrow keys as n/p shortcuts."""
    import sys, tty, termios
    sys.stdout.write(prompt)
    sys.stdout.flush()
    # Try raw mode to catch arrow keys
    try:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setraw(fd)
        chars = []
        while True:
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                # Escape sequence -- read two more chars
                seq = sys.stdin.read(2)
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
                sys.stdout.write("\n")
                if seq == "[C":   # right arrow
                    return "n"
                elif seq == "[D": # left arrow
                    return "p"
                elif seq == "[A": # up arrow
                    return "up"
                elif seq == "[B": # down arrow
                    return "n"
                else:
                    return ""
            elif ch in ("\r", "\n"):
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
                sys.stdout.write("\n")
                return "".join(chars).strip()
            elif ch in ("\x7f", "\x08"):  # backspace
                if chars:
                    chars.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif ch == "\x03":  # Ctrl-C
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
                sys.stdout.write("\n")
                raise KeyboardInterrupt
            else:
                chars.append(ch)
                sys.stdout.write(ch)
                sys.stdout.flush()
    except Exception:
        # Fallback to normal input if raw mode fails (e.g. piped input)
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except Exception:
            pass
        return input("").strip()


def paginated_list(rows, prompt, can_mkdir=False, can_modify=False, can_upload=False, can_back=False):
    """
    Display a paginated list. 40 char wide C64 screen layout.
    Returns index, None, "up", "mkdir", "rename", or "delete".
    """
    total  = len(rows)
    offset = 0
    while True:
        page_rows = rows[offset:offset + PAGE_SIZE]
        for line in page_rows:
            print(line)
        end = offset + len(page_rows)
        print()

        # Line 1: Showing X-Y of Z | navigation
        nav = []
        if can_modify:
            nav.append("^=up")
        if offset > 0:
            nav.append("p/<-=prev")
        if end < total:
            nav.append("n/->=next")
        nav_str = ("  " + "  ".join(nav)) if nav else ""
        print(f"  Showing {offset+1}-{end} of {total}  |{nav_str}")

        # Line 2: Number to select, actions q=quit:
        actions = []
        if can_modify:
            if can_mkdir:
                actions.append("m=mkdir")
            actions += ["r=rename", "d=delete"]
        if can_upload:
            actions.append("u=upload")
        if can_back:
            actions.append("b=back")
        actions.append("q=quit")
        actions_str = "  ".join(actions)
        choice = read_input(f"  Number to select,  {actions_str}: ").lower()

        if not choice or choice == "q":
            return None
        if choice == "b":
            return "back" if can_back else None
        if choice in ("^", "up") and can_modify:
            return "up"
        if choice == "m" and can_mkdir:
            return "mkdir"
        if choice == "r" and can_modify:
            return "rename"
        if choice == "d" and can_modify:
            return "delete"
        if choice == "u" and can_upload:
            return "upload"

        if choice == "p" or choice == "[D":
            offset = max(0, offset - PAGE_SIZE)
            continue
        if choice == "n":
            if end < total:
                offset += PAGE_SIZE
            continue
        try:
            idx = int(choice) - 1
            if 0 <= idx < total:
                return idx
            print(f"  Out of range (1-{total})")
        except ValueError:
            print("  Invalid")

def pick(items, run_ip=None, download=False, show_files=False, autodisk=False, can_back=False):
    print(f"\n  {len(items)} result(s):\n")
    rows = []
    for i, item in enumerate(items, 1):
        name     = item.get("name", "-")
        group    = item.get("group") or ""
        handle   = item.get("handle") or ""
        year     = item.get("year") or ""
        released = item.get("released") or ""
        cat      = cat_label(item.get("category", ""))
        credits  = group or handle
        date_str = released or (str(year) if year else "")
        extra    = "  ".join(filter(None, [credits, date_str, cat]))
        rows.append(f"  {i:>3}. {name}  [{extra}]")
    idx = paginated_list(rows, "Enter number to view details", can_back=can_back)
    if idx is None or idx in ("up", "mkdir", "rename", "delete", "upload"):
        return False
    if idx == "back":
        return "back"
    show_item(items[idx], run_ip=run_ip, download=download, show_files=show_files, autodisk=autodisk, can_back=can_back)
    return True


def pick_name(names, prompt="select", can_back=False):
    print(f"\n  {len(names)} match(es):\n")
    rows = [f"  {i:>3}. {n}" for i, n in enumerate(names, 1)]
    idx  = paginated_list(rows, f"Enter number to {prompt}", can_back=can_back)
    if idx is None or idx in ("up", "mkdir", "rename", "delete", "upload"):
        return None
    if idx == "back":
        return "back"
    return names[idx]

# ---------- AQL ---------------------------------------------------------------

def q_val(s):
    return f'"{s}"' if " " in s else s

def build_query(args):
    parts = []
    if hasattr(args, "name") and args.name:
        parts.append(f"name:{q_val(args.name)}")
    if hasattr(args, "group") and args.group:
        parts.append(f"group:{q_val(args.group)}")
    if hasattr(args, "handle") and args.handle:
        parts.append(f"handle:{q_val(args.handle)}")
    if hasattr(args, "repo") and args.repo:
        parts.append(f"repo:{args.repo}")
    if hasattr(args, "cat") and args.cat:
        _, repo_type = resolve_cat_id(args.cat)
        if repo_type:
            parts.append(f"repo:{repo_type}")
        else:
            parts.append(f"repo:{args.cat}")
    if hasattr(args, "date") and args.date:
        parts.append(f"date:{args.date}")
    if hasattr(args, "after") and args.after:
        parts.append(f"date:>{args.after}")
    if hasattr(args, "before") and args.before:
        parts.append(f"date:<{args.before}")
    if hasattr(args, "order") and args.order:
        parts.append(f"order:{args.order}")
    return " ".join(parts)


def cmd_search(args):
    run_ip   = getattr(args, "run", None)
    download = getattr(args, "download", False)
    has_kv   = any([args.group, args.handle, args.repo, args.cat,
                    args.date, args.after, args.before])

    # Name only (no filters) -- use fast name lookup endpoint
    if args.name and not has_kv:
        enc   = urllib.parse.quote(args.name.replace(" ", ""))
        cat   = resolve_cat_id(args.cat)[0] if args.cat else 1
        names = get(f"search/releases/{enc}/{cat}")
        if not isinstance(names, list) or not names:
            print("  No results.")
            return
        chosen = pick_name(names, "get details")
        if not chosen:
            return
        items = get(f"search/releasegroup/{urllib.parse.quote(chosen)}/{cat}")
        if not isinstance(items, list) or not items:
            print("  No details found.")
            return
        pick(items, run_ip=run_ip, download=download, show_files=args.files, autodisk=getattr(args, "autodisk", False))
        return

    # Name + filters, or filters only -- use AQL
    if not args.name and not has_kv:
        print("  Please provide at least one filter or a name to search.")
        return

    items = aql(build_query(args), limit=args.limit)
    if not items:
        print("  No results.")
        return
    pick(items, run_ip=run_ip, download=download, show_files=args.files, autodisk=getattr(args, "autodisk", False))


def cmd_sid(args):
    run_ip   = getattr(args, "run", None)
    download = getattr(args, "download", False)
    enc      = urllib.parse.quote(args.query)
    names    = get(f"search/releases/{enc}/18")
    if not isinstance(names, list) or not names:
        print("  No results.")
        return

    chosen = pick_name(names, "get details")
    if not chosen:
        return

    items = get(f"search/releasegroup/{urllib.parse.quote(chosen)}/18")
    if not isinstance(items, list) or not items:
        print("  No details found.")
        return

    if args.after:
        items = [r for r in items if r.get("released") and r["released"].replace("-","") > args.after]
    if args.before:
        items = [r for r in items if r.get("released") and r["released"].replace("-","") < args.before]
    if args.order == "asc":
        items.sort(key=lambda r: r.get("released") or "")
    elif args.order == "desc":
        items.sort(key=lambda r: r.get("released") or "", reverse=True)
    if not items:
        print("  No results after filtering.")
        return

    pick(items, run_ip=run_ip, download=download, show_files=args.files, autodisk=getattr(args, "autodisk", False))


def cmd_charts(args):
    run_ip   = getattr(args, "run", None)
    download = getattr(args, "download", False)
    data     = get("charts")
    if not isinstance(data, list) or not data:
        print("  No charts available.")
        return

    chart_names = [c.get("name", "") for c in data if c.get("name")]

    def show_chart(chart):
        items = chart.get("entries", [])
        header(f"CHART: {chart.get('name','')}")
        rows = []
        for i, item in enumerate(items, 1):
            name    = item.get("name", "-")
            group   = item.get("group") or ""
            handle  = item.get("handle") or ""
            year    = item.get("year") or ""
            rating  = item.get("siteRating") or item.get("rating") or ""
            credits = group or handle
            date_str = str(year) if year else ""
            extra   = "  ".join(filter(None, [credits, date_str]))
            rating_str = f"*{rating:.2f}" if isinstance(rating, float) else f"*{rating}"
            rows.append(f"  {i:>3}. {name}  [{extra}]  {rating_str}")
        idx = paginated_list(rows, "Enter number to view details")
        if idx is not None:
            show_item(items[idx], run_ip=run_ip, download=download)

    if args.name:
        chart = next((c for c in data if c.get("name","").lower() == args.name.lower()), None)
        if not chart:
            print(f"  Chart '{args.name}' not found.")
            print(f"  Available: {', '.join(chart_names)}")
            return
        show_chart(chart)
    else:
        header("AVAILABLE CHARTS")
        for i, name in enumerate(chart_names, 1):
            print(f"  {i:>3}. {name}")
        sep()
        print()
        choice = input("  Enter number to view chart (or Enter to quit): ").strip()
        if not choice:
            return
        try:
            chart = data[int(choice) - 1]
            show_chart(chart)
        except (ValueError, IndexError):
            print("  Invalid choice.")


def cmd_presets(args):
    data = get("search/aql/presets")
    if not isinstance(data, list) or not data:
        print("  No presets available.")
        return

    if args.name:
        preset = next((p for p in data if p.get("type","").lower() == args.name.lower()), None)
        if not preset:
            print(f"  Preset '{args.name}' not found.")
            print(f"  Available: {', '.join(p.get('type','') for p in data)}")
            return
        header(f"PRESET: {preset.get('type','')}")
        print(f"  {preset.get('description','')}")
        print()
        for v in preset.get("values", []):
            print(f"  {v.get('id'):>3}  {v.get('name','')}")
            if v.get("aqlKey"):
                print(f"       AQL: {v.get('aqlKey')}")
        sep()
    else:
        header("AQL PRESETS")
        for p in data:
            print(f"  {p.get('type',''):<20} {p.get('description','')}  ({len(p.get('values',[]))} entries)")
        sep()
        print(f"\n  Use:  assembly64 presets \"<type>\"")


class _JumpSubcat(Exception): pass
class _JumpCategory(Exception): pass
class _JumpAll(Exception): pass


def cmd_categories(args):
    run_ip   = getattr(args, "run", None)
    download = getattr(args, "download", False)
    data = get("search/categories")
    if not isinstance(data, list):
        print("  Could not fetch categories.")
        return

    by_type = {}
    for c in data:
        by_type.setdefault(c.get("type", "other"), []).append(c)
    type_names = sorted(by_type.keys())

    if getattr(args, "list", False):
        header("CATEGORY LIST")
        print(f"  All categories (repo:type in AQL):")
        sep()
        for t in type_names:
            cats = sorted(by_type[t], key=lambda x: x["id"])
            for c in cats:
                print(f"  id:{c['id']:<4} repo:{t:<15} {c['description']}")
        sep()
        return

    def cat_header(c):
        sep()
        print(f"  [{c['id']:>3}]  {c['description']}  ({c['name']})")
        sep()

    def show_filter_prompt(cat_name, cat_id, cat_name_short, query, multi_cat):
        sep()
        print(f"  [{cat_id:>3}]  {cat_name}  ({cat_name_short})")
        sep()
        print(f"  Query: {query}")
        print(f"  n=name  h=handle  g=group")
        print(f"  f=after  b=before  o=order  c=clear")
        if multi_cat:
            print(f"  Back to: s=subcategory  t=category  a=all")
        else:
            print(f"  Back to: t=category  a=all")
        print(f"  b=back  q=quit")

    def show_results_header(cat_name, cat_id, cat_name_short, query, offset, shown, has_more, multi_cat):
        sep()
        print(f"  [{cat_id:>3}]  {cat_name}  ({cat_name_short})")
        sep()
        print(f"  Query: {query}")
        if offset == 0 and has_more:
            print(f"  Found 50+ results")
        elif has_more:
            print(f"  Results {offset+1}-{shown}  (more available)")
        else:
            print(f"  Results {offset+1}-{shown}")
        print()

    # Top level: all categories
    while True:
        try:
            header("CATEGORIES")
            for i, t in enumerate(type_names, 1):
                print(f"  {i:>3}. {t}  ({len(by_type[t])} categories)")
            sep()
            choice = input("  Number to browse,  q=quit: ").strip().lower()
            if choice == "q":
                return
            if choice in ("s", "t", "a"):
                continue
            try:
                chosen_type = type_names[int(choice) - 1]
            except (ValueError, IndexError):
                print("  Invalid choice.")
                continue

            cats = sorted(by_type[chosen_type], key=lambda x: x["id"])
            multi_cat = len(cats) > 1

            # If only one category, go straight in
            if not multi_cat:
                chosen_cat = cats[0]
            else:
                chosen_cat = None

            # Category type list (only shown for multi-cat repos)
            while True:
                try:
                    if multi_cat and chosen_cat is None:
                        header(f"  {chosen_type}")
                        for i, c in enumerate(cats, 1):
                            print(f"  {i:>3}. [{c['id']:>3}]  {c['description']}  ({c['name']})")
                        sep()
                        choice2 = input("  Number to select,  b=back  a=all  q=quit: ").strip().lower()
                        if choice2 == "q":
                            return
                        if choice2 in ("b", "t", "a"):
                            break
                        if choice2 == "s":
                            continue
                        try:
                            idx = int(choice2) - 1
                            if not (0 <= idx < len(cats)):
                                print("  Invalid number.")
                                continue
                        except ValueError:
                            print("  Invalid input.")
                            continue
                        chosen_cat = cats[idx]

                    cat_name       = chosen_cat["description"]
                    cat_type       = chosen_cat["type"]
                    cat_name_short = chosen_cat["name"]
                    cat_id         = chosen_cat["id"]

                    filters = {}

                    def build_cat_query():
                        parts = [f"repo:{cat_type}"]
                        if cat_name_short in set(CATEGORIES.values()):
                            parts.append(f"category:{cat_name_short}")
                        for field, val in filters.items():
                            parts.append(f"{field}:{q_val(val)}")
                        return " ".join(parts)

                    # Subcategory filter loop
                    while True:
                        try:
                            q = build_cat_query()
                            show_filter_prompt(cat_name, cat_id, cat_name_short, q, multi_cat)
                            key = input("  Filter: ").strip().lower()

                            if key == "q":
                                return
                            elif key == "b":
                                if multi_cat:
                                    chosen_cat = None
                                break
                            elif key == "s" and multi_cat:
                                filters = {}
                                continue
                            elif key == "t":
                                raise _JumpCategory()
                            elif key == "a":
                                raise _JumpAll()
                            elif key == "c":
                                filters = {}
                            elif key == "n":
                                val = input("  Name: ").strip()
                                if val: filters["name"] = val
                            elif key == "h":
                                val = input("  Handle: ").strip()
                                if val: filters["handle"] = val
                            elif key == "g":
                                val = input("  Group: ").strip()
                                if val: filters["group"] = val
                            elif key == "f":
                                val = input("  After (YYYYMMDD): ").strip()
                                if val: filters["date:>"] = val
                            elif key == "o":
                                print("  [1] Rating (default)")
                                print("  [2] Newest first")
                                print("  [3] Oldest first")
                                oc = input("  Order: ").strip()
                                if oc == "1":   filters.pop("order", None)
                                elif oc == "2": filters["order"] = "date_desc"
                                elif oc == "3": filters["order"] = "date_asc"
                            elif key == "":
                                query  = build_cat_query()
                                offset = 0
                                limit  = 50

                                while True:
                                    try:
                                        print(f"  Searching ...", flush=True)
                                        items = aql(query, offset=offset, limit=limit)
                                        if not items:
                                            print("  No results." if offset == 0 else "  No more results.")
                                            break

                                        if "order" not in filters:
                                            items.sort(key=lambda x: float(x.get("siteRating") or x.get("rating") or 0), reverse=True)

                                        shown    = offset + len(items)
                                        has_more = len(items) == limit

                                        show_results_header(cat_name, cat_id, cat_name_short, query, offset, shown, has_more, multi_cat)

                                        options = [("view", "[1] View results")]
                                        if has_more:
                                            options.append(("next", f"[{len(options)+1}] Next {limit} ->"))
                                        if offset > 0:
                                            options.append(("prev", f"[{len(options)+1}] <- Prev {limit}"))
                                        options.append(("refine", f"[{len(options)+1}] Refine query"))
                                        for _, label in options:
                                            print(f"  {label}")
                                        if multi_cat:
                                            print(f"  Back to: s=subcategory  t=category  a=all")
                                        else:
                                            print(f"  Back to: t=category  a=all")
                                        print(f"  b=back  q=quit")
                                        print()
                                        ch = input("  Choose: ").strip().lower()

                                        if ch == "q":
                                            return
                                        elif ch == "b":
                                            break
                                        elif ch == "s" and multi_cat:
                                            raise _JumpSubcat()
                                        elif ch == "t":
                                            raise _JumpCategory()
                                        elif ch == "a":
                                            raise _JumpAll()
                                        else:
                                            try:
                                                n = int(ch) - 1
                                                key2, _ = options[n]
                                            except (ValueError, IndexError):
                                                continue
                                            if key2 == "view":
                                                pick(items, run_ip=run_ip, download=download, can_back=True)
                                            elif key2 == "next":
                                                offset += limit
                                            elif key2 == "prev":
                                                offset = max(0, offset - limit)
                                            elif key2 == "refine":
                                                break
                                    except (_JumpSubcat, _JumpCategory, _JumpAll):
                                        raise

                        except _JumpSubcat:
                            filters = {}
                            continue
                        except (_JumpCategory, _JumpAll):
                            raise

                    if not multi_cat:
                        break  # single-cat repo: b goes back to CATEGORIES

                except _JumpCategory:
                    chosen_cat = None
                    if not multi_cat:
                        raise _JumpAll()
                    break
                except _JumpAll:
                    raise

        except _JumpAll:
            continue


def parse_flip_file(path):
    """
    Parse a flip/swap file and return ordered list of (filename, duration_seconds).
    Supports:
      flip-info.txt  -- Assembly64: filename;seconds (last entry may have no duration)
      *.lst          -- Pi1541: one filename per line, no timing
      *.vfl          -- VICE fliplist: one filename per line
    """
    entries = []
    try:
        with open(path) as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
        for line in lines:
            if ";" in line:
                parts = line.split(";", 1)
                fname    = parts[0].strip()
                duration = int(parts[1].strip()) if parts[1].strip().isdigit() else 0
            else:
                fname    = line.strip()
                duration = 0
            if fname:
                entries.append((fname, duration))
    except Exception as e:
        print(f"  Warning: could not parse flip file {path}: {e}")
    return entries


def find_flip_file(directory):
    """Look for a flip/swap file in the given directory.
    Priority: numbered *-flip-info.txt > plain flip-info.txt > .lst > .vfl"""
    numbered  = []
    plain     = []
    others    = []
    for f in os.listdir(directory):
        fl = f.lower()
        fp = os.path.join(directory, f)
        if fl.endswith("-flip-info.txt") or fl.endswith("_flip_info.txt"):
            # Numbered ones (e.g. 72550-flip-info.txt) -- highest priority
            numbered.append(fp)
        elif fl in ("flip-info.txt", "flipinfo.txt", "flip_info.txt"):
            plain.append(fp)
        elif fl.endswith(".lst") or fl.endswith(".vfl"):
            others.append(fp)
    all_found = numbered + plain + others
    if not all_found:
        return None
    if len(all_found) > 1:
        print(f"  Warning: multiple flip files found:")
        for fp in all_found:
            print(f"    {os.path.basename(fp)}")
        print(f"  Using: {os.path.basename(all_found[0])}")
    return all_found[0]


def cmd_run(args):
    cfg = load_config()
    ip  = args.ip or cfg.get("ultimate_ip", "")
    if not ip:
        ip = input("  Ultimate IP address: ").strip()
        if not ip:
            print("  No IP given.")
            return

    # If --remote, delegate to rrun logic
    if getattr(args, "remote", False):
        args.ip = ip
        cmd_rrun(args)
        return

    path = args.path
    disk_exts = set(DISK_TYPES.keys())
    all_exts  = disk_exts | set(ULTIMATE_RUNNERS.keys())

    # Single file
    if os.path.isfile(path):
        ext = "." + path.lower().rsplit(".", 1)[-1]
        if ext not in all_exts:
            print(f"  Unsupported file type: {ext}")
            return
        print(f"  Reading {path} ...", end=" ", flush=True)
        with open(path, "rb") as f:
            data = f.read()
        print(f"done  ({len(data):,} bytes)")
        filename = os.path.basename(path)
        run_on_ultimate(filename, data, ip)
        return

    # Directory
    if os.path.isdir(path):
        # Find all disk images
        files = sorted(os.listdir(path))
        disks = [(f, os.path.join(path, f)) for f in files
                 if "." + f.lower().rsplit(".", 1)[-1] in disk_exts]
        prgs  = [(f, os.path.join(path, f)) for f in files
                 if "." + f.lower().rsplit(".", 1)[-1] in ULTIMATE_RUNNERS]

        if not disks and not prgs:
            print(f"  No supported files found in {path}")
            return

        # Single PRG/SID/CRT -- just run it
        if not disks and len(prgs) == 1:
            fn, fp = prgs[0]
            with open(fp, "rb") as f:
                data = f.read()
            run_on_ultimate(fn, data, ip)
            return

        # Single disk -- just run it
        if len(disks) == 1:
            fn, fp = disks[0]
            with open(fp, "rb") as f:
                data = f.read()
            run_on_ultimate(fn, data, ip)
            return

        # Multiple disks -- check for flip file
        flip_path = find_flip_file(path)
        if flip_path:
            print(f"  Found flip file: {os.path.basename(flip_path)}")
            flip_entries = parse_flip_file(flip_path)
            if flip_entries:
                print(f"  Loading {len(flip_entries)} disks in flip order...")
                disk_cache = []
                for fn, duration in flip_entries:
                    fp = os.path.join(path, fn)
                    if os.path.isfile(fp):
                        with open(fp, "rb") as f:
                            data = f.read()
                        disk_cache.append((fn, data))
                        print(f"    {fn}  ({len(data):,} bytes)  [{duration}s]")
                    else:
                        print(f"    {fn}  NOT FOUND -- skipping")

                # Build flipinfo-like structure from flip file
                flipinfo = [{"diskName": fn, "length": dur}
                            for fn, dur in flip_entries]
                # Re-pair with loaded data
                cache_with_flip = [(fn, data) for fn, data in disk_cache]
                run_autodisk(ip, cache_with_flip, flipinfo)
                return

        # Multiple disks, no flip file -- load all and prompt
        print(f"  {len(disks)} disk image(s) found, no flip file -- manual swap mode")
        disk_cache = []
        for fn, fp in disks:
            with open(fp, "rb") as f:
                data = f.read()
            disk_cache.append((fn, data))
            print(f"    {fn}  ({len(data):,} bytes)")

        fn, data = disk_cache[0]
        if mount_and_run(ip, fn, data):
            print()
            print("  Press Enter when the demo asks for the next disk,")
            print("  type a disk number to mount a specific one, or q to quit.")
            disk_idx = 1
            while disk_idx < len(disk_cache):
                prompt = input(f"  [Enter=disk {disk_idx+1}, number, or q]: ").strip()
                if prompt.lower() == "q":
                    break
                if prompt.isdigit():
                    idx = int(prompt) - 1
                    if 0 <= idx < len(disk_cache):
                        disk_idx = idx
                    else:
                        print(f"  Invalid -- valid range 1-{len(disk_cache)}")
                        continue
                fn, data = disk_cache[disk_idx]
                mount_disk(ip, fn, data)
                disk_idx += 1
        return

    print(f"  Not found: {path}")


def cmd_rmount(args):
    """Mount a file already on the Ultimate filesystem on drive A."""
    cfg = load_config()
    ip  = args.ip or cfg.get("ultimate_ip", "")
    if not ip:
        ip = input("  Ultimate IP address: ").strip()
        if not ip:
            print("  No IP given.")
            return
    path = "/" + args.path.lstrip("/")
    print(f"  Mounting {path} on drive A: ...", end=" ", flush=True)
    try:
        status = ultimate_put(ip, "drives/a:mount", {"image": path, "mode": "unlinked"})
        print(f"done  ({status})")
    except Exception as e:
        print(f"FAILED: {e}")


def cmd_mount(args):
    """Mount a local or remote disk image on drive A (no reset or autorun)."""
    cfg = load_config()
    ip  = args.ip or cfg.get("ultimate_ip", "")
    if not ip:
        ip = input("  Ultimate IP address: ").strip()
        if not ip:
            print("  No IP given.")
            return

    if getattr(args, "remote", False):
        path = "/" + args.path.lstrip("/")
        print(f"  Mounting {path} on drive A: ...", end=" ", flush=True)
        try:
            status = ultimate_put(ip, "drives/a:mount", {"image": path, "mode": "unlinked"})
            print(f"done  ({status})")
        except Exception as e:
            print(f"FAILED: {e}")
        return

    path = args.path
    if not os.path.isfile(path):
        print(f"  File not found: {path}")
        return
    ext = "." + path.lower().rsplit(".", 1)[-1]
    if ext not in DISK_TYPES:
        print(f"  Unsupported disk type: {ext}")
        print(f"  Supported: {', '.join(DISK_TYPES)}")
        return
    print(f"  Reading {path} ...", end=" ", flush=True)
    with open(path, "rb") as f:
        data = f.read()
    print(f"done  ({len(data):,} bytes)")
    mount_disk(ip, os.path.basename(path), data)


def cmd_rrun(args):
    """Run a file already on the Ultimate's filesystem."""
    import time
    cfg = load_config()
    ip  = args.ip or cfg.get("ultimate_ip", "")
    if not ip:
        ip = input("  Ultimate IP address: ").strip()
        if not ip:
            print("  No IP given.")
            return

    path = "/" + args.path.lstrip("/")
    ext  = "." + path.lower().rsplit(".", 1)[-1]

    if ext in ULTIMATE_RUNNERS:
        # PRG/CRT/SID -- use run_prg/run_crt/sidplay with file= param
        runner = ULTIMATE_RUNNERS[ext]
        print(f"  Running {path} on Ultimate ...", end=" ", flush=True)
        try:
            status = ultimate_put(ip, f"runners:{runner}", {"file": path})
            print(f"done  ({status})")
        except Exception as e:
            print(f"FAILED: {e}")

    elif ext in DISK_TYPES:
        # D64 -- mount by path then reset + keyboard inject
        print(f"  Mounting {path} ...", end=" ", flush=True)
        try:
            status = ultimate_put(ip, "drives/a:mount", {"image": path, "mode": "unlinked"})
            print(f"done  ({status})")
        except Exception as e:
            print(f"FAILED: {e}")
            return
        print(f"  Resetting machine ...", end=" ", flush=True)
        try:
            ultimate_put(ip, "machine:reset")
            print("done")
        except Exception as e:
            print(f"FAILED: {e}")
            return
        time.sleep(3)
        print('  Injecting LOAD"*",8,1 + RUN ...')
        inject_keyboard(ip, 'LOAD"*",8,1\rRUN\r')
    else:
        print(f"  Unsupported file type: {ext}")
        print(f"  Supported: {', '.join(list(ULTIMATE_RUNNERS) + list(DISK_TYPES))}")


def ftp_base(ip):
    return f"ftp://{ip}"


def ftp_url(ip, path):
    """Build an FTP URL with spaces in path components properly encoded."""
    encoded = "/".join(urllib.parse.quote(p, safe="") for p in path.split("/"))
    return f"ftp://{ip}/{encoded}"


def cmd_pull(args):
    """Download a file from the Ultimate."""
    import subprocess, fnmatch
    cfg = load_config()
    ip  = args.ip or cfg.get("ultimate_ip", "")
    if not ip:
        ip = input("  Ultimate IP address: ").strip()
        if not ip:
            print("  No IP given.")
            return

    remote = args.remote.lstrip("/")

    # If wildcard or no extension (treat as prefix), resolve via directory listing
    last = remote.split("/")[-1]
    if "*" in remote or "?" in remote or ("." not in last and last):
        if "*" in remote or "?" in remote:
            print("  Tip: on zsh, quote wildcards to avoid shell expansion: \"GH*\"")
        parent  = "/".join(remote.split("/")[:-1])
        pattern = last.lower() + ("" if "*" in last or "?" in last else "*")
        list_url = ftp_url(ip, parent + "/") if parent else ftp_url(ip, "")
        res = subprocess.run(["curl", "-s", list_url], capture_output=True, text=True)
        matches = []
        for line in res.stdout.strip().splitlines():
            parts = line.split(None, 8)
            if len(parts) >= 9:
                name = parts[8]
                if fnmatch.fnmatch(name.lower(), pattern):
                    matches.append(name)
        if not matches:
            print(f"  No files matching {remote}")
            return
        if len(matches) > 1:
            print(f"  {len(matches)} files match:")
            for m in matches:
                print(f"    {m}")
            ans = input(f"  Download all {len(matches)} files? [y/N]: ").strip().lower()
            if ans != "y":
                return
            for m in matches:
                r = f"{parent}/{m}" if parent else m
                local = args.local or m
                url   = ftp_url(ip, r)
                print(f"  Pulling {r} -> {m} ...")
                result = subprocess.run(["curl", "-s", "-o", m, url], capture_output=True, text=True)
                if result.returncode == 0 and os.path.exists(m):
                    print(f"  Saved  ->  {m}  ({os.path.getsize(m):,} bytes)")
                else:
                    print(f"  FAILED: {result.stderr.strip() or 'unknown error'}")
            return
        remote = f"{parent}/{matches[0]}" if parent else matches[0]
        print(f"  Resolved: {remote}")

    local = args.local or remote.split("/")[-1]
    url   = ftp_url(ip, remote)

    print(f"  Pulling {remote} -> {local} ...")
    result = subprocess.run(["curl", "-s", "-o", local, url], capture_output=True, text=True)
    if result.returncode == 0 and os.path.exists(local):
        size = os.path.getsize(local)
        print(f"  Saved  ->  {local}  ({size:,} bytes)")
    else:
        print(f"  FAILED: {result.stderr.strip() or 'unknown error'}")


def cmd_push(args):
    """Upload a local file to the Ultimate."""
    import subprocess, glob
    cfg = load_config()
    ip  = args.ip or cfg.get("ultimate_ip", "")
    if not ip:
        ip = input("  Ultimate IP address: ").strip()
        if not ip:
            print("  No IP given.")
            return

    local_arg = args.local
    local_files = [f for f in glob.glob(local_arg) if os.path.isfile(f)] \
                  if ("*" in local_arg or "?" in local_arg) else [local_arg]

    if not local_files:
        print(f"  No files matching: {local_arg}")
        return

    if len(local_files) > 1:
        print(f"  {len(local_files)} files match:")
        for f in local_files:
            print(f"    {f}  ({os.path.getsize(f):,} bytes)")
        ans = input(f"  Push all {len(local_files)} files? [y/N]: ").strip().lower()
        if ans != "y":
            return

    # If no remote given, browse to pick destination
    if not args.remote:
        info = None
        try:
            req  = urllib.request.Request(f"http://{ip}/v1/info")
            with urllib.request.urlopen(req, timeout=5) as r:
                info = json.loads(r.read().decode("utf-8"))
        except Exception:
            pass
        hostname = info.get("hostname", ip) if info else ip
        print(f"  Browse to destination (Enter=select current dir, q=cancel):")

        # Suggest folder name from first local file (without extension)
        suggested = os.path.splitext(os.path.basename(local_files[0]))[0] if local_files else None

        while True:
            remote_dir = ls_browse_pick_dir(ip, hostname, suggested_name=suggested)
            if remote_dir is None:
                print("  Cancelled.")
                return

            for local in local_files:
                if not os.path.isfile(local):
                    print(f"  File not found: {local}")
                    continue
                filename = os.path.basename(local)
                remote   = f"{remote_dir}/{filename}" if remote_dir else filename
                remote   = remote.lstrip("/")
                url      = ftp_url(ip, remote)
                size = os.path.getsize(local)
                print(f"  Pushing {local} ({size:,} bytes) -> /{remote} ...")
                result = subprocess.run(["curl", "-s", "-T", local, url],
                                        capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"  Done.")
                else:
                    print(f"  FAILED: {result.stderr.strip() or 'unknown error'}")

            # Drop into full ls browser at the destination
            ls_browse(ip, hostname, remote_dir + "/", run_ip=ip, suggested_name=suggested)
            return

    for local in local_files:
        if not os.path.isfile(local):
            print(f"  File not found: {local}")
            continue
        filename = os.path.basename(local)
        remote   = f"{remote_dir}/{filename}" if remote_dir else filename
        remote   = remote.lstrip("/")
        url      = ftp_url(ip, remote)
        size = os.path.getsize(local)
        print(f"  Pushing {local} ({size:,} bytes) -> /{remote} ...")
        result = subprocess.run(["curl", "-s", "-T", local, url], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  Done.")
        else:
            print(f"  FAILED: {result.stderr.strip() or 'unknown error'}")


def ls_browse_pick_dir(ip, hostname, suggested_name=None):
    """Browse the Ultimate filesystem directories.
    Returns chosen directory path string, or None if cancelled.
    Enter with no number = select current directory.
    q at root = cancel.
    """
    import subprocess
    path = "/"

    while True:
        had_trailing = path.endswith("/")
        path = "/".join(p for p in path.split("/") if p)
        if had_trailing and path:
            path += "/"
        list_path = path.rstrip("/")

        all_entries = ls_list(ip, list_path) or []
        dirs  = [(n, d, s) for n, d, s in all_entries if d]
        files = [(n, d, s) for n, d, s in all_entries if not d]

        rows = []
        for i, (n, d, s) in enumerate(dirs, 1):
            rows.append(f"  {i:>3}. [DIR]  {n}/")

        display_path = f"/{list_path}/" if list_path else "/"
        header(f"{hostname}: {display_path}")
        print(f"  Enter=upload here")

        can_modify = bool(list_path)
        idx = paginated_list(rows, "Number to descend", can_mkdir=can_modify, can_modify=can_modify, can_upload=False)

        if idx is None:
            # Enter = select current directory
            return list_path

        if idx == "up":
            if not list_path:
                return None  # q at root = cancel
            list_path = "/".join(list_path.split("/")[:-1])
            path = list_path + "/" if list_path else "/"
            continue

        if idx == "mkdir":
            if suggested_name and not any(n == suggested_name and d for n, d, _ in all_entries):
                print(f"  [1] {suggested_name}/")
                print(f"  [2] Enter name manually")
                mk_choice = input("  Choose (or Enter for suggestion): ").strip()
                if mk_choice == "2":
                    dirname = input("  New directory name: ").strip()
                else:
                    dirname = suggested_name
            else:
                dirname = input("  New directory name: ").strip()
            if dirname:
                if any(n == dirname and d for n, d, _ in all_entries):
                    print(f"  Already exists: {dirname}/")
                else:
                    new_path = f"{list_path}/{dirname}" if list_path else dirname
                    url = ftp_url(ip, new_path + "/")
                    res = subprocess.run(["curl", "-s", "--ftp-create-dirs", url],
                                         capture_output=True, text=True)
                    if res.returncode == 0:
                        print(f"  Created: /{new_path}/")
                        path = new_path + "/"
                    else:
                        print(f"  FAILED: {res.stderr.strip() or 'unknown error'}")
            continue

        if idx == "rename":
            num = input("  Number to rename: ").strip()
            try:
                entry_name, _, _ = dirs[int(num) - 1]
            except (ValueError, IndexError):
                print("  Invalid number.")
                continue
            new_name = input(f"  Rename '{entry_name}' to: ").strip()
            if new_name:
                old_path = f"{list_path}/{entry_name}" if list_path else entry_name
                new_path = f"{list_path}/{new_name}" if list_path else new_name
                ok, err = ftp_rename(ip, old_path, new_path)
                print("  Done." if ok else f"  FAILED: {err or 'unknown error'}")
            continue

        if idx == "delete":
            num = input("  Number to delete: ").strip()
            try:
                entry_name, entry_is_dir, _ = dirs[int(num) - 1]
            except (ValueError, IndexError):
                print("  Invalid number.")
                continue
            del_path = f"{list_path}/{entry_name}" if list_path else entry_name
            contents = ls_list(ip, del_path) or []
            if contents:
                print(f"  /{del_path}/ is not empty ({len(contents)} items).")
                ans = input(f"  Delete recursively? [y/N]: ").strip().lower()
                if ans == "y":
                    ok, err = ftp_delete_recursive(ip, del_path)
                    print("  Done." if ok else f"  FAILED: {err or 'unknown error'}")
            else:
                ans = input(f"  Delete /{del_path}/? [y/N]: ").strip().lower()
                if ans == "y":
                    ok, err = ftp_delete(ip, del_path, is_dir=True)
                    print("  Done." if ok else f"  FAILED: {err or 'unknown error'}")
            continue

        # Navigate into selected directory
        name, _, _ = dirs[idx]
        base = list_path.rstrip("/")
        path = f"{base}/{name}/" if base else f"{name}/"

def ls_list(ip, remote):
    """Fetch and parse an FTP directory listing. Returns list of (name, is_dir, size).
    Returns None if the path doesn't exist or can't be listed."""
    import subprocess
    url    = ftp_url(ip, remote if remote.endswith("/") else remote + "/")
    result = subprocess.run(["curl", "-s", url], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    entries = []
    for line in result.stdout.strip().splitlines():
        parts = line.split(None, 8)
        if len(parts) >= 9:
            is_dir = parts[0].startswith("d")
            size   = int(parts[4]) if not is_dir and parts[4].isdigit() else 0
            name   = parts[8]
            entries.append((name, is_dir, size))
    return entries


def get_upload_files(local_path):
    """Given a local path (file or dir), return (uploads, error).
    uploads is a list of (local_file, relative_remote_path)."""
    local_path = os.path.expanduser(local_path.strip())
    if not os.path.exists(local_path):
        return None, f"Not found: {local_path}"
    uploads = []
    if os.path.isfile(local_path):
        uploads.append((local_path, os.path.basename(local_path)))
    elif os.path.isdir(local_path):
        for root, dirs, files in os.walk(local_path):
            dirs.sort()
            for fname in sorted(files):
                full = os.path.join(root, fname)
                rel  = os.path.relpath(full, os.path.dirname(local_path))
                uploads.append((full, rel))
    return uploads, None



def ls_browse(ip, hostname, start_path, run_ip=None, suggested_name=None):
    """Interactive FTP browser."""
    import fnmatch, subprocess
    path = start_path.lstrip("/")

    while True:
        # Normalize path -- collapse double slashes, preserve trailing slash
        had_trailing = path.endswith("/")
        path = "/".join(p for p in path.split("/") if p)
        if had_trailing and path:
            path += "/"
        pattern   = None
        list_path = path.rstrip("/")  # use without trailing slash for path construction

        if path and not path.endswith("/"):
            entries = ls_list(ip, path)
            if entries is None or (entries == [] and not path.endswith("/")):
                # Not a directory -- treat last component as prefix filter
                parent  = "/".join(path.split("/")[:-1])
                prefix  = path.split("/")[-1].lower()
                pattern = prefix + "*"
                list_path = parent
                entries = ls_list(ip, list_path) or []
                entries = [(n, d, s) for n, d, s in entries
                           if fnmatch.fnmatch(n.lower(), pattern)]
        else:
            entries = ls_list(ip, list_path) or []

        if entries is None:
            print(f"  Not found: /{list_path}")
            return

        if not entries:
            print(f"  (empty directory)")
            # Still show the prompt so user can go up or mkdir
            display_path = f"/{list_path}/" if list_path else "/"
            header(f"{hostname}: {display_path}")
            print(f"  (empty)")
            idx = paginated_list([], "Number to select", can_mkdir=bool(list_path), can_modify=bool(list_path), can_upload=True)
            if idx is None:
                return
            if idx == "up":
                list_path = "/".join(list_path.rstrip("/").split("/")[:-1])
                path = list_path + "/" if list_path else ""
            elif idx == "mkdir":
                if suggested_name:
                    print(f"  [1] {suggested_name}/")
                    print(f"  [2] Enter name manually")
                    mk_choice = input("  Choose (or Enter for suggestion): ").strip()
                    dirname = suggested_name if mk_choice != "2" else input("  New directory name: ").strip()
                else:
                    dirname = input("  New directory name: ").strip()
                if dirname:
                    new_path = f"{list_path}/{dirname}" if list_path else dirname
                    url = ftp_url(ip, new_path + "/")
                    res = subprocess.run(["curl", "-s", "--ftp-create-dirs", url],
                                         capture_output=True, text=True)
                    print(f"  Created: /{new_path}/" if res.returncode == 0 else f"  FAILED")
            continue

        dirs  = [(n, d, s) for n, d, s in entries if d]
        files = [(n, d, s) for n, d, s in entries if not d]
        all_entries = dirs + files

        rows = []
        for i, (n, is_dir, size) in enumerate(all_entries, 1):
            if is_dir:
                rows.append(f"  {i:>3}. [DIR]  {n}/")
            else:
                rows.append(f"  {i:>3}. {n}  ({size:,} bytes)" if size else f"  {i:>3}. {n}")

        label = f" (filter: {pattern.rstrip('*')})" if pattern else ""
        display_path = f"/{list_path}/" if list_path else "/"
        header(f"{hostname}: {display_path}{label}")
        can_mkdir  = bool(list_path)
        can_modify = bool(list_path)
        idx = paginated_list(rows, "Number to select", can_mkdir=can_mkdir, can_modify=can_modify, can_upload=True)
        if idx is None:
            return
        if idx == "mkdir":
            if suggested_name and not any(n == suggested_name and d for n, d, _ in all_entries):
                print(f"  [1] {suggested_name}/")
                print(f"  [2] Enter name manually")
                mk_choice = input("  Choose (or Enter for suggestion): ").strip()
                if mk_choice == "2":
                    dirname = input("  New directory name: ").strip()
                else:
                    dirname = suggested_name
            else:
                dirname = input("  New directory name: ").strip()
            if dirname:
                # Check if already exists
                if any(n == dirname and d for n, d, _ in all_entries):
                    print(f"  Already exists: {dirname}/")
                else:
                    new_path = f"{list_path}/{dirname}" if list_path else dirname
                    url = ftp_url(ip, new_path + "/")
                    res = subprocess.run(["curl", "-s", "--ftp-create-dirs", url],
                                         capture_output=True, text=True)
                    if res.returncode == 0:
                        print(f"  Created: /{new_path}/")
                    else:
                        print(f"  FAILED: {res.stderr.strip() or 'unknown error'}")
            continue
        if idx == "rename":
            num = input("  Number to rename: ").strip()
            try:
                entry_name, entry_is_dir, _ = all_entries[int(num) - 1]
            except (ValueError, IndexError):
                print("  Invalid number.")
                continue
            new_name = input(f"  Rename '{entry_name}' to: ").strip()
            if new_name:
                old_path = f"{list_path}/{entry_name}" if list_path else entry_name
                new_path = f"{list_path}/{new_name}" if list_path else new_name
                ok, err = ftp_rename(ip, old_path, new_path)
                print("  Done." if ok else f"  FAILED: {err or 'unknown error'}")
            continue
        if idx == "delete":
            num = input("  Number to delete: ").strip()
            try:
                entry_name, entry_is_dir, _ = all_entries[int(num) - 1]
            except (ValueError, IndexError):
                print("  Invalid number.")
                continue
            del_path = f"{list_path}/{entry_name}" if list_path else entry_name
            label = f"/{del_path}/" if entry_is_dir else f"/{del_path}"
            if entry_is_dir:
                contents = ls_list(ip, del_path) or []
                if contents:
                    print(f"  {label} is not empty ({len(contents)} items).")
                    ans = input(f"  Delete recursively? [y/N]: ").strip().lower()
                    if ans == "y":
                        ok, err = ftp_delete_recursive(ip, del_path)
                        print("  Done." if ok else f"  FAILED: {err or 'unknown error'}")
                    else:
                        print("  Cancelled.")
                    continue
            ans = input(f"  Delete {label}? [y/N]: ").strip().lower()
            if ans == "y":
                ok, err = ftp_delete(ip, del_path, is_dir=entry_is_dir)
                print("  Done." if ok else f"  FAILED: {err or 'unknown error'}")
            else:
                print("  Cancelled.")
            continue
        if idx == "upload":
            print()
            print("  Upload:")
            print("  [1] Enter local path")
            print("  [2] Browse local filesystem")
            print()
            uc = input("  Choose: ").strip()
            if uc == "2":
                local_browse(ip, list_path or "/", hostname)
                continue
            else:
                local_path = input("  Local path: ").strip()
                if not local_path:
                    continue
                local_path = os.path.expanduser(local_path)

            uploads, err = get_upload_files(local_path)
            if err:
                print(f"  {err}")
                continue

            import subprocess
            remote_base = list_path.rstrip("/") if list_path else ""
            label = os.path.basename(local_path.rstrip("/"))
            dest  = f"/{remote_base}/{label}" if remote_base else f"/{label}"
            print(f"  Uploading {label} -> {dest} ...")
            ok = True
            for local_file, rel_path in uploads:
                remote_file = f"{remote_base}/{rel_path}" if remote_base else rel_path
                url = ftp_url(ip, remote_file)
                size_b = os.path.getsize(local_file)
                print(f"    {rel_path} ...", end=" ", flush=True)
                res = subprocess.run(["curl", "-s", "--ftp-create-dirs", "-T",
                                      local_file, url],
                                     capture_output=True, text=True)
                if res.returncode == 0:
                    print(f"done ({size_b:,} bytes)")
                else:
                    print(f"FAILED")
                    ok = False
            print(f"  Done." if ok else "  Completed with errors.")
            continue
        if idx == "up":
            if not list_path or list_path in ("", "/"):
                return
            list_path = "/".join(list_path.rstrip("/").split("/")[:-1])
            path = list_path
            continue

        name, is_dir, size = all_entries[idx]
        if is_dir:
            dir_path = f"{list_path}/{name}" if list_path else name
            # Get immediate listing for stats
            entries = ls_list(ip, dir_path) or []
            num_dirs  = sum(1 for _, d, _ in entries if d)
            num_files = sum(1 for _, d, _ in entries if not d)
            total_shown = sum(s for _, d, s in entries if not d)
            mb = total_shown / (1024*1024)
            if mb >= 1:
                size_str = f"~{mb:.1f} MB shown" if num_dirs else f"{mb:.1f} MB"
            else:
                kb = total_shown / 1024
                size_str = f"~{kb:.0f} KB shown" if num_dirs else f"{kb:.0f} KB"

            print(f"\n  Selected: /{dir_path}/")
            parts = []
            if num_dirs:  parts.append(f"{num_dirs} dirs")
            if num_files: parts.append(f"{num_files} files")
            parts.append(size_str)
            print(f"  {', '.join(parts)}")
            print()
            print(f"  [1] Enter directory")
            print(f"  [2] Download all")
            print(f"  [3] Go back")
            print()
            dir_choice = input("  Choose: ").strip()
            if dir_choice == "2":
                # Show warnings if needed
                warns = []
                if num_dirs:
                    warns.append("Has subdirs, true size unknown")
                if mb >= 50:
                    warns.append("Very large download")
                if warns:
                    warn_str = " - ".join(warns)
                    # Wrap at 38 chars
                    if len(f"  ** {warn_str}") > 38:
                        mid = warn_str.find(" - ")
                        if mid > 0:
                            print(f"  ** {warn_str[:mid]}")
                            print(f"     {warn_str[mid+3:]}")
                        else:
                            print(f"  ** {warn_str[:34]}")
                            print(f"     {warn_str[34:]}")
                    else:
                        print(f"  ** {warn_str}")
                    ans = input("  Download anyway? [y/N]: ").strip().lower()
                    if ans != "y":
                        continue
                target_dir = prompt_download_dir(name, None, multi_file=True)
                dest = os.path.join(target_dir, slugify(name)) if target_dir in (".", "") else target_dir
                print(f"  Downloading to {dest}/ ...")
                ftp_fetch_recursive(ip, dir_path, dest)
                print(f"  Done.")
            elif dir_choice == "1" or not dir_choice:
                base = list_path.rstrip("/")
                path = f"{base}/{name}/" if base else f"{name}/"
            continue

        full_path = f"/{list_path}/{name}" if list_path else f"/{name}"
        ext = "." + name.lower().rsplit(".", 1)[-1]
        print(f"\n  Selected: {full_path}")

        options = []
        if ext in DISK_TYPES or ext in ULTIMATE_RUNNERS:
            options.append(("rrun",   "Run on Ultimate (sid player)" if ext == ".sid" else "Run on Ultimate"))
            options.append(("rmount", "Mount on drive A"))
        if ext in (".txt", ".md", ".nfo", ".diz", ".info", ".me"):
            options.append(("view", "View contents"))
        options.append(("pull", "Download to current directory"))
        options.append(("back", "Go back"))

        print()
        for i, (_, lbl) in enumerate(options, 1):
            print(f"  [{i}] {lbl}")
        print()
        choice = input("  Choose (or Enter to go back): ").strip()
        if not choice:
            continue
        try:
            key, _ = options[int(choice) - 1]
        except (ValueError, IndexError):
            continue

        if key == "back":
            continue
        elif key == "view":
            res = subprocess.run(["curl", "-s", ftp_url(ip, full_path.lstrip("/"))],
                                 capture_output=True, text=True, errors="replace")
            if res.returncode == 0:
                header(f"View: {name}")
                print(res.stdout)
                sep()
                input("  Press Enter to continue...")
            else:
                print(f"  FAILED: {res.stderr.strip() or 'unknown error'}")
        elif key == "pull":
            local = name
            print(f"  Pulling {full_path} -> {local} ...")
            res = subprocess.run(["curl", "-s", "-o", local,
                                  ftp_url(ip, full_path.lstrip("/"))],
                                 capture_output=True, text=True)
            if res.returncode == 0 and os.path.exists(local):
                print(f"  Saved  ->  {local}  ({os.path.getsize(local):,} bytes)")
            else:
                print(f"  FAILED: {res.stderr.strip() or 'unknown error'}")
        elif key == "rmount":
            print(f"  Mounting {full_path} on drive A: ...", end=" ", flush=True)
            try:
                status = ultimate_put(ip, "drives/a:mount",
                                      {"image": full_path, "mode": "unlinked"})
                print(f"done  ({status})")
            except Exception as e:
                print(f"FAILED: {e}")
        elif key == "rrun":
            import argparse
            fake = argparse.Namespace(path=full_path, ip=ip)
            cmd_rrun(fake)


def cmd_ls(args):
    """List and browse files on the Ultimate interactively."""
    cfg = load_config()

    # If path looks like a device name, resolve its IP
    path_arg = args.path or ""
    if path_arg and not path_arg.startswith("/") and "/" not in path_arg:
        # Check if it matches a device name
        devices = cfg.get("devices", [])
        dev = next((d for d in devices if d["name"].lower() == path_arg.lower()), None)
        if dev:
            # Override IP and clear path
            args.ip   = dev["ip"]
            path_arg  = ""
            print(f"  Using device: {dev['name']} ({dev['ip']})")

    ip = args.ip or cfg.get("ultimate_ip", "")
    if not ip:
        ip = input("  Ultimate IP address: ").strip()
        if not ip:
            print("  No IP given.")
            return

    info = None
    try:
        req  = urllib.request.Request(f"http://{ip}/v1/info")
        with urllib.request.urlopen(req, timeout=5) as r:
            info = json.loads(r.read().decode("utf-8"))
    except Exception:
        pass
    hostname = info.get("hostname", ip) if info else ip

    if "*" in path_arg or "?" in path_arg:
        print("  Tip: on zsh, quote wildcards: \"GH*\"")

    # Default path: explicit arg > config default > root
    default_path = cfg.get("ls_default_path", "/")
    start_path   = path_arg or default_path

    run_ip = getattr(args, "run", None) or cfg.get("ultimate_ip", "")
    ls_browse(ip, hostname, start_path, run_ip=run_ip)


def cmd_mkdir(args):
    """Create a directory on the Ultimate filesystem."""
    import subprocess
    cfg = load_config()
    ip  = args.ip or cfg.get("ultimate_ip", "")
    if not ip:
        ip = input("  Ultimate IP address: ").strip()
        if not ip:
            print("  No IP given.")
            return
    path = args.path.lstrip("/")
    url  = ftp_url(ip, path + "/")
    print(f"  Creating /{path}/ ...")
    res = subprocess.run(["curl", "-s", "--ftp-create-dirs", url],
                         capture_output=True, text=True)
    if res.returncode == 0:
        print(f"  Done.")
    else:
        print(f"  FAILED: {res.stderr.strip() or 'unknown error'}")


def ftp_count_recursive(ip, path):
    """Count files and total bytes in a remote directory recursively."""
    entries = ls_list(ip, path) or []
    count, total = 0, 0
    for name, is_dir, size in entries:
        child = f"{path.rstrip('/')}/{name}"
        if is_dir:
            c, t = ftp_count_recursive(ip, child)
            count += c
            total += t
        else:
            count += 1
            total += size
    return count, total


def ftp_fetch_recursive(ip, remote_path, local_dir):
    """Download all files from a remote directory recursively into local_dir."""
    import subprocess
    entries = ls_list(ip, remote_path) or []
    os.makedirs(local_dir, exist_ok=True)
    for name, is_dir, size in entries:
        child_remote = f"{remote_path.rstrip('/')}/{name}"
        child_local  = os.path.join(local_dir, name)
        if is_dir:
            ftp_fetch_recursive(ip, child_remote, child_local)
        else:
            print(f"  Fetching {name} ...", end=" ", flush=True)
            res = subprocess.run(["curl", "-s", "-o", child_local,
                                  f"ftp://{ip}/{child_remote.lstrip('/')}"],
                                 capture_output=True, text=True)
            if res.returncode == 0:
                print(f"done  ({size:,} bytes)")
            else:
                print(f"FAILED")


def ftp_delete_recursive(ip, path):
    """Recursively delete a directory and all its contents via FTP."""
    import subprocess
    entries = ls_list(ip, path) or []
    for name, is_dir, _ in entries:
        child = f"{path.rstrip('/')}/{name}"
        if is_dir:
            ok, err = ftp_delete_recursive(ip, child)
            if not ok:
                return False, err
        else:
            res = subprocess.run([
                "curl", "-s", f"ftp://{ip}/",
                "--quote", f"DELE /{child.lstrip('/')}"
            ], capture_output=True, text=True, errors="replace")
            if res.returncode != 0:
                return False, res.stderr.strip()
    # Now remove the empty directory
    res = subprocess.run([
        "curl", "-s", f"ftp://{ip}/",
        "--quote", f"RMD /{path.lstrip('/')}"
    ], capture_output=True, text=True, errors="replace")
    return res.returncode == 0, res.stderr.strip()


def ftp_rename(ip, old_path, new_path):
    """Rename a file or directory on the Ultimate via FTP RNFR/RNTO."""
    import subprocess
    res = subprocess.run([
        "curl", "-s", f"ftp://{ip}/",
        "--quote", f"RNFR /{old_path.lstrip('/')}",
        "--quote", f"RNTO /{new_path.lstrip('/')}"
    ], capture_output=True, text=True)
    return res.returncode == 0, res.stderr.strip()


def ftp_delete(ip, path, is_dir=False):
    """Delete a file or directory on the Ultimate via FTP."""
    import subprocess
    if is_dir:
        res = subprocess.run([
            "curl", "-s", f"ftp://{ip}/",
            "--quote", f"RMD /{path.lstrip('/')}"
        ], capture_output=True, text=True, errors="replace")
    else:
        res = subprocess.run([
            "curl", "-s", f"ftp://{ip}/",
            "--quote", f"DELE /{path.lstrip('/')}"
        ], capture_output=True, text=True, errors="replace")
    return res.returncode == 0, res.stderr.strip()


def cmd_rename(args):
    """Rename a file or directory on the Ultimate filesystem."""
    cfg = load_config()
    ip  = args.ip or cfg.get("ultimate_ip", "")
    if not ip:
        ip = input("  Ultimate IP address: ").strip()
        if not ip:
            print("  No IP given.")
            return
    old = args.old.lstrip("/")
    new = args.new.lstrip("/")
    print(f"  Renaming /{old} -> /{new} ...")
    ok, err = ftp_rename(ip, old, new)
    print("  Done." if ok else f"  FAILED: {err or 'unknown error'}")


def cmd_delete(args):
    """Delete a file or directory on the Ultimate filesystem."""
    cfg = load_config()
    ip  = args.ip or cfg.get("ultimate_ip", "")
    if not ip:
        ip = input("  Ultimate IP address: ").strip()
        if not ip:
            print("  No IP given.")
            return
    path = args.path.lstrip("/")
    ans  = input(f"  Delete /{path}? [y/N]: ").strip().lower()
    if ans != "y":
        print("  Cancelled.")
        return
    ok, err = ftp_delete(ip, path, is_dir=args.dir)
    print("  Done." if ok else f"  FAILED: {err or 'unknown error'}")


def cmd_reset(args):
    cfg = load_config()
    ip  = args.ip or cfg.get("ultimate_ip", "")
    if not ip:
        ip = input("  Ultimate IP address: ").strip()
        if not ip:
            print("  No IP given.")
            return
    print(f"  Resetting C64 at {ip} ...", end=" ", flush=True)
    try:
        status = ultimate_put(ip, "machine:reset")
        print(f"done  ({status})")
    except Exception as e:
        print(f"FAILED: {e}")


def cmd_reboot(args):
    cfg = load_config()
    ip  = args.ip or cfg.get("ultimate_ip", "")
    if not ip:
        ip = input("  Ultimate IP address: ").strip()
        if not ip:
            print("  No IP given.")
            return
    print(f"  Rebooting C64 at {ip} ...", end=" ", flush=True)
    try:
        status = ultimate_put(ip, "machine:reboot")
        print(f"done  ({status})")
    except Exception as e:
        print(f"FAILED: {e}")


def active_ip(args=None, cfg=None):
    """Return the currently active Ultimate IP from args, config, or prompt."""
    if cfg is None:
        cfg = load_config()
    ip = (getattr(args, "ip", None) or "") if args else ""
    return ip or cfg.get("ultimate_ip", "")



def cmd_device_list(args):
    """List configured devices (read-only)."""
    cfg     = load_config()
    devices = cfg.get("devices", [])
    current = cfg.get("default_device", "")
    if not devices:
        print("  No devices configured.")
        print("  Use: assembly64 config --add NAME IP")
        return
    header("DEVICES")
    for d in devices:
        marker = " *" if d["name"] == current else ""
        print(f"  {d['name']:<20} {d['ip']}{marker}")
    print(f"  (* = active)")
    sep()


def cmd_config(args):
    cfg     = load_config()
    devices = cfg.get("devices", [])
    changed = False

    # Device management
    if getattr(args, "add", None):
        name, ip = args.add
        if any(d["name"] == name for d in devices):
            print(f"  Device '{name}' already exists. Use --remove first.")
            return
        devices.append({"name": name, "ip": ip})
        cfg["devices"] = devices
        if not cfg.get("ultimate_ip"):
            cfg["ultimate_ip"] = ip
            cfg["default_device"] = name
        save_config(cfg)
        print(f"  Added: {name} ({ip})")
        return

    if getattr(args, "remove", None):
        name   = args.remove
        before = len(devices)
        devices = [d for d in devices if d["name"] != name]
        if len(devices) == before:
            print(f"  Device '{name}' not found.")
            return
        cfg["devices"] = devices
        if cfg.get("default_device") == name:
            if devices:
                cfg["default_device"] = devices[0]["name"]
                cfg["ultimate_ip"]    = devices[0]["ip"]
                print(f"  Switched active to: {devices[0]['name']}")
            else:
                cfg.pop("default_device", None)
                cfg.pop("ultimate_ip", None)
        save_config(cfg)
        print(f"  Removed: {name}")
        return

    if getattr(args, "set", None):
        name = args.set
        dev  = next((d for d in devices if d["name"] == name), None)
        if not dev:
            print(f"  Device '{name}' not found.")
            return
        cfg["default_device"] = name
        cfg["ultimate_ip"]    = dev["ip"]
        save_config(cfg)
        print(f"  Active: {name} ({dev['ip']})")
        return

    if getattr(args, "next", False):
        if not devices:
            print("  No devices configured.")
            return
        current  = cfg.get("default_device", "")
        idx      = next((i for i, d in enumerate(devices) if d["name"] == current), -1)
        next_dev = devices[(idx + 1) % len(devices)]
        cfg["default_device"] = next_dev["name"]
        cfg["ultimate_ip"]    = next_dev["ip"]
        save_config(cfg)
        print(f"  Active: {next_dev['name']} ({next_dev['ip']})")
        return

    # Settings
    if getattr(args, "set_ip", None):
        cfg["ultimate_ip"] = args.set_ip
        changed = True
        print(f"  Saved IP: {args.set_ip}")

    if getattr(args, "set_demos_dir", None):
        cfg["download_dir_demos"] = os.path.expanduser(args.set_demos_dir)
        changed = True
        print(f"  Saved demos dir: {cfg['download_dir_demos']}")

    if getattr(args, "set_sids_dir", None):
        cfg["download_dir_sids"] = os.path.expanduser(args.set_sids_dir)
        changed = True
        print(f"  Saved SIDs dir: {cfg['download_dir_sids']}")

    if getattr(args, "set_ls_path", None):
        cfg["ls_default_path"] = args.set_ls_path
        changed = True
        print(f"  Saved ls default path: {args.set_ls_path}")

    if changed:
        save_config(cfg)
        return

    # Show all config
    header("CONFIG")
    current = cfg.get("default_device", "")
    print(f"  Config:    {CONFIG_FILE}")
    print(f"  Active IP: {cfg.get('ultimate_ip', '(not set)')}")
    demos = cfg.get("download_dir_demos", "")
    sids  = cfg.get("download_dir_sids", "")
    ls_path = cfg.get("ls_default_path", "")
    if demos:
        print(f"  Demos dir: {demos}")
    if sids:
        print(f"  SIDs dir:  {sids}")
    if ls_path:
        print(f"  ls path:   {ls_path}")
    if devices:
        sep()
        for d in devices:
            marker = " *" if d["name"] == current else ""
            print(f"  {d['name']:<20} {d['ip']}{marker}")
        print(f"  (* = active)")
    elif not cfg:
        print("  (no config saved)")
    sep()

# ---------- Parser ------------------------------------------------------------

def add_common(sp):
    sp.add_argument("--group",   metavar="NAME",  help="Filter by group name")
    sp.add_argument("--handle",  metavar="NAME",  help="Filter by handle/scener")
    sp.add_argument("--repo",    metavar="REPO",  help=f"Filter by repo: {', '.join(sorted(REPOS))}")
    sp.add_argument("--cat",     metavar="CAT",   help=f"Filter by category: {', '.join(CATEGORIES)}")
    sp.add_argument("--date",    metavar="DATE",  help="Exact date: YYYYMMDD or YYYYMM or YYYY")
    sp.add_argument("--after",   metavar="DATE",  help="Released after: YYYYMMDD")
    sp.add_argument("--before",  metavar="DATE",  help="Released before: YYYYMMDD")
    sp.add_argument("--order",   choices=["asc", "desc"], help="Sort order")
    sp.add_argument("--limit",   type=int, default=50, metavar="N", help="Max results (default: 50)")
    sp.add_argument("--files",   action="store_true", help="Show file listing only")
    sp.add_argument("--download",action="store_true", help="Download without prompting")
    sp.add_argument("--run",     metavar="IP",    help="Run on Ultimate at IP without prompting")
    sp.add_argument("--autodisk", action="store_true", help="Auto-flip disks using Assembly64 flip timings (--run required)")


FULL_HELP = """
ASSEMBLY64 - C64 Scene Tool
hackerswithstyle.se/leet/

COMMANDS
  search [query]   Search releases
  sid <query>      Search HVSC SIDs
  charts           Browse top charts
  presets          Browse AQL presets
  cats             Browse categories
  ls/remote [path] Browse Ultimate files
  push/put <file>  Upload to Ultimate
  pull/get <path>  Download
  run <path>       Run local file/dir
  rrun <path>      Run file on Ultimate
  mount <file>     Mount local disk
  rmount <path>    Mount remote disk
  mkdir <path>     Create directory
  rename <old> <new>  Rename
  delete <path>    Delete file/dir
  reset            Reset the C64
  reboot           Reboot the C64
  device/devices   List devices
  config           Show/set config
  help             Show this help

SEARCH FLAGS
  --group  --handle  --repo  --cat
  --date / --after / --before
  --order asc|desc  --limit N
  --download  --run IP  --autodisk

SEARCH NOTES
  Results fetched 50 at a time.
  Use Next to page through results.
  Use cats to browse all repos.

FILE TYPES
  .prg .crt   DMA load and run
  .sid        SID player
  .d64 .d71 .d81 .g64 .g71
              Mount, reset, autorun

MULTI-DISK AUTO-FLIP
  Enter=flip now  q+Enter=stop

LS/REMOTE BROWSER KEYS
  number    select / descend
  u / ^     go up a level
  b / <-    prev page
  n / ->    next page
  m         make directory
  r         rename
  d         delete
  q         quit

LS TIPS
  ls              start at / or default
  ls USB1/DEMOS   start at specific path
  ls U64EII       use named device
  config --set-ls-path USB1  set default

CONFIG FLAGS
  --set-ip IP      Set active IP
  --set-demos-dir  Set demos dir
  --set-sids-dir   Set SIDs dir
  --set-ls-path    Set default ls path
  --add NAME IP    Add a device
  --remove NAME    Remove a device
  --set NAME       Set active device
  --next           Cycle to next device
"""

EXAMPLES = """
EXAMPLES
  assembly64 search "edge of disgrace"
  assembly64 search --group fairlight
  assembly64 search --handle laxity
  assembly64 sid sanxion
  assembly64 charts
  assembly64 ls
  assembly64 ls USB1/DEMOS
  assembly64 ls U64EII
  assembly64 remote
  assembly64 push game.d64
  assembly64 run mygame.d64
  assembly64 rrun SD/_BASIC/Tetris.d64
  assembly64 reset
  assembly64 device
  assembly64 config
  assembly64 config --set-ip 192.168.2.32
  assembly64 config --set-demos-dir ~/demos
  assembly64 config --set-sids-dir ~/sids
  assembly64 config --set-ls-path USB1
  assembly64 config --add U64 192.168.2.32
  assembly64 config --add U2L 192.168.2.33
  assembly64 config --set U2L
  assembly64 config --next
  assembly64 config --remove U2L
"""


def cmd_help(args):
    print(FULL_HELP)
    print(EXAMPLES)



def build_parser():
    p = argparse.ArgumentParser(
        prog="assembly64",
        description="C64 scene lookup via the Assembly64 API (hackerswithstyle.se/leet/)",
        formatter_class=ColoredHelpFormatter,
    )
    p.add_argument("--full-help", "--fullhelp", action="store_true", help="Show full help")
    p.add_argument("--examples",  action="store_true", help="Show examples")
    p.add_argument("--version",   action="store_true", help="Show version")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("help", help="Show full help")

    s = sub.add_parser("search", help="Search by name or AQL filters")
    s.add_argument("name", nargs="?", metavar="QUERY")
    add_common(s)

    si = sub.add_parser("sid", help="Search HVSC SID music by tune name")
    si.add_argument("query", metavar="QUERY")
    si.add_argument("--after",    metavar="DATE")
    si.add_argument("--before",   metavar="DATE")
    si.add_argument("--order",    choices=["asc", "desc"])
    si.add_argument("--limit",    type=int, default=50, metavar="N")
    si.add_argument("--files",    action="store_true")
    si.add_argument("--download", action="store_true")
    si.add_argument("--run",      metavar="IP")

    ch = sub.add_parser("charts", help="Browse top charts")
    ch.add_argument("name", nargs="?", metavar="CHART")
    ch.add_argument("--files",    action="store_true")
    ch.add_argument("--download", action="store_true")
    ch.add_argument("--run",      metavar="IP")

    pr = sub.add_parser("presets", help="Browse AQL query presets")
    pr.add_argument("name", nargs="?", metavar="TYPE")

    ca = sub.add_parser("cats", aliases=["cat", "category"], help="Browse categories")
    ca.add_argument("--list",     action="store_true", help="List all categories and exit")
    ca.add_argument("--download", action="store_true")
    ca.add_argument("--run",      metavar="IP")

    ru = sub.add_parser("run", help="Run a local file or directory on the Ultimate")
    ru.add_argument("path", metavar="PATH", help="File or directory to run")
    ru.add_argument("--ip", metavar="IP", help="Ultimate IP (uses saved default if not given)")
    ru.add_argument("--remote", action="store_true", help="Path is on the Ultimate filesystem, not local")

    ls = sub.add_parser("ls", aliases=["remote"], help="List files on the Ultimate")
    ls.add_argument("path", nargs="?", metavar="PATH", help="Remote path (default: USB1/)")
    ls.add_argument("--ip", metavar="IP")

    pu = sub.add_parser("pull", aliases=["get"], help="Download a file from the Ultimate")
    pu.add_argument("remote", metavar="REMOTE", help="Remote path e.g. USB1/DEMOS/foo.d64")
    pu.add_argument("local", nargs="?", metavar="LOCAL", help="Local filename (default: basename of remote)")
    pu.add_argument("--ip", metavar="IP")

    ps = sub.add_parser("push", aliases=["put"], help="Upload a file to the Ultimate")
    ps.add_argument("local", metavar="LOCAL", help="Local file to upload")
    ps.add_argument("remote", nargs="?", metavar="REMOTE", help="Remote directory (default: USB1/)")
    ps.add_argument("--ip", metavar="IP")

    rr = sub.add_parser("rrun", help="Run a file already on the Ultimate filesystem")
    rr.add_argument("path", metavar="PATH", help="Path on Ultimate e.g. SD/_BASIC/Tetris.d64")
    rr.add_argument("--ip", metavar="IP")

    mo = sub.add_parser("mount", help="Mount a disk image on drive A (local or remote)")
    mo.add_argument("path", metavar="PATH", help="Local file or remote path on Ultimate")
    mo.add_argument("--ip",     metavar="IP", help="Ultimate IP (uses saved default if not given)")
    mo.add_argument("--remote", action="store_true", help="Path is on the Ultimate filesystem, not local")

    rm = sub.add_parser("rmount", help="Mount a file already on the Ultimate filesystem")
    rm.add_argument("path", metavar="PATH", help="Path on Ultimate e.g. SD/_BASIC/Tetris.d64")
    rm.add_argument("--ip", metavar="IP")

    md = sub.add_parser("mkdir", help="Create a directory on the Ultimate filesystem")
    md.add_argument("path", metavar="PATH", help="Directory to create e.g. USB1/NEWDIR")
    md.add_argument("--ip", metavar="IP")

    rn = sub.add_parser("rename", help="Rename a file or directory on the Ultimate")
    rn.add_argument("old", metavar="OLD", help="Current path")
    rn.add_argument("new", metavar="NEW", help="New path")
    rn.add_argument("--ip", metavar="IP")

    dl = sub.add_parser("delete", help="Delete a file or directory on the Ultimate")
    dl.add_argument("path", metavar="PATH")
    dl.add_argument("--dir", action="store_true", help="Path is a directory")
    dl.add_argument("--ip", metavar="IP")

    rst = sub.add_parser("reset", help="Reset the C64")
    rst.add_argument("--ip", metavar="IP", help="Ultimate IP (uses saved default if not given)")

    rbt = sub.add_parser("reboot", help="Reboot the C64 (reinitialises cartridge + reset)")
    rbt.add_argument("--ip", metavar="IP", help="Ultimate IP (uses saved default if not given)")

    cfg_p = sub.add_parser("config", help="Show or set saved configuration")
    cfg_p.add_argument("--set-ip",        metavar="IP",          help="Save default Ultimate IP")
    cfg_p.add_argument("--set-demos-dir", metavar="DIR",         help="Default download dir for demos")
    cfg_p.add_argument("--set-sids-dir",  metavar="DIR",         help="Default download dir for SIDs")
    cfg_p.add_argument("--set-ls-path",   metavar="PATH",        help="Default ls start path (default: /)")
    cfg_p.add_argument("--add",           nargs=2, metavar=("NAME", "IP"), help="Add a device")
    cfg_p.add_argument("--remove",        metavar="NAME",        help="Remove a device")
    cfg_p.add_argument("--set",           metavar="NAME",        help="Set active device")
    cfg_p.add_argument("--next",          action="store_true",   help="Switch to next device")

    sub.add_parser("device",  aliases=["devices"], help="List configured Ultimate devices")

    return p


def main():
    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    # Handle --full-help, --fullhelp, --examples before subcommand parsing
    if "--version" in sys.argv:
        print(f"  assembly64  v{VERSION}  (build {BUILD})")
        sys.exit(0)
    if "--full-help" in sys.argv or "--fullhelp" in sys.argv:
        print(FULL_HELP)
        print(EXAMPLES)
        sys.exit(0)
    if "--examples" in sys.argv:
        print(EXAMPLES)
        sys.exit(0)

    args = parser.parse_args()

    if args.cmd == "help":
        cmd_help(args)
    elif args.cmd == "search":
        cmd_search(args)
    elif args.cmd == "sid":
        cmd_sid(args)
    elif args.cmd == "charts":
        cmd_charts(args)
    elif args.cmd == "presets":
        cmd_presets(args)
    elif args.cmd in ("cats", "cat", "category"):
        cmd_categories(args)
    elif args.cmd == "run":
        cmd_run(args)
    elif args.cmd in ("ls", "remote"):
        cmd_ls(args)
    elif args.cmd in ("pull", "get"):
        cmd_pull(args)
    elif args.cmd in ("push", "put"):
        cmd_push(args)
    elif args.cmd == "rrun":
        cmd_rrun(args)
    elif args.cmd == "rmount":
        cmd_rmount(args)
    elif args.cmd == "mount":
        cmd_mount(args)
    elif args.cmd == "mkdir":
        cmd_mkdir(args)
    elif args.cmd == "rename":
        cmd_rename(args)
    elif args.cmd == "delete":
        cmd_delete(args)
    elif args.cmd == "reset":
        cmd_reset(args)
    elif args.cmd == "reboot":
        cmd_reboot(args)
    elif args.cmd in ("config", "device", "devices"):
        if args.cmd in ("device", "devices"):
            cmd_device_list(args)
        else:
            cmd_config(args)


if __name__ == "__main__":
    main()
