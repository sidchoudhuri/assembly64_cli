#!/usr/bin/env python3

import sys
import json
import argparse
import urllib.request
import urllib.parse

BASE    = "https://hackerswithstyle.se/leet/"
HEADERS = {"client-id": "swagger", "Accept": "application/json"}

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

REPOS = {
    "csdb", "gamebase64", "guybrush", "hvsc", "mayhem",
    "oneload", "pres", "seuck", "tapes", "c64com",
    "c64orgintro", "commodore", "utape",
}


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
    qs  = urllib.parse.urlencode({"query": query})
    return get(f"search/aql/{offset}/{limit}?{qs}")


def sep():
    print("-" * 62)


def header(t):
    sep()
    print(f"  {t}")
    sep()


def field(label, value, width=14):
    if value not in (None, "", 0, 0.0):
        print(f"  {label:<{width}} {value}")


def cat_label(cat_id):
    for name, cid in CATEGORIES.items():
        if cid == cat_id:
            return name
    return str(cat_id)


def download_file(item_id, cat, f):
    file_id  = f.get("id")
    filename = f.get("path", f"file_{file_id}").replace("\\", "/").split("/")[-1]
    url      = BASE + f"search/bin/{urllib.parse.quote(str(item_id))}/{cat}/{file_id}"
    req      = urllib.request.Request(url, headers={"client-id": "swagger"})
    print(f"  Downloading {filename} ...", end=" ", flush=True)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        with open(filename, "wb") as out:
            out.write(data)
        print(f"done  ({len(data):,} bytes)  ->  {filename}")
    except Exception as e:
        print(f"FAILED: {e}")


def show_item(item, show_files=False, download=False):
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

    header(name)
    field("ID:",       iid)
    field("Category:", cat_label(cat) if isinstance(cat, int) else cat)
    field("Group:",    group)
    field("Handle:",   handle)
    field("Year:",     str(year) if year else "")
    field("Released:", released)
    field("Rating:",   str(rating) if rating else "")
    field("Event:",    event)
    if compo:
        field("Compo:", f"{compo}  (place #{place})" if place else compo)

    if (show_files or download) and iid:
        resp    = get(f"search/entries/{urllib.parse.quote(str(iid))}/{cat}")
        entries = resp.get("contentEntry", []) if isinstance(resp, dict) else []
        if entries:
            print()
            if not download:
                print("  Files:")
                for f in entries:
                    print(f"    [{f.get('id')}] {f.get('path','')}  ({f.get('size',0):,} bytes)")
            else:
                if len(entries) == 1:
                    download_file(iid, cat, entries[0])
                else:
                    print("  Files:")
                    for f in entries:
                        print(f"    {f.get('id')+1:>3}. {f.get('path','')}  ({f.get('size',0):,} bytes)")
                    print()
                    choice = input("  Enter number to download (or Enter for all): ").strip()
                    if choice:
                        try:
                            entries = [entries[int(choice) - 1]]
                        except (ValueError, IndexError):
                            print("  Invalid — downloading all.")
                    for f in entries:
                        download_file(iid, cat, f)
    sep()


def pick(items, show_files=False, download=False):
    print(f"\n  {len(items)} result(s):\n")
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
        print(f"  {i:>3}. {name}  [{extra}]")
    print()
    choice = input("  Enter number to view details (or Enter to quit): ").strip()
    if not choice:
        return
    try:
        show_item(items[int(choice) - 1], show_files=show_files, download=download)
    except (ValueError, IndexError):
        print("  Invalid choice.")


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
        aql_name = CATEGORIES.get(key, args.cat)
        parts.append(f"category:{aql_name}")
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
    has_kv_filter = any([
        args.group, args.handle, args.repo, args.cat,
        args.date, args.after, args.before
    ])

    if args.name and not has_kv_filter:
        enc   = urllib.parse.quote(args.name.replace(" ", ""))
        cat   = resolve_cat(args.cat) if args.cat else 1
        names = get(f"search/releases/{enc}/{cat}")
        if not isinstance(names, list) or not names:
            print("  No results.")
            return
        print(f"\n  {len(names)} match(es):\n")
        for i, n in enumerate(names, 1):
            print(f"  {i:>3}. {n}")
        print()
        choice = input("  Enter number to get details (or Enter to quit): ").strip()
        if not choice:
            return
        try:
            chosen = names[int(choice) - 1]
        except (ValueError, IndexError):
            print("  Invalid choice.")
            return
        items = get(f"search/releasegroup/{urllib.parse.quote(chosen)}/{cat}")
        if not isinstance(items, list) or not items:
            print("  No details found.")
            return
        pick(items, show_files=args.files, download=args.download)
        return

    if not has_kv_filter:
        print("  Please provide at least one filter (--group, --handle, --repo, --cat, --date, --after, --before).")
        print("  For name-only search use:  assembly64 search \"name\"")
        return

    query = build_query(args)
    items = aql(query, limit=args.limit)
    if not items:
        print("  No results.")
        return
    pick(items, show_files=args.files, download=args.download)


def cmd_sid(args):
    enc   = urllib.parse.quote(args.query)
    names = get(f"search/releases/{enc}/18")
    if not isinstance(names, list) or not names:
        print("  No results.")
        return

    print(f"\n  {len(names)} match(es):\n")
    for i, n in enumerate(names, 1):
        print(f"  {i:>3}. {n}")
    print()
    choice = input("  Enter number to get details (or Enter to quit): ").strip()
    if not choice:
        return
    try:
        chosen = names[int(choice) - 1]
    except (ValueError, IndexError):
        print("  Invalid choice.")
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

    pick(items, show_files=args.files, download=args.download)


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


CAT_IDS = {
    "demos": 1, "games": 0, "graphics": 3, "music": 4,
    "discmags": 5, "tools": 8, "sid": 18, "hvsc": 18,
    "misc": 7, "intros": 11, "c128": 2, "bbs": 6, "charts": 9,
}


def resolve_cat(val):
    key = val.lower()
    if key in CAT_IDS:
        return CAT_IDS[key]
    try:
        return int(val)
    except ValueError:
        sys.exit(f"Unknown category '{val}'. Use a number or: {', '.join(CAT_IDS)}")


def add_common(sp):
    sp.add_argument("--group",   metavar="NAME",  help="Filter by group name")
    sp.add_argument("--handle",  metavar="NAME",  help="Filter by handle/scener")
    sp.add_argument("--repo",    metavar="REPO",  help=f"Filter by repo: {', '.join(sorted(REPOS))}")
    sp.add_argument("--cat",     metavar="CAT",   help=f"Filter by category: {', '.join(CATEGORIES)}")
    sp.add_argument("--date",    metavar="DATE",  help="Exact date: YYYYMMDD or YYYYMM or YYYY")
    sp.add_argument("--after",   metavar="DATE",  help="Released after: YYYYMMDD")
    sp.add_argument("--before",  metavar="DATE",  help="Released before: YYYYMMDD")
    sp.add_argument("--order",   choices=["asc", "desc"], help="Sort order (default: desc)")
    sp.add_argument("--limit",   type=int, default=50, metavar="N", help="Max results (default: 50)")
    sp.add_argument("--files",   action="store_true", help="Show file listing")
    sp.add_argument("--download",action="store_true", help="Download files to current directory")


def build_parser():
    p = argparse.ArgumentParser(
        prog="assembly64",
        description="C64 scene lookup via the Assembly64 API (hackerswithstyle.se/leet/)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Commands:
  search           Search by name or filters
  sid    <query>   Search HVSC SID music (category 18)
  cats             List all categories and repos

Name search (search/releases endpoint):
  assembly64 search "edge of disgrace"         searches CSDB demos (cat 1)
  assembly64 search "commando" --cat games     searches CSDB games (cat 0)
  assembly64 search "commando" --cat 0         same, using category ID
  assembly64 sid sanxion                       searches HVSC (cat 18)

Filter search (AQL, requires at least one --group/--handle/--repo/--cat/--date):
  --group    group name (e.g. fairlight, "Booze Design")
  --handle   scener handle (e.g. laxity)
  --repo     {', '.join(sorted(REPOS))}
  --cat      {', '.join(CATEGORIES)}
  --date     exact date YYYYMMDD / YYYYMM / YYYY
  --after    released after YYYYMMDD
  --before   released before YYYYMMDD
  --order    asc or desc
  --limit    max results (default: 50)
  --files    show file listing for selected item
  --download download file(s) to current directory

Examples:
  assembly64 search "edge of disgrace"
  assembly64 search "edge of disgrace" --download
  assembly64 search "commando" --cat games
  assembly64 search --group fairlight --order asc
  assembly64 search --group fairlight --after 20000101 --before 20101231
  assembly64 search --group "Booze Design" --cat demos
  assembly64 search --handle laxity --repo csdb
  assembly64 sid sanxion
  assembly64 sid sanxion --download
  assembly64 cats
        """
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="Search by name (CSDB demos) or AQL filters")
    s.add_argument("name", nargs="?", metavar="QUERY",
                   help="Name to search (uses search/releases, default cat: demos)")
    add_common(s)

    si = sub.add_parser("sid", help="Search HVSC SID music by tune name")
    si.add_argument("query", metavar="QUERY")
    si.add_argument("--after",    metavar="DATE", help="Released after YYYYMMDD")
    si.add_argument("--before",   metavar="DATE", help="Released before YYYYMMDD")
    si.add_argument("--order",    choices=["asc", "desc"], help="Sort order")
    si.add_argument("--limit",    type=int, default=50, metavar="N")
    si.add_argument("--files",    action="store_true")
    si.add_argument("--download", action="store_true")

    sub.add_parser("cats", help="List all categories")

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
    elif args.cmd == "cats":
        cmd_categories()


if __name__ == "__main__":
    main()
