# assembly64_cli
A command-line C64 scene lookup tool for the 1541 Ultimate II/II+L, Ultimate64/Ultimate64 Elite II, & Commodore 64 Ultimate powered by the [Assembly64 API](https://hackerswithstyle.se/leet/swagger-ui) & the [Ultimate 64 API](https://1541u-documentation.readthedocs.io/en/latest/api/api_calls.html).
- [Code notes](code_notes.md)
- [Examples](https://github.com/sidchoudhuri/assembly64_cli/blob/main/README.md#examples-1)

## Setup

Requires Python 3. No dependencies beyond the standard library.
```bash
git clone https://github.com/yourusername/assembly64.git
cd assembly64
chmod +x assembly64.py
```

Optionally add to your PATH:
```bash
cp assembly64.py ~/.local/bin/assembly64.py
```

## Usage
```
$ ./assembly64.py --fullhelp

ASSEMBLY64 CLI - C64 Scene Lookup Tool
APIS: hackerswithstyle.se/leet/
github.com/GideonZ/1541u-documentation

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
$
  ```
## Examples

### Looking up the first 50 demos from Fairlight in descending order (newest first)
<details>
  <summary>$ ./assembly64.py search --group fairlight --cat demos --order desc</summary>
  
```
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

  Showing 1-18 of 50  |  u/^=up  n/->=next
  Number to select,  r=rename  d=delete  q=quit: 1
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

  [1] Run on Ultimate (192.168.2.64)
  [2] Download to current directory
  [3] Quit

  Choose action (or Enter to quit): 3  
$
```
</details>

### Directly downloading Qdor Qdor, the demo we found in the prevous example
<details>
  <summary>$ ./assembly64.py search "qdor qdor" --download </summary>
  
```
  1 match(es):

    1. Qdor Qdor

  Showing 1-1 of 1  |  u/^=up
  Number to select,  r=rename  d=delete  q=quit: 1

  1 result(s):

    1. Qdor Qdor  [Fairlight  2026-02-13  1 (demos)]

  Showing 1-1 of 1  |  u/^=up
  Number to select,  r=rename  d=delete  q=quit: 1
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

  Download to:
  [1] Demos dir (/home/idun/demos)
  [2] Browse local filesystem
  [3] Current directory
  [4] Create folder: qdor-qdor/

  Choose (or Enter for current directory): 4
  Created folder: qdor-qdor/
  Downloading qdor-qdor-75db9b39.d64 ... done  (174,848 bytes)
  Saved  ->  qdor-qdor/qdor-qdor-75db9b39.d64
$ 
```
</details>

### Searching the demo charts and running a multi-disk demo using automatic disk swap timings 
<details>
  <summary>$ ./assembly64.py charts</summary>
  
```
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
   20. Wonderland XIV  []  *9.55

  Showing 1-20 of 200  |  n/->=next  p/<-=prev  q=quit

  Enter number to view details: 5
--------------------------------------------------------------
  1337
--------------------------------------------------------------
  ID:              242855
  Category:        1 (demos)
  Rating:          9.6748466257669
--------------------------------------------------------------

  Flip info available -- 3 disks with auto-flip timings.

  Files:
      1. fairlight-1337-58679b69-a.d64  (196,608 bytes)
      2. fairlight-1337-58679b69-b.d64  (196,608 bytes)
      3. fairlight-1337-58679b69-c.d64  (196,608 bytes)
      4. flip-info.txt  (98 bytes)

  [1] Run on Ultimate (192.168.2.32)
  [2] Run with auto disk flip (192.168.2.32)
  [3] Download to current directory
  [4] Quit

  Choose action (or Enter to quit): 2

  Multi-disk release -- 3 disk image(s):
    1. fairlight-1337-58679b69-a.d64  (196,608 bytes)
    2. fairlight-1337-58679b69-b.d64  (196,608 bytes)
    3. fairlight-1337-58679b69-c.d64  (196,608 bytes)

  Downloading all disks...
  Fetching fairlight-1337-58679b69-a.d64 ... done  (196,608 bytes)
  Fetching fairlight-1337-58679b69-b.d64 ... done  (196,608 bytes)
  Fetching fairlight-1337-58679b69-c.d64 ... done  (196,608 bytes)
  Uploading and mounting fairlight-1337-58679b69-a.d64 ... done  -> /Temp/temp0005
  Resetting machine ... done
  Injecting LOAD"*",8,1 + RUN ...
  Waiting for load to complete ... done  (3713)
  Load detection took 6.2s

  Press Enter to flip immediately, q+Enter to stop.
  Auto-flip: disk 2 (fairlight-1337-58679b69-b.d64) in 0m 01s ...
  Auto-flip to disk 2: fairlight-1337-58679b69-b.d64
  Mounting fairlight-1337-58679b69-b.d64 on drive A: ... done  (200)
  Auto-flip: disk 3 (fairlight-1337-58679b69-c.d64) in 0m 01s ...
  Auto-flip to disk 3: fairlight-1337-58679b69-c.d64
  Mounting fairlight-1337-58679b69-c.d64 on drive A: ... done  (200)

  All disks played.
$ 
```
</details>

### Using the Remote File Browser to upload a directory to the Ultimate file system
<details>
  <summary>$ assembly64 remote</summary>
  
```
--------------------------------------------------------------
  Ultimate-64-II-439E67: /
--------------------------------------------------------------
    1. [DIR]  SD/
    2. [DIR]  Flash/
    3. [DIR]  Temp/
    4. [DIR]  USB0/

  Showing 1-4 of 4  |
  Number to select,  u=upload  q=quit: 1

  Selected: /SD/
  45 dirs, 8 files, ~578 KB shown

  [1] Enter directory
  [2] Download all
  [3] Go back

  Choose: 1
--------------------------------------------------------------
  Ultimate-64-II-439E67: /SD/
--------------------------------------------------------------
    1. [DIR]  #/
    2. [DIR]  _arm2sid/
    3. [DIR]  _BASIC/
    4. [DIR]  _bbs/
    5. [DIR]  _carts/
    6. [DIR]  _D81/
    7. [DIR]  _demos/
    8. [DIR]  _favs/
    9. [DIR]  _G64/
   10. [DIR]  _GEOS/
   11. [DIR]  _Kawari/
   12. [DIR]  _music/
   13. [DIR]  _Pocketwriter64/
   14. [DIR]  _reu_nuvies/
   15. [DIR]  _tape/
   16. [DIR]  _tools/
   17. [DIR]  _Ultimate64/
   18. [DIR]  _updates/
   19. [DIR]  _vic20/

  Showing 1-53 of 53  |  ^=up
  Number to select,  m=mkdir  r=rename  d=delete  u=upload  q=quit: u

  Upload:
  [1] Enter local path
  [2] Browse local filesystem

  Choose: 2
--------------------------------------------------------------
  Local: /home/idun
--------------------------------------------------------------
    1. [DIR]  code/
    2. [DIR]  demos/
    3. [DIR]  games/
    4. [DIR]  idun-base/
    5. [DIR]  idun-sys/
    6. [DIR]  pics/
    7. [DIR]  sids/

  Showing 1-39 of 39  |  ^=up
  Number to select,  m=mkdir  r=rename  d=delete  q=quit: 2

  Selected: demos/
  8 dirs, 46 files, ~4.1 MB

  [1] Enter directory
  [2] Upload all to /SD/
  [3] Go back

  Choose: 1
--------------------------------------------------------------
  Local: /home/idun/demos
--------------------------------------------------------------
    1. [DIR]  edge-of-disgrace/
    2. [DIR]  grey/
    3. [DIR]  lifecycle/
    4. [DIR]  next-level/
    5. [DIR]  nine/
    6. [DIR]  signal-carnival/
    7. [DIR]  sonic-the-hedgehog-v12-5/
    8. [DIR]  wonderland-xiii/
    9. amiga-intro.prg  (6,912 bytes)
   10. CopperBooze.prg  (19,593 bytes)
   11. flip-info.txt.bak  (98 bytes)
   12. pac_grey.prg  (38,150 bytes)
   13. rfovdc2.d64  (174,848 bytes)
   14. scanandspin.d64  (174,848 bytes)

  Showing 1-14 of 14  |  ^=up
  Number to select,  m=mkdir  r=rename  d=delete  q=quit: 2

  Selected: grey/
  3 files, 43 KB

  [1] Enter directory
  [2] Upload all to /SD/
  [3] Go back

  Choose: 2
  Uploading grey/ -> /SD/grey/ ...
    grey/pac_grey.prg ... done (38,150 bytes)
    grey/walking_in_the_sunshine.prg ... done (4,096 bytes)
    grey/walking_in_the_sunshine.sid ... done (1,558 bytes)
  Done.
--------------------------------------------------------------
  Local: /home/idun/demos
--------------------------------------------------------------
    1. [DIR]  edge-of-disgrace/
    2. [DIR]  grey/
    3. [DIR]  lifecycle/
    4. [DIR]  next-level/
    5. [DIR]  nine/
    6. [DIR]  signal-carnival/
    7. [DIR]  sonic-the-hedgehog-v12-5/
    8. [DIR]  wonderland-xiii/
    9. amiga-intro.prg  (6,912 bytes)
   10. CopperBooze.prg  (19,593 bytes)
   11. flip-info.txt.bak  (98 bytes)
   12. pac_grey.prg  (38,150 bytes)
   13. rfovdc2.d64  (174,848 bytes)
   14. scanandspin.d64  (174,848 bytes)

  Showing 1-14 of 14  |  ^=up
  Number to select,  m=mkdir  r=rename  d=delete  q=quit: q
--------------------------------------------------------------
  Ultimate-64-II-439E67: /SD/
--------------------------------------------------------------
    1. [DIR]  #/
    2. [DIR]  _arm2sid/
    3. [DIR]  _BASIC/
    4. [DIR]  _bbs/
    5. [DIR]  _carts/
    6. [DIR]  _D81/
    7. [DIR]  _demos/
    8. [DIR]  _favs/
    9. [DIR]  _G64/
   10. [DIR]  _GEOS/
   11. [DIR]  _Kawari/
   12. [DIR]  _music/
   13. [DIR]  _Pocketwriter64/
   14. [DIR]  _reu_nuvies/
   15. [DIR]  _tape/
   16. [DIR]  _tools/
   17. [DIR]  _Ultimate64/
   18. [DIR]  _updates/
   19. [DIR]  _vic20/
   20. [DIR]  grey/

  Showing 1-54 of 54  |  ^=up
  Number to select,  m=mkdir  r=rename  d=delete  u=upload  q=quit: d
  Number to delete: 20
  /SD/grey/ is not empty (3 items).
  Delete recursively? [y/N]: y
  Done.
--------------------------------------------------------------
  Ultimate-64-II-439E67: /SD/
--------------------------------------------------------------
    1. [DIR]  #/
    2. [DIR]  _arm2sid/
    3. [DIR]  _BASIC/
    4. [DIR]  _bbs/
    5. [DIR]  _carts/
    6. [DIR]  _D81/
    7. [DIR]  _demos/
    8. [DIR]  _favs/
    9. [DIR]  _G64/
   10. [DIR]  _GEOS/
   11. [DIR]  _Kawari/
   12. [DIR]  _music/
   13. [DIR]  _Pocketwriter64/
   14. [DIR]  _reu_nuvies/
   15. [DIR]  _tape/
   16. [DIR]  _tools/
   17. [DIR]  _Ultimate64/
   18. [DIR]  _updates/
   19. [DIR]  _vic20/

  Showing 1-53 of 53  |  ^=up
  Number to select,  m=mkdir  r=rename  d=delete  u=upload  q=quit: q
$
```
</details>

### Interactively building a search query in the Category Browser

<details>
  <summary>$ assembly64 cats</summary>
  
```
--------------------------------------------------------------
  CATEGORIES
--------------------------------------------------------------
    1. c64com  (2 categories)
    2. c64orgintro  (1 categories)
    3. commodore  (5 categories)
    4. csdb  (12 categories)
    5. gamebase  (1 categories)
    6. guybrush  (7 categories)
    7. hvsc  (4 categories)
    8. mayhem  (1 categories)
    9. oneload  (1 categories)
   10. pres  (2 categories)
   11. seuck  (1 categories)
   12. tapes  (1 categories)
   13. utape  (1 categories)
--------------------------------------------------------------

  Enter number to browse category type (or Enter to quit): 4
--------------------------------------------------------------
    csdb
--------------------------------------------------------------
    1. [  0]  CSDB games  (games)
    2. [  1]  CSDB demos  (demos)
    3. [  2]  CSDB 128  (c128stuff)
    4. [  3]  CSDB graphics  (graphics)
    5. [  4]  CSDB music  (music)
    6. [  5]  CSDB discmags  (discmags)
    7. [  6]  CSDB bbs  (bbs)
    8. [  7]  CSDB misc  (c64misc)
    9. [  8]  CSDB tools  (tools)
   10. [  9]  CSDB charts  (charts)
   11. [ 10]  CSDB easyflash  (easyflash)
   12. [ 25]  CSDB reu  (reu)

  Showing 1-12 of 12  |
  Number to select,  q=quit: 4

  CSDB graphics
  Query: category:graphics
  n=name  h=handle  g=group
  a=after  b=before  o=order  c=clear
  Enter=search  q=quit
  Filter: g
  Group: m0nde

  CSDB graphics
  Query: category:graphics group:m0nde
  n=name  h=handle  g=group
  a=after  b=before  o=order  c=clear
  Enter=search  q=quit
  Filter: 
  Searching ...

  Query: category:graphics group:m0nde
  Showing 1-1

  [1] View results
  [4] Refine query
  q=quit

  Choose: 1

  1 result(s):

    1. Me  [m0nde  2024-11-06  3 (graphics)]

  Showing 1-1 of 1  |
  Number to select,  q=quit: 1
--------------------------------------------------------------
  Me
--------------------------------------------------------------
  ID:              247364
  Category:        3 (graphics)
  Group:           m0nde
  Year:            2024
  Released:        2024-11-06
--------------------------------------------------------------

  Files:
      1. me.d64  (174,848 bytes)

  [1] Run on Ultimate (192.168.2.64)
  [2] Download to current directory
  [3] Quit

  Choose action (or Enter to quit): 1
  Downloading me.d64 ... done  (174,848 bytes)
  Uploading and mounting me.d64 ... done  -> /Temp/temp0006
  Resetting machine ... done
  Injecting LOAD"*",8,1 + RUN ...
  Waiting for load to complete ... done  (3110)
  Load detection took 4.2s
  Searching ...

  Query: category:graphics group:m0nde
  Showing 1-1

  [1] View results
  [4] Refine query
  q=quit

  Choose: q 
$ 
```
</details>
