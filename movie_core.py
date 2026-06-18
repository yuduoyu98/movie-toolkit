"""
Movie Toolkit Core
项目制 + 演员库：项目ID只用影视名，创建时可无演员，剪辑时强制要求演员
"""
import re
import subprocess
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict


class Actor:
    """演员数据模型"""

    def __init__(self, name: str, country: str, chn_name: Optional[str] = None, id: Optional[int] = None):
        self.id = id
        self.name = name
        self.country = country
        self.chn_name = chn_name

    @classmethod
    def create(cls, name: str, country: str, chn_name: Optional[str] = None) -> "Actor":
        return cls(name, country, chn_name)

    @property
    def display_name(self) -> str:
        if self.chn_name:
            return f"{self.name} ({self.chn_name}) [{self.country}]"
        return f"{self.name} [{self.country}]"

    @property
    def short_name(self) -> str:
        if self.chn_name:
            return f"{self.name} ({self.chn_name})"
        return self.name

    @property
    def search_keys(self) -> List[str]:
        keys = [self.name.lower()]
        if self.chn_name:
            keys.append(self.chn_name.lower())
        return keys

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "chn_name": self.chn_name,
        }


class ActorManager:
    """演员库管理，使用 SQLite 存储"""

    def __init__(self, db_path: str = "data.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        # 检测旧 schema（无 id 列或有 created_at）→ 删表重建
        cursor.execute("PRAGMA table_info(actors)")
        cols = [row[1] for row in cursor.fetchall()]
        if cols and ("id" not in cols or "created_at" in cols):
            cursor.execute("DROP TABLE actors")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS actors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country TEXT NOT NULL,
                name TEXT NOT NULL,
                chn_name TEXT,
                UNIQUE(country, name)
            )
        """)
        self.conn.commit()

    def list_actors(self) -> List[Actor]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM actors ORDER BY LOWER(name)")
        return [self._row_to_actor(row) for row in cursor.fetchall()]

    def get(self, actor_id: int) -> Optional[Actor]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM actors WHERE id = ?", (actor_id,))
        row = cursor.fetchone()
        return self._row_to_actor(row) if row else None

    def get_by_country_name(self, country: str, name: str) -> Optional[Actor]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM actors WHERE country = ? AND name = ?", (country, name))
        row = cursor.fetchone()
        return self._row_to_actor(row) if row else None

    def find_by_name(self, name: str) -> Optional[Actor]:
        name = name.strip()
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM actors WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            return self._row_to_actor(row)
        cursor.execute("SELECT * FROM actors WHERE chn_name = ?", (name,))
        row = cursor.fetchone()
        return self._row_to_actor(row) if row else None

    def search(self, keyword: str) -> List[Actor]:
        keyword = keyword.strip().lower()
        if not keyword:
            return []
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM actors WHERE LOWER(name) LIKE ? OR LOWER(chn_name) LIKE ? ORDER BY LOWER(name)",
            (f"%{keyword}%", f"%{keyword}%")
        )
        return [self._row_to_actor(row) for row in cursor.fetchall()]

    def add(self, actor: Actor):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO actors (country, name, chn_name) VALUES (?, ?, ?) "
            "ON CONFLICT(country, name) DO UPDATE SET chn_name=excluded.chn_name",
            (actor.country, actor.name, actor.chn_name)
        )
        actor.id = cursor.lastrowid
        self.conn.commit()

    def delete(self, actor_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM actors WHERE id = ?", (actor_id,))
        self.conn.commit()

    def all_names(self) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT name, chn_name FROM actors")
        names = []
        for row in cursor.fetchall():
            names.append(row["name"])
            if row["chn_name"]:
                names.append(row["chn_name"])
        return names

    def _row_to_actor(self, row) -> Actor:
        return Actor(
            id=row["id"],
            name=row["name"],
            country=row["country"],
            chn_name=row["chn_name"],
        )

    def close(self):
        if self.conn:
            self.conn.close()

    def __del__(self):
        self.close()


class Project:
    """影片项目，项目ID只用影视名+年份，创建时可无演员"""

    def __init__(self, data: dict):
        self._data = data
        self._actor_display_names: Optional[List[str]] = None

    @classmethod
    def create(cls, movie: str, year: int, source_file_path: str,
               target_base_path: str, is_series: bool = False,
               season: Optional[int] = None) -> "Project":
        data = {
            "id": None,  # assigned by DB
            "slug": cls._make_slug(movie, year, is_series, season),
            "movie": movie,
            "year": year,
            "is_series": is_series,
            "season": season,
            "source_file_path": source_file_path,
            "target_base_path": target_base_path,
        }
        return cls(data)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            self._data[k] = v
        self._data["updated_at"] = datetime.now().isoformat()

    def resolve_actors(self, actor_manager: ActorManager):
        names = []
        for aid in self.actor_ids:
            actor = actor_manager.get(aid)
            if actor:
                display = actor.name.replace(' ', '.')
                if actor.chn_name:
                    display = f"{display}.{actor.chn_name}"
                names.append(display)
        self._actor_display_names = names

    @staticmethod
    def _make_slug(movie: str, year: int, is_series: bool, season: Optional[int]) -> str:
        """项目文本标识，用于文件名"""
        base = f"{movie}.{year}"
        if is_series and season is not None:
            base += f".S{season:02d}"
        base = re.sub(r'[\\/:*?"<>|]', '_', base)
        return base

    @property
    def id(self) -> Optional[int]: return self._data.get("id")
    @property
    def slug(self) -> str: return self._data["slug"]
    @property
    def movie(self) -> str: return self._data["movie"]
    @property
    def year(self) -> int: return self._data["year"]
    @property
    def season(self) -> Optional[int]: return self._data.get("season")
    @property
    def is_series(self) -> bool: return self._data.get("is_series", False)
    @property
    def source_file_path(self) -> str: return self._data["source_file_path"]
    @property
    def target_base_path(self) -> str: return self._data["target_base_path"]
    @property
    def country(self) -> str: return self._data.get("country", "")  # 导出时动态设置，不存 DB

    @property
    def actor_ids(self) -> List[int]:
        val = self._data.get("actor", [])
        if isinstance(val, int):
            return [val]
        return val or []

    def set_actor_ids(self, ids: List[int]):
        self._data["actor"] = ids

    @property
    def actor_display_names(self) -> List[str]:
        if self._actor_display_names is not None:
            return self._actor_display_names
        return [str(a) for a in self.actor_ids]

    @property
    def display_name(self) -> str:
        actors = "+".join(self.actor_display_names) if self.actor_display_names else "Unknown"
        se = ""
        if self.is_series and self.season is not None:
            se = f".S{self.season:02d}"
        return f"{actors}{se} » {self.movie}.{self.year}"

    @property
    def short_name(self) -> str:
        """列表显示：[年份]名称（不含演员）"""
        se = ""
        if self.is_series and self.season is not None:
            se = f" S{self.season:02d}"
        return f"[{self.year}]{self.movie}{se}"


class ProjectManager:
    def __init__(self, db_path: str = "data.db", actor_manager: Optional[ActorManager] = None):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_db()
        self.actor_manager = actor_manager

    def _init_db(self):
        cursor = self.conn.cursor()

        # 检测旧 schema（有 country / created_at / updated_at 列）→ 删表重建
        cursor.execute("PRAGMA table_info(projects)")
        cols = [row[1] for row in cursor.fetchall()]
        if cols and ("country" in cols or "updated_at" in cols):
            cursor.execute("DROP TABLE projects")
            cursor.execute("DROP TABLE IF EXISTS project_actors")

        # 项目表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                movie TEXT NOT NULL,
                year INTEGER NOT NULL,
                is_series INTEGER NOT NULL DEFAULT 0,
                season INTEGER,
                source_file_path TEXT NOT NULL,
                target_base_path TEXT NOT NULL
            )
        """)

        # 项目-演员关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_actors (
                project_id INTEGER NOT NULL,
                actor_id INTEGER NOT NULL,
                PRIMARY KEY (project_id, actor_id),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (actor_id) REFERENCES actors(id) ON DELETE CASCADE
            )
        """)

        self.conn.commit()

    def list_projects(self) -> List[Project]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY id DESC")
        projects = []
        for row in cursor.fetchall():
            data = dict(row)
            # 获取项目关联的演员
            cursor2 = self.conn.cursor()
            cursor2.execute(
                "SELECT actor_id FROM project_actors WHERE project_id = ?",
                (data["id"],)
            )
            data["actor"] = [r["actor_id"] for r in cursor2.fetchall()]
            projects.append(Project(data))
        return projects

    def get_project(self, project_id: int) -> Optional[Project]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            cursor2 = self.conn.cursor()
            cursor2.execute(
                "SELECT actor_id FROM project_actors WHERE project_id = ?",
                (data["id"],)
            )
            data["actor"] = [r["actor_id"] for r in cursor2.fetchall()]
            return Project(data)
        return None

    def save(self, project: Project):
        cursor = self.conn.cursor()

        if project.id:
            cursor.execute(
                """UPDATE projects SET slug=?, movie=?, year=?, is_series=?,
                   season=?, source_file_path=?, target_base_path=?
                   WHERE id=?""",
                (project.slug, project.movie, project.year,
                 1 if project.is_series else 0, project.season,
                 project.source_file_path, project.target_base_path,
                 project.id)
            )
        else:
            cursor.execute(
                """INSERT INTO projects
                   (slug, movie, year, is_series, season, source_file_path,
                    target_base_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (project.slug, project.movie, project.year,
                 1 if project.is_series else 0, project.season,
                 project.source_file_path, project.target_base_path)
            )
            project._data["id"] = cursor.lastrowid

        # 重建演员关联
        cursor.execute("DELETE FROM project_actors WHERE project_id = ?", (project.id,))
        for actor_id in project.actor_ids:
            cursor.execute(
                "INSERT INTO project_actors (project_id, actor_id) VALUES (?, ?)",
                (project.id, actor_id)
            )

        self.conn.commit()

    def delete(self, project_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM project_actors WHERE project_id = ?", (project_id,))
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self.conn.commit()

class NamingEngine:
    @staticmethod
    def _safe_name(name: str) -> str:
        return name.replace(' ', '.')

    @staticmethod
    def _build_actor_str(display_names: List[str]) -> str:
        return "+".join(display_names) if display_names else "Unknown"

    @classmethod
    def _se_suffix(cls, proj: Project) -> str:
        if proj.is_series and proj.season is not None:
            s = f".S{proj.season:02d}"
            ep = proj._data.get("episode")
            if ep is not None:
                s += f"E{ep:02d}"
            return s
        return ""

    @classmethod
    def gif_name(cls, proj: Project, index: int = 1) -> str:
        actors = cls._build_actor_str(proj.actor_display_names)
        movie = cls._safe_name(proj.movie)
        se = cls._se_suffix(proj)
        return f"[{proj.country}]{actors} » {movie}.{proj.year}{se}({index}).gif"

    @classmethod
    def video_name(cls, proj: Project, start: str, end: str) -> str:
        actors = cls._build_actor_str(proj.actor_display_names)
        movie = cls._safe_name(proj.movie)
        start_fmt = start.replace(':', '.')
        end_fmt = end.replace(':', '.')
        se = cls._se_suffix(proj)
        return f"[{proj.country}]{actors} » {movie}.{proj.year}{se} » {start_fmt}-{end_fmt}.mp4"

    @classmethod
    def concat_name(cls, proj: Project, first: str, last: str) -> str:
        actors = cls._build_actor_str(proj.actor_display_names)
        movie = cls._safe_name(proj.movie)
        first_fmt = first.replace(':', '.')
        last_fmt = last.replace(':', '.')
        se = cls._se_suffix(proj)
        return f"[{proj.country}]{actors} » {movie}.{proj.year}{se} » {first_fmt}~{last_fmt}.mp4"


    @classmethod
    def image_name(cls, proj: Project, count: int, ext: str) -> str:
        """图片重命名：遵循 v0/correct.py 命名规则"""
        actors = cls._build_actor_str(proj.actor_display_names)
        movie = cls._safe_name(proj.movie)
        se = cls._se_suffix(proj)
        return f"[{proj.country}]{actors} » {movie}.{proj.year}{se}-{count}.{ext}"


class PathHelper:
    @staticmethod
    def get_nonconflicting_filename(file_path: Path) -> Path:
        if not file_path.exists():
            return file_path
        parent = file_path.parent
        stem = file_path.stem
        suffix = file_path.suffix
        match = re.search(r'\((\d+)\)$', stem)
        if match:
            base = stem[:match.start()]
            idx = int(match.group(1))
        else:
            base = stem
            idx = 1
        while True:
            new_path = parent / f"{base}({idx}){suffix}"
            if not new_path.exists():
                return new_path
            idx += 1

    @staticmethod
    def ensure_dir(path: Path):
        path.mkdir(parents=True, exist_ok=True)


class FFmpegEngine:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback or print

    def _run(self, cmd: str) -> Tuple[bool, str]:
        self.log_callback(f"> {cmd}")
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                encoding='utf-8', errors='replace'
            )
            if result.returncode == 0:
                self.log_callback("[OK] 执行成功")
                return True, ""
            else:
                err = result.stderr[-500:] if result.stderr else "未知错误"
                self.log_callback(f"[ERR] {err}")
                return False, err
        except Exception as e:
            self.log_callback(f"[ERR] {e}")
            return False, str(e)

    def make_gif(self, proj: Project, start: str, end: str,
                 width: int = 480, fps: int = 15, colors: int = 64,
                 brightness: float = 0, contrast: float = 1, speed: float = 1) -> Tuple[bool, Path]:
        target_dir = Path(proj.target_base_path)
        PathHelper.ensure_dir(target_dir)
        raw_name = NamingEngine.gif_name(proj, 1)
        target_path = PathHelper.get_nonconflicting_filename(target_dir / raw_name)

        filters = []
        if brightness != 0 or contrast != 1:
            filters.append(f"eq=contrast={contrast}:brightness={brightness}")
        if speed != 1:
            filters.append(f"setpts={speed}*PTS")
        filters.extend([
            f"fps={fps}",
            f"scale={width}:-1:flags=lanczos",
            f"split[s0][s1];[s0]palettegen=max_colors={colors}[p];[s1][p]paletteuse=dither=bayer"
        ])
        filter_str = ",".join(filters)
        cmd = (
            f'ffmpeg -y -ss {start} -to {end} -i "{proj.source_file_path}" '
            f'-vf "{filter_str}" -loop 0 "{target_path}"'
        )
        ok, _ = self._run(cmd)
        return ok, target_path

    def cut_video(self, proj: Project, start: str, end: str,
                  copy: bool = False, no_audio: bool = False,
                  aspect: Optional[str] = None, audio_stream: Optional[int] = None) -> Tuple[bool, Path]:
        target_dir = Path(proj.target_base_path)
        PathHelper.ensure_dir(target_dir)
        raw_name = NamingEngine.video_name(proj, start, end)
        target_path = PathHelper.get_nonconflicting_filename(target_dir / raw_name)

        opts = []
        if copy:
            opts.append("-codec copy")
        if no_audio:
            opts.append("-an")
        if aspect:
            opts.append(f"-aspect {aspect}")
        if audio_stream is not None:
            opts.append(f"-map 0:v:0 -map 0:a:{audio_stream-1}")

        opt_str = " ".join(opts)
        cmd = (
            f'ffmpeg -y -ss {start} -to {end} -accurate_seek '
            f'-i "{proj.source_file_path}" {opt_str} -avoid_negative_ts 1 "{target_path}"'
        )
        ok, _ = self._run(cmd)
        return ok, target_path

    def concat_segments(self, proj: Project, segments: List[Tuple[str, str]],
                        copy: bool = False, no_audio: bool = False,
                        aspect: Optional[str] = None, audio_stream: Optional[int] = None) -> Tuple[bool, Path]:
        tmp_dir = Path("tmp/concat")
        PathHelper.ensure_dir(tmp_dir)
        for f in tmp_dir.glob("*.mp4"):
            f.unlink()

        filelist_lines = []
        for i, (seg_start, seg_end) in enumerate(segments, 1):
            seg_path = tmp_dir / f"{i}.mp4"
            filelist_lines.append(f"file {i}.mp4")
            opts = []
            if copy:
                opts.append("-codec copy")
            else:
                opts.append("-max_muxing_queue_size 9999")
            if no_audio:
                opts.append("-an")
            if aspect:
                opts.append(f"-aspect {aspect}")
            if audio_stream is not None:
                opts.append(f"-map 0:v:0 -map 0:a:{audio_stream-1}")
            opt_str = " ".join(opts)
            cmd = (
                f'ffmpeg -y -ss {seg_start} -to {seg_end} -accurate_seek '
                f'-i "{proj.source_file_path}" {opt_str} -avoid_negative_ts 1 "{seg_path}"'
            )
            ok, _ = self._run(cmd)
            if not ok:
                return False, Path("")

        list_file = tmp_dir / "filelist.txt"
        list_file.write_text("\n".join(filelist_lines), encoding='utf-8')

        target_dir = Path(proj.target_base_path)
        PathHelper.ensure_dir(target_dir)
        raw_name = NamingEngine.concat_name(proj, segments[0][0], segments[-1][1])
        target_path = PathHelper.get_nonconflicting_filename(target_dir / raw_name)

        cmd = f'ffmpeg -y -f concat -i "{list_file}" -c copy "{target_path}"'
        ok, _ = self._run(cmd)
        return ok, target_path