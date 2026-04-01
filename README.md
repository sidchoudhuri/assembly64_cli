### Coming Soon!
1. automatic disk change for multi-disk demos via flipdisk.txt
2. multiple Ultimate devices
3. favorites
### [Code notes](code_notes.md)
---
# assembly64_cli
A command-line C64 scene lookup tool powered by the [Assembly64 API](https://hackerswithstyle.se/leet/swagger-ui).

## Setup

Requires Python 3. No dependencies beyond the standard library.
```bash
git clone https://github.com/yourusername/assembly64.git
cd assembly64
chmod +x assembly64.py
```

Optionally add to your PATH:
```bash
cp assembly64.py ~/.local/bin/assembly64
```

## Usage
```
$ ./assembly64.py 
usage: assembly64 [-h]
                  {search,sid,charts,presets,cats,run,mount,reset,reboot,config} ...

C64 scene lookup via the Assembly64 API (hackerswithstyle.se/leet/)

positional arguments:
  {search,sid,charts,presets,cats,run,mount,reset,reboot,config}
    search              Search by name or AQL filters
    sid                 Search HVSC SID music by tune name
    charts              Browse top charts
    presets             Browse AQL query presets
    cats                Browse categories
    run                 Run a local file or directory on the Ultimate
    mount               Mount a local disk image on the Ultimate (no reset)
    reset               Reset the C64
    reboot              Reboot the C64 (reinitialises cartridge + reset)
    config              Show or set saved configuration

options:
  -h, --help            show this help message and exit

Commands:
  search  [query]  Search by name or AQL filters
  sid     <query>  Search HVSC SID music
  charts  [name]   Browse top charts
  presets [type]   Browse AQL query presets
  cats             List all categories
  mount   <file>   Mount a local disk image on drive A (no reset or autorun)
  run     <path>   Run a local file or directory on the Ultimate
                   Supports: .prg .crt .sid .d64 .d71 .d81 .g64 .g71
                   For directories: auto-detects flip-info.txt/.lst/.vfl
                   for multi-disk ordering and auto-flip timings
  reboot           Reboot the C64 (reinitialises cartridge + reset)
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
  and mounts the next disk automatically.
  During auto-flip: Enter=flip now, q+Enter=stop sequence

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
  --repo     c64com, c64orgintro, commodore, csdb, gamebase64, guybrush, hvsc, mayhem, oneload, pres, seuck, tapes, utape
  --cat      demos, games, graphics, music, discmags, tools, sid, hvsc, misc, intros, c128, bbs, charts
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
$ 
```
## Example: looking up the first 50 demos from Fairlight in descending order (newest first)
```
sid@sid-macbookprom4 run % ./assembly64.py search --group fairlight --cat demos --order desc

  50 result(s):

    1. Qdor Qdor  [Fairlight  2026-02-13  1 (demos)]
    2. The Hat  [Fairlight,Genesis Project  2026-02-01  1 (demos)]
    3. Crazy People  [Fairlight  1991-11-01  1 (demos)]
    4. Good Wheel 2025  [Fairlight  2025-01-01  37]
    5. Good Wheel 2025  [Fairlight  2025-12-24  1 (demos)]
    6. A Fayre Glow  [Fairlight  2025-01-01  37]
    7. Soya 50yo  [Fairlight  2025-01-01  37]
    8. The Safety Dudes  [Fairlight  2025-01-01  37]
    9. Fjälldata 2026 Invite  [Genesis Project,Fairlight  2025-01-01  37]
   10. CashesCash#1  [Fairlight,Triad  2025-01-01  37]
   11. Beergola Bros 2025 Fuel Like a Casserole  [Fairlight  2025-01-01  37]
   12. Zone 5  [Fairlight  2025-01-01  37]
   13. D011 Mayhem  [Fairlight  2025-01-01  37]
   14. Just Our Quality Stuff Again  [Fairlight  1990-01-01  37]
   15. The Trip  [Fairlight  2025-01-01  37]
   16. Edison 2025 Invite  [Fairlight  2025-01-01  37]
   17. The Fair Light  [Fairlight  2025-01-01  37]
   18. OTech People III  [Fairlight  2025-01-01  37]
   19. The Raster Bar  [Fairlight  2024-01-01  37]
   20. Xmas 2024  [Fairlight  2024-01-01  37]

  Showing 1-20 of 50  |  n/→=next  p/←=prev  q=quit

  Enter number to view details: 1
--------------------------------------------------------------
  Qdor Qdor
--------------------------------------------------------------
  ID:              259366
  Category:        1 (demos)
  Group:           Fairlight
  Handle:          hedning,Pal,redcrab,bepp,SkY,Norrland,Radiant,Pernod,Soya,Pitcher,Pantaloon,Stein Pedersen,Archmage,Frost,papademos,El Jefe,Trap,Trasher,Wix,Danko,Epsilon,tNG,Pastoelio,Bacchus,Trident,Qdor
  Year:            2026
  Released:        2026-02-13
--------------------------------------------------------------

  Files:
      1. qdor-qdor-75db9b39.d64  (174,848 bytes)

  [1] Run on Ultimate (192.168.2.32)
  [2] Download to current directory
  [3] Quit

  Choose action (or Enter to quit):               
  
$
```
## Example: directly downloading Qdor Qdor, the demo we found in the prevous example
```
$ ./assembly64.py search "qdor qdor" --download                    

  1 match(es):

    1. Qdor Qdor

  Showing 1-1 of 1

  Enter number to get details: 1

  1 result(s):

    1. Qdor Qdor  [Fairlight  2026-02-13  1 (demos)]

  Showing 1-1 of 1

  Enter number to view details: 1
--------------------------------------------------------------
  Qdor Qdor
--------------------------------------------------------------
  ID:              259366
  Category:        1 (demos)
  Group:           Fairlight
  Handle:          hedning,Pal,redcrab,bepp,SkY,Norrland,Radiant,Pernod,Soya,Pitcher,Pantaloon,Stein Pedersen,Archmage,Frost,papademos,El Jefe,Trap,Trasher,Wix,Danko,Epsilon,tNG,Pastoelio,Bacchus,Trident,Qdor
  Year:            2026
  Released:        2026-02-13
--------------------------------------------------------------
  Downloading qdor-qdor-75db9b39.d64 ... done  (174,848 bytes)
  Saved  ->  qdor-qdor-75db9b39.d64
$ 
```
## Example: Searching the demo charts and running a multi-disk demo on the C64 Ultimate
```
$ ./assembly64.py charts                       
--------------------------------------------------------------
  AVAILABLE CHARTS
--------------------------------------------------------------
    1. DEMOS
    2. ONEFILE DEMOS
    3. GAMES
    4. MUSIC
    5. GRAPHICS
    6. TOOLS
--------------------------------------------------------------

  Enter number to view chart (or Enter to quit): 1
--------------------------------------------------------------
  CHART: DEMOS
--------------------------------------------------------------
    1. Aloft  []  *9.75
    2. The Hat  []  *9.75
    3. Next Level  []  *9.73
    4. We Are The Anomaly  []  *9.68
    5. 1337  []  *9.67
    6. Codeboys & Endians  []  *9.67
    7. Mojo  []  *9.65
    8. Coma Light 13  []  *9.64
    9. The Violators  []  *9.64
   10. Edge of Disgrace  []  *9.62
   11. Comaland 100%  []  *9.62
   12. Bromance  []  *9.60
   13. Uncensored  []  *9.60
   14. No Bounds  []  *9.59
   15. Fitty  []  *9.58
   16. The Ghost  []  *9.57
   17. What Is The Matrix 2  []  *9.57
   18. Unboxed  []  *9.56
   19. Lifecycle  []  *9.55
   20. The XFile  []  *9.55

  Showing 1-20 of 200  |  n/→=next  p/←=prev  q=quit

  Enter number to view details: 5
--------------------------------------------------------------
  1337
--------------------------------------------------------------
  ID:              242855
  Category:        1 (demos)
  Rating:          9.6748466257669
--------------------------------------------------------------

  Files:
      1. fairlight-1337-58679b69-a.d64  (196,608 bytes)
      2. fairlight-1337-58679b69-b.d64  (196,608 bytes)
      3. fairlight-1337-58679b69-c.d64  (196,608 bytes)
      4. flip-info.txt  (98 bytes)

  [1] Run on Ultimate (192.168.2.32)
  [2] Download to current directory
  [3] Quit

  Choose action (or Enter to quit): 1

  Multi-disk release — 3 disk image(s):
    1. fairlight-1337-58679b69-a.d64  (196,608 bytes)
    2. fairlight-1337-58679b69-b.d64  (196,608 bytes)
    3. fairlight-1337-58679b69-c.d64  (196,608 bytes)

  Downloading all disks...
  Fetching fairlight-1337-58679b69-a.d64 ... done  (196,608 bytes)
  Fetching fairlight-1337-58679b69-b.d64 ... done  (196,608 bytes)
  Fetching fairlight-1337-58679b69-c.d64 ... done  (196,608 bytes)
  Mounting fairlight-1337-58679b69-a.d64 on drive A: ... done  (200)
  Resetting machine ... done
  Waiting for BASIC prompt ... done
  Injecting LOAD"*",8,1 + RUN ...

  Press Enter when the demo asks for the next disk,
  type a disk number to mount a specific one, or q to quit.
  [Enter=disk 2, number, or q]: 
  Mounting fairlight-1337-58679b69-b.d64 on drive A: ... done  (200)
  [Enter=disk 3, number, or q]: 
  Mounting fairlight-1337-58679b69-c.d64 on drive A: ... done  (200)
$ 
```
