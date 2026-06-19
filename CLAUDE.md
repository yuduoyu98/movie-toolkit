# CLAUDE.md

Project documentation for Claude Code.

## Background

PyQt5 GUI to replace v0 CLI scripts for video editing. v0 scripts are the source of truth for naming conventions and FFmpeg patterns.

## Run

```bash
python movie_gui.py
```

Requires: Python 3, PyQt5, FFmpeg on PATH. Virtual environment at `.venv`.

## File Map

```
v0/                          ← Original CLI scripts (naming & FFmpeg source of truth)
  video_cutter.py            ← Single segment cut
  video_cutter_segment.py    ← Multi-segment concat
  gif_maker.py               ← GIF generation
  correct.py                 ← Image batch rename
  classify.py                ← Archive / classify
  movie.ini                  ← Legacy config

movie_core.py                ← Actor, Project, NamingEngine, FFmpegEngine, PathHelper
movie_gui.py                 ← PyQt5 GUI (all UI + dialogs)
data.db                      ← SQLite (actors + projects)
icon.svg                     ← App icon
run.py                       ← Entry point

tmp/concat/                  ← Temp segments for concat (cleaned before each run)
```

## Core (`movie_core.py`)

- **Actor / ActorManager** — SQLite-backed CRUD. Country codes: CHN, JAP, KOR, WEST, SLA, SEA, LTA.
- **Project / ProjectManager** — SQLite-backed CRUD. Slug format: `{Movie}.{Year}` or `{Movie}.{Year}.S01E01`. Projects can be created without actors; actors required at export time. `update()` accepts any key (dynamic fields like `country` supported).
- **NamingEngine** — Filename generation per v0 conventions: `gif_name`, `video_name`, `concat_name`, `image_name`.
- **FFmpegEngine** — Subprocess wrappers: `make_gif`, `cut_video`, `concat_segments`. All use `shell=True`.
- **PathHelper** — Auto-incrementing collision avoidance `(1)`, `(2)`, …; directory creation.

## GUI (`movie_gui.py`)

- **MainWindow** — `QStackedWidget`: ProjectListPage ↔ WorkbenchPage. Sets app icon and Windows AppUserModelID.
- **ProjectListPage** — List / create / delete projects.
- **WorkbenchPage** — 3 tabs + archive dialog:
  - **GIF** — Width/fps/colors (default 600/30/256), brightness/contrast/speed filters.
  - **Video Cut** — Unified tab: single segment → cut_video (`-` separator in filename); multi-segment → concat (`~` separator). Segment table with ▲▼ reorder, ⏃ sort, time-sequence validation. Options: -codec copy / -an / -aspect / -map.
  - **Image Rename** — Scan directory, filter by prefix, checkbox select, batch rename with auto-increment (skips existing numbered files). Lazy thumbnail loading. Double-click preview with ←→ navigation.
  - **归档整理** — Button in top bar. ArchiveDialog: scan files for `[Country]` prefix, classify into `{archive_root}/{Country}/{Actor}/[{Year}]{Movie}/` structure.
- **ActorSelector** — Search, autocomplete, multi-select tags, inline actor creation, drag-to-reorder.
- **Dialogs** — ProjectDialog, ActorEditDialog, ArchiveDialog.

## Naming Conventions

Spaces in names become dots. Timestamps replace `:` with `.`. Multiple actors joined with `+`.

| Type | Format |
|------|--------|
| **GIF** | `[Country]Actor.Name.中文名 » Movie.Name.Year(1).gif` |
| **Video** | `[Country]Actor.Name.中文名 » Movie.Name.Year » HH.mm.ss-HH.mm.ss.mp4` |
| **Series** | `[Country]Actor.Name.中文名 » Movie.Name.Year.S01E01 » HH.mm.ss-HH.mm.ss.mp4` |
| **Concat** | Same as video but `~` between timestamps |
| **Image** | `[Country]Actor.Name.中文名 » Movie.Name.Year-1.png` |

## FFmpeg Patterns

**Video cut:**
```
ffmpeg -y -ss {start} -to {end} -accurate_seek -i "{source}" {opts} -avoid_negative_ts 1 "{output}"
```
Opts: `-codec copy`, `-an`, `-aspect 16:9`, `-map 0:v:0 -map 0:a:{n}`.

**GIF** (single-pass split+palettegen+paletteuse):
```
ffmpeg -y -ss {start} -to {end} -i "{source}" -vf "{filters}" -loop 0 "{output}"
```
Filters: `eq=contrast={c}:brightness={b},setpts={speed}*PTS,fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors={n}[p];[s1][p]paletteuse=dither=bayer`

**Concat:** Cut segments to `tmp/concat/{i}.mp4`, write `filelist.txt`, then:
```
ffmpeg -y -f concat -i "tmp/concat/filelist.txt" -c copy "{output}"
```

## Recent Changes (2026-06-19/20)

- **Tabs merged** — Video Cut + Concat into one "视频剪辑" tab. Single segment → `-` separator; multi-segment → `~` separator.
- **Parallel tasks** — GIF、video、concat run in independent threads; log tagged `[GIF]`/`[视频]`/`[拼接]`; no button disable.
- **Dark mode** — `QPalette`-based toggle (🌙/☀), auto-detect 18:00–05:59, persisted to `.filmcutter_config.json`.
- **Project list** — Search box, bold `[Year]Name` format, per-row edit/delete, small-window startup → maximize on enter.
- **Actor sync** — `_save_tab_actors` uses triggering tab as truth (not union). `set_project_actor_ids` syncs `project_actor_ids` + `selected_actor_ids` + completer. Selection ≠ unbinding.
- **Image rename** — Regex `^\[[A-Z]{2,4}\]` detects already-renamed files. Status column: green new name / orange "未重命名" / gray "已重命名". Search auto-selects matching non-renamed files. Sort by time/name with ↑↓ toggle. jpg/png filter checkboxes. "隐藏已重命名的图片" default on.
- **State persistence** — Workbench parameters (segments, GIF options, actors, tab) saved to `projects.state` TEXT column (JSON). `ProjectManager.save_state` / `load_state`.
- **Video segments** — Copy selected rows in import format (`start,end` per line). Error shown as red ✗ with tooltip.
- **`_safe_name`** — Replaces `:` with `：` (Chinese colon), strips surrounding spaces first.

## Known Differences from v0

- GIF: v0 uses two-pass palette (separate palettegen → paletteuse); core uses single-pass filter graph. Functionally equivalent.
- Image rename: v0 scans files starting with source video keyword; GUI scans all images, pre-checks matching ones, supports search filter.
- `PathHelper.get_nonconflicting_filename` handles the no-index case that v0's version doesn't.
