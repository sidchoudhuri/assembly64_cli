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
usage: assembly64 [-h] {search,sid,cats} ...

C64 scene lookup via the Assembly64 API (hackerswithstyle.se/leet/)

positional arguments:
  {search,sid,cats}
    search           Search by name (CSDB demos) or AQL filters
    sid              Search HVSC SID music by tune name
    cats             List all categories

options:
  -h, --help         show this help message and exit

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
  --repo     c64com, c64orgintro, commodore, csdb, gamebase64, guybrush, hvsc, mayhem, oneload, pres, seuck, tapes, utape
  --cat      demos, games, graphics, music, discmags, tools, sid, hvsc, misc, intros, c128, bbs, charts
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
```
## Example: looking up the first 50 demos from Fairlight in descending order (newest first)
```
$ ./assembly64.py search --group fairlight --cat demos --order desc

  50 result(s):

    1. Qdor Qdor  [Fairlight  2026-02-13  1]
    2. The Hat  [Fairlight,Genesis Project  2026-02-01  1]
    3. Crazy People  [Fairlight  1991-11-01  1]
    4. Good Wheel 2025  [Fairlight  2025-01-01  37]
    5. Good Wheel 2025  [Fairlight  2025-12-24  1]
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
   21. Panta 50  [Fairlight  2024-01-01  37]
   22. Stars and Swipes  [Fairlight  2024-01-01  37]
   23. The Demo Coder  [Fairlight  2024-01-01  37]
   24. Stay Hungry  [Fairlight  2024-01-01  37]
   25. Demo Retox  [Fairlight  2024-01-01  37]
   26. Beergola 2024 Invite  [Fairlight  2024-01-01  37]
   27. The Night the Beergola Boys Turned Into the BeergolaPågarna  [Fairlight  2024-01-01  37]
   28. Eddie Demo  [Fairlight,Actual Cracking Force  37]
   29. In Business_ No One Can Hear You Scream  [Fairlight  2024-01-01  37]
   30. From the Deep of the North  [Fairlight  2024-01-01  37]
   31. 1337  [Fairlight  2024-01-01  37]
   32. The Ghost  [Genesis Project,Fairlight  2024-01-01  37]
   33. Me & Batman  [Fairlight,Triad  2024-01-01  37]
   34. Going 69 at 50  [Fairlight,Pretzel Logic,Lethargy,Atlantis,Bonzai  2024-01-01  37]
   35. The Krampuses Xmas Demo 2023  [Pretzel Logic,Fairlight  2023-01-01  37]
   36. The Night Before Christmas  [Fairlight  2023-01-01  37]
   37. Fairlight Wishes a Merry Christmas 2023  [Fairlight  2023-01-01  37]
   38. No Sprites  [Fairlight  2023-01-01  37]
   39. Xmas 2023 Compo Invite  [Fairlight  2023-01-01  37]
   40. Rushing  [Fairlight  2023-01-01  37]
   41. Eyes  [Fairlight  2023-01-01  37]
   42. Sir Epsilon  [Fairlight  2023-01-01  37]
   43. The Emergent Behavior of Hydrogen Oxide at Altitude A Case Study  [Fairlight  2023-01-01  37]
   44. Danko 50+  [Censor Design,Fairlight  2023-01-01  37]
   45. Danko 50  [Censor Design,Fairlight  2023-01-01  37]
   46. Bits and Flowers  [Fairlight  2023-01-01  37]
   47. The Space is Broken  [Fairlight  2023-01-01  37]
   48. The Scroll of Antonius  [Fairlight  2023-01-01  37]
   49. 76 Rastersplits  [Fairlight  2023-01-01  37]
   50. Looking for Atlantis  [Fairlight  2023-01-01  37]

  Enter number to view details (or Enter to quit): 1
--------------------------------------------------------------
  Qdor Qdor
--------------------------------------------------------------
  ID:            259366
  Category:      1
  Group:         Fairlight
  Handle:        hedning,Pal,redcrab,bepp,SkY,Norrland,Radiant,Pernod,Soya,Pitcher,Pantaloon,Stein Pedersen,Archmage,Frost,papademos,El Jefe,Trap,Trasher,Wix,Danko,Epsilon,tNG,Pastoelio,Bacchus,Trident,Qdor
  Year:          2026
  Released:      2026-02-13
--------------------------------------------------------------
$
```
## Example: downloading Qdor Qdor, the demo we found in the prevous example
```
$ ./assembly64.py search "qdor qdor" --download

  1 match(es):

    1. Qdor Qdor

  Enter number to get details (or Enter to quit): 1

  1 result(s):

    1. Qdor Qdor  [Fairlight  2026-02-13  1]

  Enter number to view details (or Enter to quit): 1
--------------------------------------------------------------
  Qdor Qdor
--------------------------------------------------------------
  ID:            259366
  Category:      1
  Group:         Fairlight
  Handle:        hedning,Pal,redcrab,bepp,SkY,Norrland,Radiant,Pernod,Soya,Pitcher,Pantaloon,Stein Pedersen,Archmage,Frost,papademos,El Jefe,Trap,Trasher,Wix,Danko,Epsilon,tNG,Pastoelio,Bacchus,Trident,Qdor
  Year:          2026
  Released:      2026-02-13

  Downloading qdor-qdor-75db9b39.d64 ... done  (174,848 bytes)  ->  qdor-qdor-75db9b39.d64
--------------------------------------------------------------
$ 
```
