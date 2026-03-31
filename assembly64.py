#!/usr/bin/env python3

import sys
import os
import json
import argparse
import urllib.request
import urllib.parse

BASE         = "https://hackerswithstyle.se/leet/"
HEADERS      = {"client-id": "swagger", "Accept": "application/json"}
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
            return json.load(f)
    except Exception:
        return {}

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

# ---------- Formatting --------------------------------------------------------

def sep():
    print("-" * 62)

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

def resolve_cat(val):
    key = val.lower()
    if key in CAT_IDS:
        return CAT_IDS[key]
    try:
        return int(val)
    except ValueError:
        sys.exit(f"Unknown category '{val}'. Use a number or: {', '.join(CAT_IDS)}")

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
    2. Value stabilises (same value N times in a row — load is done)
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
                # Loading started — wait for value to stabilise
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
    """Upload and mount a disk image, reset, inject LOAD+RUN, wait for load to complete."""
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
        return False

    print(f"  Resetting machine ...", end=" ", flush=True)
    try:
        ultimate_put(ip, "machine:reset")
        print("done")
    except Exception as e:
        print(f"FAILED: {e}")
        return False

    time.sleep(3)
    print('  Injecting LOAD"*",8,1 + RUN ...')
    inject_keyboard(ip, 'LOAD"*",8,1\rRUN\r')
    wait_for_load(ip)
    return True


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
    req     = urllib.request.Request(url, headers={"client-id": "swagger"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def download_file(item_id, cat, f, run_ip=None):
    file_id  = f.get("id")
    filename = f.get("path", f"file_{file_id}").replace("\\", "/").split("/")[-1]
    print(f"  Downloading {filename} ...", end=" ", flush=True)
    try:
        data = fetch_file_data(item_id, cat, f)
        print(f"done  ({len(data):,} bytes)")
        if run_ip:
            run_on_ultimate(filename, data, run_ip)
        else:
            with open(filename, "wb") as out:
                out.write(data)
            print(f"  Saved  ->  {filename}")
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

def action_prompt(run_ip, flipinfo=None):
    """Ask user what to do. Returns ('run', ip), ('autodisk', ip), ('download',), or None."""
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
    options.append(("download", "Download to current directory"))
    options.append(("quit",     "Quit"))

    print()
    for i, (_, label) in enumerate(options, 1):
        print(f"  [{i}] {label}")
    print()
    choice = input("  Choose action (or Enter to quit): ").strip()
    if not choice:
        return None
    try:
        key, _ = options[int(choice) - 1]
        if key == "quit":
            return None
        if key == "download":
            return ("download",)
        if key in ("run", "autodisk"):
            ip = effective_ip
            if not ip:
                ip = input("  Ultimate IP address (or Enter to download instead): ").strip()
                if not ip:
                    print("  No IP given — downloading instead.")
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

    # Build ordered list matching flipinfo diskNames to disk_cache
    cache_map = {fn.lower(): (fn, data) for fn, data in disk_cache}
    ordered   = []
    for entry in flipinfo:
        dn = entry.get("diskName", "").lower()
        if dn in cache_map:
            ordered.append((cache_map[dn][0], cache_map[dn][1], entry.get("length", 0)))
    if not ordered:
        ordered = [(fn, data, 0) for fn, data in disk_cache]

    fn, data, duration = ordered[0]
    if not mount_and_run(ip, fn, data):
        return

    import select, sys

    stop = threading.Event()

    def check_quit():
        """Non-blocking stdin check — returns True if user typed q."""
        if select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline()
            if line.strip().lower() == "q":
                return True
        return False

    print("\n  Press q+Enter at any time to stop auto-flip.")

    for i, (fn, data, duration) in enumerate(ordered[1:], 1):
        for remaining in range(duration, 0, -1):
            if stop.is_set():
                break
            m, s = divmod(remaining, 60)
            print(f"\r  Auto-flip: disk {i+1} ({fn}) in {m}m {s:02d}s ...", end="", flush=True)
            time.sleep(1)
            if check_quit():
                stop.set()
                break

        print()
        if stop.is_set():
            print("  Auto-flip stopped.")
            return

        if data:
            print(f"  Flipping to disk {i+1}: {fn}")
            mount_disk(ip, fn, data)
        else:
            print(f"  Disk {i+1} data missing, skipping.")

    print("\n  All disks played.")


def handle_files(iid, cat, entries, run_ip, download, flipinfo=None):
    """Handle file listing, download, or run for a set of entries."""
    disk_exts = set(DISK_TYPES.keys())
    disks     = [f for f in entries
                 if "." + f.get("path","").lower().rsplit(".",1)[-1] in disk_exts]

    if run_ip and len(disks) > 1:
        print(f"\n  Multi-disk release — {len(disks)} disk image(s):")
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
                                print(f"  Invalid — valid range 1-{len(disk_cache)}")
                                continue
                        fn, data = disk_cache[disk_idx]
                        if data:
                            mount_disk(run_ip, fn, data)
                        else:
                            print(f"  Disk {disk_idx+1} failed to download, skipping.")
                        disk_idx += 1
        return

    if len(entries) == 1:
        download_file(iid, cat, entries[0], run_ip=run_ip)
    else:
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
                print("  Invalid — processing all.")
        for f in entries:
            download_file(iid, cat, f, run_ip=run_ip)


def show_item(item, run_ip=None, download=False, show_files=False, autodisk=False):
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
        print(f"\n  Flip info available — {len(flipinfo)} disks with auto-flip timings.")

    if show_files and not download and not run_ip:
        print("\n  Files:")
        for i, f in enumerate(entries, 1):
            print(f"    [{i}] {f.get('path','')}  ({f.get('size',0):,} bytes)")
        return

    if download:
        handle_files(iid, cat, entries, run_ip=None, download=True)
        return

    if run_ip:
        fi = flipinfo if autodisk else None
        handle_files(iid, cat, entries, run_ip=run_ip, download=False, flipinfo=fi)
        return

    # Interactive action prompt
    print("\n  Files:")
    for i, f in enumerate(entries, 1):
        print(f"    {i:>3}. {f.get('path','')}  ({f.get('size',0):,} bytes)")

    action = action_prompt(run_ip=None, flipinfo=flipinfo)
    if action is None:
        return
    if action[0] in ("run", "autodisk"):
        ip = action[1]
        fi = flipinfo if action[0] == "autodisk" else None
        handle_files(iid, cat, entries, run_ip=ip, download=False, flipinfo=fi)
    elif action[0] == "download":
        if len(entries) == 1:
            download_file(iid, cat, entries[0])
        else:
            choice = input("\n  Enter number to download (or Enter for all): ").strip()
            if choice:
                try:
                    entries = [entries[int(choice) - 1]]
                except (ValueError, IndexError):
                    print("  Invalid — downloading all.")
            for f in entries:
                download_file(iid, cat, f)

# ---------- List helpers ------------------------------------------------------

PAGE_SIZE = 20


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
                # Escape sequence — read two more chars
                seq = sys.stdin.read(2)
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
                sys.stdout.write("\n")
                if seq == "[C":   # right arrow
                    return "n"
                elif seq == "[D": # left arrow
                    return "p"
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


def paginated_list(rows, prompt):
    """
    Display a paginated list. rows is a list of pre-formatted strings.
    Returns the chosen 0-based index, or None.
    Navigation: number to select, n/→ next, p/← prev, q/Enter to quit.
    """
    total  = len(rows)
    offset = 0
    while True:
        page_rows = rows[offset:offset + PAGE_SIZE]
        for line in page_rows:
            print(line)
        end = offset + len(page_rows)
        print()
        if end < total:
            print(f"  Showing {offset+1}-{end} of {total}  |  n/→=next  p/←=prev  q=quit")
        else:
            print(f"  Showing {offset+1}-{end} of {total}")
        print()
        choice = read_input(f"  {prompt}: ").lower()
        if not choice or choice == "q":
            return None
        if choice == "n":
            if end < total:
                offset += PAGE_SIZE
            continue
        if choice == "p":
            offset = max(0, offset - PAGE_SIZE)
            continue
        try:
            idx = int(choice) - 1
            if 0 <= idx < total:
                return idx
            print(f"  Out of range (1-{total})")
        except ValueError:
            print("  Invalid — enter a number, n/→, p/←, or q")


def pick(items, run_ip=None, download=False, show_files=False, autodisk=False):
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
    idx = paginated_list(rows, "Enter number to view details")
    if idx is None:
        return
    show_item(items[idx], run_ip=run_ip, download=download, show_files=show_files, autodisk=autodisk)


def pick_name(names, prompt="select"):
    print(f"\n  {len(names)} match(es):\n")
    rows = [f"  {i:>3}. {n}" for i, n in enumerate(names, 1)]
    idx  = paginated_list(rows, f"Enter number to {prompt}")
    if idx is None:
        return None
    return names[idx]

# ---------- AQL ---------------------------------------------------------------

def q_val(s):
    return f'"{s}"' if " " in s else s

def build_query(args):
    parts = []
    if hasattr(args, "group") and args.group:
        parts.append(f"group:{q_val(args.group)}")
    if hasattr(args, "handle") and args.handle:
        parts.append(f"handle:{q_val(args.handle)}")
    if hasattr(args, "repo") and args.repo:
        parts.append(f"repo:{args.repo}")
    if hasattr(args, "cat") and args.cat:
        key = args.cat.lower()
        parts.append(f"category:{CATEGORIES.get(key, args.cat)}")
    if hasattr(args, "date") and args.date:
        parts.append(f"date:{args.date}")
    if hasattr(args, "after") and args.after:
        parts.append(f"date:>{args.after}")
    if hasattr(args, "before") and args.before:
        parts.append(f"date:<{args.before}")
    if hasattr(args, "order") and args.order:
        parts.append(f"order:{args.order}")
    return " ".join(parts)

# ---------- Commands ----------------------------------------------------------

def cmd_search(args):
    run_ip   = getattr(args, "run", None)
    download = getattr(args, "download", False)
    has_kv   = any([args.group, args.handle, args.repo, args.cat,
                    args.date, args.after, args.before])

    if args.name and not has_kv:
        enc   = urllib.parse.quote(args.name.replace(" ", ""))
        cat   = resolve_cat(args.cat) if args.cat else 1
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

    if not has_kv:
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


def cmd_categories():
    data = get("search/categories")
    if not isinstance(data, list):
        print("  Could not fetch categories.")
        return
    header("CATEGORIES")
    by_type = {}
    for c in data:
        by_type.setdefault(c.get("type", "other"), []).append(c)
    for t, cats in sorted(by_type.items()):
        print(f"  {t}:")
        for c in sorted(cats, key=lambda x: x["id"]):
            print(f"    {c['id']:>3}  {c['description']}  ({c['name']})")
        print()
    sep()


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
    cfg = load_config()
    if args.set_ip:
        cfg["ultimate_ip"] = args.set_ip
        save_config(cfg)
        print(f"  Saved Ultimate IP: {args.set_ip}")
    elif args.show:
        header("CONFIG")
        for k, v in cfg.items():
            field(f"{k}:", v)
        if not cfg:
            print("  (no config saved)")
        sep()
    else:
        print(f"  Config file: {CONFIG_FILE}")
        print(f"  Current IP:  {cfg.get('ultimate_ip', '(not set)')}")

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


def build_parser():
    p = argparse.ArgumentParser(
        prog="assembly64",
        description="C64 scene lookup via the Assembly64 API (hackerswithstyle.se/leet/)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Commands:
  search  [query]  Search by name or AQL filters
  sid     <query>  Search HVSC SID music
  charts  [name]   Browse top charts
  presets [type]   Browse AQL query presets
  cats             List all categories
  reset            Reset the C64 (uses saved IP or prompts)
  config           Show/set saved config

After selecting any item you'll be prompted to:
  Run on Ultimate          — sends file to your C64 via REST API
  Run with auto disk flip  — auto-mounts disks using Assembly64 flip timings
                             (only shown when flip info is available)
  Download                 — saves to current directory
  Quit

Supported file types for --run:
  .prg / .crt   DMA load and run
  .sid          SID player
  .d64 / .g64 / .d71 / .g71 / .d81
                mount on drive A, reset, inject LOAD"*",8,1 + RUN

Multi-disk releases:
  Disks are downloaded upfront. You're prompted to flip manually,
  or use auto disk flip (if flip info available) which counts down
  and mounts the next disk automatically. Press q+Enter to stop.

Flags (bypass the interactive prompt):
  --download         download immediately without prompting
  --run IP           run on Ultimate at IP without prompting
  --autodisk         use auto disk flip timing (requires --run)
  --files            show file listing only, no action
  --limit N          max AQL results (default 50)

Pagination: n/→ next page, p/← prev page, q/Enter to quit

Save your Ultimate IP so you don't have to type it every time:
  assembly64 config --set-ip 192.168.2.32
  assembly64 config --show

Name search (uses search/releases):
  assembly64 search "edge of disgrace"         CSDB demos (default)
  assembly64 search "commando" --cat games     CSDB games
  assembly64 sid sanxion                       HVSC SIDs

AQL filter search (needs at least one of --group/--handle/--repo/--cat/--date):
  --group    group name  e.g. fairlight, "Booze Design"
  --handle   scener      e.g. laxity
  --repo     {', '.join(sorted(REPOS))}
  --cat      {', '.join(CATEGORIES)}
  --date / --after / --before   YYYYMMDD
  --order    asc or desc

Examples:
  assembly64 search "edge of disgrace"
  assembly64 search "edge of disgrace" --run 192.168.2.32
  assembly64 search "edge of disgrace" --run 192.168.2.32 --autodisk
  assembly64 search --group fairlight --cat demos --order asc
  assembly64 search --group "Booze Design" --after 20000101
  assembly64 search --handle laxity --repo csdb
  assembly64 sid sanxion
  assembly64 charts
  assembly64 charts "Top Demos"
  assembly64 presets
  assembly64 reset
  assembly64 config --set-ip 192.168.2.32
        """
    )
    sub = p.add_subparsers(dest="cmd", required=True)

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

    sub.add_parser("cats", help="List all categories")

    rst = sub.add_parser("reset", help="Reset the C64")
    rst.add_argument("--ip", metavar="IP", help="Ultimate IP (uses saved default if not given)")

    cfg = sub.add_parser("config", help="Show or set saved configuration")
    cfg.add_argument("--set-ip", metavar="IP", help="Save default Ultimate IP address")
    cfg.add_argument("--show",   action="store_true", help="Show current config")

    return p


def main():
    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    args = parser.parse_args()

    if args.cmd == "search":
        cmd_search(args)
    elif args.cmd == "sid":
        cmd_sid(args)
    elif args.cmd == "charts":
        cmd_charts(args)
    elif args.cmd == "presets":
        cmd_presets(args)
    elif args.cmd == "cats":
        cmd_categories()
    elif args.cmd == "reset":
        cmd_reset(args)
    elif args.cmd == "config":
        cmd_config(args)


if __name__ == "__main__":
    main()
