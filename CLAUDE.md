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

movie_core.py                ← Actor, Project, NamingEngine, FFmpegEngine, PathHelper, TaskManager
movie_gui.py                 ← PyQt5 GUI (all UI + dialogs)
data.db                      ← SQLite (actors + projects + tasks)
icon.svg                     ← App icon
run.py                       ← Entry point
FilmCutter.spec              ← PyInstaller packaging (onedir, no console)

tmp/                         ← Runtime temp: concat segments + preview thumbnails (gitignored)
```

## Core (`movie_core.py`)

- **Actor / ActorManager** — SQLite-backed CRUD. Country codes: CHN, JAP, KOR, WEST, SLA, SEA, LTA.
- **Project / ProjectManager** — SQLite-backed CRUD. Slug format: `{Movie}.{Year}` or `{Movie}.{Year}.S01E01`. Projects can be created without actors; actors required at export time. `update()` accepts any key (dynamic fields like `country` supported).
- **NamingEngine** — Filename generation per v0 conventions: `gif_name`, `video_name`, `concat_name`, `image_name`.
- **FFmpegEngine** — `make_gif`, `cut_video`, `concat_segments` (`shell=True`). `_run` uses `Popen`; `kill()` stops the ffmpeg tree (`taskkill /F /T`); `target_path` exposed for cleanup/thumbnails.
- **PathHelper** — Auto-incrementing collision avoidance `(1)`, `(2)`, …; directory creation.
- **TaskManager** — SQLite CRUD over the `tasks` table (per-project task history & presets): create / update_status / get / list / delete / mark_stale_running.

## GUI (`movie_gui.py`)

- **MainWindow** — `QStackedWidget`: ProjectListPage ↔ WorkbenchPage. Sets app icon and Windows AppUserModelID.
- **ProjectListPage** — List / create / delete projects.
- **WorkbenchPage** — 3 tabs + top-bar buttons (编辑/归档/任务/退出):
  - **GIF** — Width/fps/colors (default 600/30/256), brightness/contrast/speed. 「保存当前任务」.
  - **Video Cut** — 单段→cut_video(`-`)；多段→concat(`~`)。时间段表格(多选)：Del/Ctrl+Z/Ctrl+C/Ctrl+D/Ctrl+↑↓ 快捷键、连续选区整体移动、时序校验。Options: -codec copy / -an / -aspect / -map。「保存当前任务」.
  - **Image Rename** — 批量重命名(auto-increment)；双击预览(←→导航)，Del 删除至回收站（右键菜单亦可）.
  - **归档整理** — 按 `[Country]` 前缀归类到 `{archive_root}/{Country}/{Actor}/[{Year}]{Movie}/`.
- **TaskListDialog** — 任务面板(任务按钮)：进行中/成功/失败/未进行；保存预设/恢复(载入完整状态)/终止(杀进程+清理)/删除(输出至回收站)。成功任务缩略图；双击预览(GIF动图/视频多帧拼图+「播放」调系统播放器)；`_ZoomImage` 自适应窗口+Ctrl+滚轮缩放+最大化.
- **ActorSelector** — Search, autocomplete, multi-select tags, inline actor creation, drag-to-reorder.
- **Dialogs** — ProjectDialog, ActorEditDialog, ArchiveDialog, TaskListDialog.

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

## Recent Changes (2026-06-29/30)

- **任务系统** — `tasks` 表 + `TaskManager`；`FFmpegEngine` 改 `Popen`，支持终止(`kill()`→`taskkill /F /T`)并清理未完成输出/拼接临时段。任务面板：四态、保存预设/恢复(完整状态载入)/终止/删除(输出移至回收站)；进入项目回收上次残留的「进行中」任务。
- **任务预览** — GIF 用 `QMovie` 播放动图；视频按时长分级抽帧拼图(<10s 单帧 / <1min 4帧 / <5min 6帧 / ≥5min 9帧)，后台生成+「正在生成」提示；「播放」调系统播放器(规避 Qt DirectShow 解码缺失)。`_ZoomImage` 自适应窗口 + Ctrl+滚轮缩放 + 最大化。
- **视频剪辑快捷键** — 多选(ExtendedSelection)；Del 删除 / Ctrl+Z 撤销 / Ctrl+C 复制 / Ctrl+D 新增 / Ctrl+↑↓ 连续选区整体移动。
- **图片预览** — Del 删除至回收站（右键菜单亦可）；无撤销。
- **命名 `_safe_name`** — 词间空格→`.`，标点旁空格去掉(避免 `,.`/`.,`)；冒号仍转中文冒号 `：`。
- **打包** — `FilmCutter.spec`(onedir, 无控制台)；`tmp/` 全目录忽略。

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
