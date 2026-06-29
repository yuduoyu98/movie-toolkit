"""
Movie Toolkit GUI
项目制 + 演员库：创建项目时可无演员，剪辑时强制要求演员
基于 PyQt5
"""
import shutil
import sys
from pathlib import Path
from typing import Optional, List

# PyQt5 导入
try:
    from PyQt5 import QtWidgets, QtCore, QtGui
except ImportError as e:
    print(f"PyQt5 导入失败: {e}")
    print(f"Python: {sys.executable}")
    print("尝试:  python -m pip install --force-reinstall pyqt5")
    sys.exit(1)

# 从模块提取类
QApplication = QtWidgets.QApplication
QMainWindow = QtWidgets.QMainWindow
QWidget = QtWidgets.QWidget
QVBoxLayout = QtWidgets.QVBoxLayout
QHBoxLayout = QtWidgets.QHBoxLayout
QLabel = QtWidgets.QLabel
QLineEdit = QtWidgets.QLineEdit
QPushButton = QtWidgets.QPushButton
QComboBox = QtWidgets.QComboBox
QSpinBox = QtWidgets.QSpinBox
QDoubleSpinBox = QtWidgets.QDoubleSpinBox
QCheckBox = QtWidgets.QCheckBox
QGroupBox = QtWidgets.QGroupBox
QTabWidget = QtWidgets.QTabWidget
QTextEdit = QtWidgets.QTextEdit
QMessageBox = QtWidgets.QMessageBox
QTableWidget = QtWidgets.QTableWidget
QTableWidgetItem = QtWidgets.QTableWidgetItem
QHeaderView = QtWidgets.QHeaderView
QFileDialog = QtWidgets.QFileDialog
QListWidget = QtWidgets.QListWidget
QListWidgetItem = QtWidgets.QListWidgetItem
QStackedWidget = QtWidgets.QStackedWidget
QDialog = QtWidgets.QDialog
QDialogButtonBox = QtWidgets.QDialogButtonBox
QFormLayout = QtWidgets.QFormLayout
QGridLayout = QtWidgets.QGridLayout
QFrame = QtWidgets.QFrame
QSizePolicy = QtWidgets.QSizePolicy
QCompleter = QtWidgets.QCompleter
QStringListModel = QtCore.QStringListModel

Qt = QtCore.Qt
QThread = QtCore.QThread
QTimer = QtCore.QTimer
pyqtSignal = QtCore.pyqtSignal
QLayout = QtWidgets.QLayout
QSize = QtCore.QSize
QRect = QtCore.QRect
QFont = QtGui.QFont
QPalette = QtGui.QPalette
QColor = QtGui.QColor
from movie_core import (
    Actor, ActorManager, Project, ProjectManager,
    NamingEngine, FFmpegEngine, PathHelper, TaskManager, app_data_dir, resource_path
)


class Worker(QThread):
    """后台执行 FFmpeg"""
    log_signal = pyqtSignal(str)
    done_signal = pyqtSignal(bool, str)

    def __init__(self, engine, mode, **kwargs):
        super().__init__()
        self.engine = engine
        self.mode = mode
        self.kwargs = kwargs
        self.engine.log_callback = lambda msg: self.log_signal.emit(msg)

    def run(self):
        try:
            if self.mode == "gif":
                ok, path = self.engine.make_gif(**self.kwargs)
            elif self.mode == "cut":
                ok, path = self.engine.cut_video(**self.kwargs)
            elif self.mode == "concat":
                ok, path = self.engine.concat_segments(**self.kwargs)
            else:
                ok, path = False, Path("")
            self.done_signal.emit(ok, str(path) if path else "")
        except Exception as e:
            self.log_signal.emit(f"[ERR] 异常: {e}")
            self.done_signal.emit(False, "")


class FlowLayout(QLayout):
    """自动换行布局：从左到右排列，超出宽度自动换行"""
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        self._items = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Horizontal)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        x = rect.x() + m.left()
        y = rect.y() + m.top()
        line_height = 0
        right = rect.right() - m.right()

        for item in self._items:
            w = item.sizeHint().width()
            if x + w > right and line_height > 0:
                x = rect.x() + m.left()
                y += line_height + self.spacing()
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(x, y, w, item.sizeHint().height()))
            x += w + self.spacing()
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y() + m.bottom()


class ActorEditDialog(QDialog):
    """编辑/新建演员"""

    def __init__(self, parent=None, actor: Optional[Actor] = None):
        super().__init__(parent)
        self.actor = actor
        self.setWindowTitle("编辑演员" if actor else "新建演员")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.ed_name = QLineEdit(actor.name if actor else "")
        self.ed_chn_name = QLineEdit(actor.chn_name if actor else "")

        self.cb_country = QComboBox()
        self.cb_country.setEditable(True)
        self.cb_country.addItems(["CHN", "JAP", "KOR", "WEST", "SLA", "SEA", "LTA"])
        if actor:
            self.cb_country.setCurrentText(actor.country)

        form.addRow("姓名 *", self.ed_name)
        form.addRow("中文译名", self.ed_chn_name)
        form.addRow("地区 *", self.cb_country)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Save).setText("保存")
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_save(self):
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "姓名不能为空")
            return
        self.actor = Actor.create(
            name=name,
            country=self.cb_country.currentText(),
            chn_name=self.ed_chn_name.text().strip() or None
        )
        self.accept()

    def get_actor(self) -> Actor:
        return self.actor


class ArchiveDialog(QDialog):
    """归档整理对话框：按 国家→演员→电影 归类文件"""

    COUNTRY_NAMES = {
        'CHN': 'China', 'JAP': 'Japan', 'KOR': 'Korean',
        'WEST': 'West', 'SLA': 'Slavs', 'SEA': 'South-East Asia', 'LTA': 'Latin America',
    }

    def __init__(self, parent=None, source_dir: str = "", archive_root: str = ""):
        super().__init__(parent)
        self.setWindowTitle("归档整理")
        self.setMinimumSize(700, 500)
        self._source_dir = source_dir
        self._archive_root = archive_root
        self._preview_items = []  # [{src, dst, country, actor, movie}, ...]
        self._build_ui()
        if source_dir:
            self.ed_source.setText(source_dir)
            self._do_scan()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # 源目录
        src_row = QHBoxLayout()
        src_row.addWidget(QLabel("源目录:"))
        self.ed_source = QLineEdit(self._source_dir)
        self.ed_source.setPlaceholderText("要归档整理的目录…")
        src_row.addWidget(self.ed_source, stretch=1)
        btn_src = QPushButton("浏览...")
        btn_src.clicked.connect(lambda: self._pick_dir(self.ed_source))
        src_row.addWidget(btn_src)
        layout.addLayout(src_row)

        # 归档根目录
        ar_row = QHBoxLayout()
        ar_row.addWidget(QLabel("归档到:"))
        self.ed_archive_root = QLineEdit(self._archive_root)
        self.ed_archive_root.setPlaceholderText("归档根目录，其下按国家/演员/电影分文件夹…")
        ar_row.addWidget(self.ed_archive_root, stretch=1)
        btn_ar = QPushButton("浏览...")
        btn_ar.clicked.connect(lambda: self._pick_dir(self.ed_archive_root))
        ar_row.addWidget(btn_ar)
        layout.addLayout(ar_row)

        # 扫描 / 执行按钮
        btn_row = QHBoxLayout()
        self.btn_scan = QPushButton("🔍 扫描")
        self.btn_scan.clicked.connect(self._do_scan)
        btn_row.addWidget(self.btn_scan)

        self.lbl_summary = QLabel("")
        self.lbl_summary.setStyleSheet("color: #7f8c8d;")
        btn_row.addWidget(self.lbl_summary)
        btn_row.addStretch()

        self.btn_exec = QPushButton("执行归档")
        self.btn_exec.setEnabled(False)
        self.btn_exec.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; "
            "padding: 8px 18px; font-weight: bold; border-radius: 4px; }"
            "QPushButton:hover { background-color: #219a52; }"
            "QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.btn_exec.clicked.connect(self._do_archive)
        btn_row.addWidget(self.btn_exec)
        layout.addLayout(btn_row)

        # 预览表格
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["源文件名", "目标目录", "国家", "演员"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 50)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 100)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, stretch=1)

    def _pick_dir(self, target_edit: QLineEdit):
        start = target_edit.text().strip() or self._source_dir or ""
        path = QFileDialog.getExistingDirectory(self, "选择目录", start)
        if path:
            target_edit.setText(path)

    def _do_scan(self):
        source = self.ed_source.text().strip()
        archive_root = self.ed_archive_root.text().strip()
        if not source or not archive_root:
            QMessageBox.warning(self, "提示", "请填写源目录和归档根目录")
            return
        if not Path(source).exists():
            QMessageBox.warning(self, "提示", "源目录不存在")
            return
        if source == archive_root:
            QMessageBox.warning(self, "提示", "源目录和归档根目录不能相同")
            return

        self._preview_items = []
        IMG_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.mp4'}

        for fpath in Path(source).iterdir():
            if not fpath.is_file():
                continue
            if fpath.suffix.lower() not in IMG_EXTS:
                continue
            info = self._parse_filename(fpath.name)
            if not info:
                continue
            country_dir = self.COUNTRY_NAMES.get(info["country"], info["country"])
            target_dir = Path(archive_root) / country_dir / info["actor"] / info["movie"]
            self._preview_items.append({
                "src": fpath,
                "dst_dir": target_dir,
                "country": info["country"],
                "actor": info["actor"],
                "movie": info["movie"],
            })

        # 填充表格
        self.table.setRowCount(0)
        self.table.setRowCount(len(self._preview_items))
        for row, item in enumerate(self._preview_items):
            self.table.setItem(row, 0, QTableWidgetItem(item["src"].name))
            self.table.setItem(row, 1, QTableWidgetItem(str(item["dst_dir"])))
            self.table.setItem(row, 2, QTableWidgetItem(item["country"]))
            self.table.setItem(row, 3, QTableWidgetItem(item["actor"]))

        self.lbl_summary.setText(f"共 {len(self._preview_items)} 个文件待归档")
        self.btn_exec.setEnabled(len(self._preview_items) > 0)

    def _parse_filename(self, name: str):
        """解析文件名，提取 国家/演员/电影 信息"""
        import re
        # 格式: [Country]Actor.Name.中文名 » Movie.Name.Year-1.png  或 ... » ... » HH.mm.ss-HH.mm.ss.mp4
        try:
            # 国家
            country_match = re.match(r'^\[([A-Z]+)\]', name)
            if not country_match:
                return None
            country = country_match.group(1)
            rest = name[country_match.end():]

            # 演员 / 电影（用 » 分割）
            parts = rest.split('»')
            if len(parts) < 2:
                return None
            actor_part = parts[0].strip()
            movie_part = parts[1].strip()

            # 演员名：取英文名（点→空格），有中文名则优先中文名
            actor_name = actor_part.replace('.', ' ').strip()
            if '+' in actor_name:
                actor_name = actor_name.split('+')[0].strip()

            # 尝试提取中文/日文名
            chn_match = re.search(r'[一-鿿぀-ゟ゠-ヿ]{2,}', actor_part)
            if chn_match:
                actor_name = chn_match.group(0)

            # 电影名：去掉末尾编号/剧集标记/时间戳
            movie = movie_part.strip()
            # 去掉 -N.ext, (N).ext 结尾
            movie = re.sub(r'-\d+\.\w+$', '', movie)
            movie = re.sub(r'\(\d+\)\.\w+$', '', movie)
            # 去掉时间戳 » HH.mm.ss-HH.mm.ss 或 » HH.mm.ss~HH.mm.ss
            movie = re.sub(r'»\s*\d{2}\.\d{2}\.\d{2}[~\-]\d{2}\.\d{2}\.\d{2}', '', movie).strip()
            # 去掉剧集标记 .S01E01
            movie = re.sub(r'\.S\d{2}E\d{2}', '', movie)
            # 去掉末尾扩展名（排除纯数字年份，避免把 .1986 误删）
            movie = re.sub(r'\.(?!\d{4}$)\w+$', '', movie)

            if not movie:
                return None

            # 格式化为 [{Year}]{Movie Name}
            parts_m = movie.rsplit('.', 1)
            if len(parts_m) == 2 and parts_m[1].isdigit():
                year = parts_m[1]
                movie_name = parts_m[0].replace('.', ' ')
            else:
                year = ""
                movie_name = movie.replace('.', ' ')

            display_movie = f"[{year}]{movie_name}" if year else movie_name

            return {
                "country": country,
                "actor": actor_name,
                "movie": display_movie,
            }
        except Exception:
            return None

    def _do_archive(self):
        if not self._preview_items:
            return
        msg = f"将归档 {len(self._preview_items)} 个文件，确认执行？"
        reply = QMessageBox.question(self, "确认归档", msg, QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        success = 0
        errors = []
        for item in self._preview_items:
            try:
                item["dst_dir"].mkdir(parents=True, exist_ok=True)
                dst = item["dst_dir"] / item["src"].name
                # 冲突处理
                if dst.exists():
                    dst = PathHelper.get_nonconflicting_filename(dst)
                shutil.move(str(item["src"]), str(dst))
                success += 1
            except Exception as e:
                errors.append(f"{item['src'].name}: {e}")

        msg = f"归档完成：成功 {success} 个"
        if errors:
            msg += f"，失败 {len(errors)} 个"
        QMessageBox.information(self, "归档完成", msg)
        # 刷新预览
        self._do_scan()


class ActorSelector(QWidget):
    """演员选择器：支持搜索、自动补全、多选"""

    actors_changed = pyqtSignal()

    def __init__(self, actor_manager: ActorManager, parent=None, copy_list_button: bool = False):
        super().__init__(parent)
        self.actor_manager = actor_manager
        self.selected_actor_ids: List[int] = []
        self.project_actor_ids: List[int] = []
        self._copy_list_button = copy_list_button
        self._build_ui()

    def set_project_actor_ids(self, ids: List[int]):
        """标记哪些演员已绑定到项目（用于搜索区分），并刷新标签"""
        self.project_actor_ids = list(ids)
        # 清理已解绑的演员（不在 project 中的也移出 selected）
        self.selected_actor_ids = [a for a in self.selected_actor_ids if a in self.project_actor_ids]
        self._refresh_completer()
        self._refresh_tags()

    def _copy_actor_list(self):
        """复制项目绑定演员名称到剪贴板。

        规则：有中文译名用译名，否则英文名；名字内空格替换为 .；演员间用空格连接。
        """
        parts = []
        for aid in self.project_actor_ids:
            actor = self.actor_manager.get(aid)
            if not actor:
                continue
            name = (actor.chn_name or actor.name).replace(" ", ".")
            parts.append(name)
        text = " ".join(parts)
        QApplication.clipboard().setText(text)
        btn = getattr(self, "btn_copy_list", None)
        if btn is not None:
            btn.setText("✓ 已复制" if text else "（无绑定演员）")
            QTimer.singleShot(1200, lambda: btn.setText("复制演员列表"))

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 搜索输入 + 新建按钮
        search_row = QHBoxLayout()
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText("搜索演员，回车添加…")
        self.ed_search.returnPressed.connect(self._on_add_from_search)
        search_row.addWidget(self.ed_search)

        # 自动补全
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.ed_search.setCompleter(self.completer)
        self.ed_search.textChanged.connect(lambda: self.completer.complete())
        self._refresh_completer()

        btn_new = QPushButton("新增")
        btn_new.setToolTip("录入新演员")
        btn_new.clicked.connect(self._on_new_actor)
        search_row.addWidget(btn_new)

        btn_manage = QPushButton("演员库")
        btn_manage.clicked.connect(self._on_manage_actors)
        search_row.addWidget(btn_manage)

        layout.addLayout(search_row)

        # 已选演员标签区（自动换行）
        self.tags_widget = QWidget()
        self.tags_widget.setMinimumHeight(70)
        self.tags_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.tags_layout = FlowLayout(self.tags_widget, margin=2, spacing=4)
        layout.addWidget(self.tags_widget)

        # 底部：复制演员列表（仅工作台启用）
        if self._copy_list_button:
            self.btn_copy_list = QPushButton("复制演员列表")
            self.btn_copy_list.setToolTip(
                "复制项目绑定演员的名称：有中文译名用译名，否则英文名；"
                "名字内空格用 . 连接；演员间用空格分隔"
            )
            self.btn_copy_list.clicked.connect(self._copy_actor_list)
            layout.addWidget(self.btn_copy_list)



    def _refresh_completer(self):
        """刷新自动补全候选列表，已绑定项目的演员前缀 ●"""
        names = []
        all_actors = self.actor_manager.list_actors()
        for a in all_actors:
            label = f"[{a.country}]{a.name}"
            if a.chn_name:
                label += f"({a.chn_name})"
            if a.id in self.project_actor_ids:
                label = f"● {label}"
            names.append(label)
        model = QStringListModel(names)
        self.completer.setModel(model)

    def _on_add_from_search(self):
        text = self.ed_search.text().strip()
        if text.startswith("● "):
            text = text[2:]
        # 去掉 "[地区]" 前缀和 "(中文译名)" 后缀
        import re
        text = re.sub(r'^\[[A-Z]+\]', '', text).strip()
        text = re.sub(r'\s*\(.*?\)\s*$', '', text).strip()
        if not text:
            return

        actor = self.actor_manager.find_by_name(text)
        if not actor:
            results = self.actor_manager.search(text)
            if results:
                actor = results[0]

        if actor:
            if actor.id not in self.selected_actor_ids:
                self.selected_actor_ids.append(actor.id)
            if actor.id not in self.project_actor_ids:
                self.project_actor_ids.append(actor.id)
            self._refresh_tags()
            self.actors_changed.emit()

        c = self.ed_search.completer()
        self.ed_search.setCompleter(None)
        self.ed_search.clear()
        self.ed_search.setCompleter(c)
        if not actor:
            reply = QMessageBox.question(
                self, "演员未找到",
                f'演员 "{text}" 不在库中，是否新建？',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._on_new_actor(prefill=text)

    def _on_new_actor(self, prefill: str = ""):
        dlg = ActorEditDialog(self)
        if prefill:
            dlg.ed_name.setText(prefill)
        if dlg.exec_() == QDialog.Accepted:
            actor = dlg.get_actor()
            self.actor_manager.add(actor)
            self._refresh_completer()
            if actor.id not in self.selected_actor_ids:
                self.selected_actor_ids.append(actor.id)
            if actor.id not in self.project_actor_ids:
                self.project_actor_ids.append(actor.id)
            self._refresh_tags()
            self.actors_changed.emit()

    def _on_manage_actors(self):
        """弹出演员库管理窗口，项目绑定的演员置顶 + ● 标记"""
        dlg = QDialog(self)
        dlg.setWindowTitle("演员库管理")
        dlg.setMinimumSize(500, 400)
        layout = QVBoxLayout(dlg)

        list_widget = QListWidget()
        actors = self.actor_manager.list_actors()
        # 项目绑定的排前面
        bound = [a for a in actors if a.id in self.project_actor_ids]
        unbound = [a for a in actors if a.id not in self.project_actor_ids]
        for a in bound + unbound:
            label = f"● {a.display_name}" if a.id in self.project_actor_ids else f"  {a.display_name}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, a.id)
            if a.id in self.project_actor_ids:
                item.setForeground(QtGui.QColor("#2980b9"))
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            list_widget.addItem(item)
        layout.addWidget(list_widget)

        # 双击绑定演员并关闭
        def on_double_click(item):
            actor_id = item.data(Qt.UserRole)
            if actor_id is None:
                return
            if actor_id not in self.selected_actor_ids:
                self.selected_actor_ids.append(actor_id)
            if actor_id not in self.project_actor_ids:
                self.project_actor_ids.append(actor_id)
            self._refresh_tags()
            self.actors_changed.emit()
            dlg.accept()

        list_widget.itemDoubleClicked.connect(on_double_click)

        btn_bar = QHBoxLayout()

        btn_edit = QPushButton("编辑")
        def do_edit():
            item = list_widget.currentItem()
            if not item:
                return
            actor = self.actor_manager.get(item.data(Qt.UserRole))
            if actor:
                edlg = ActorEditDialog(dlg, actor)
                if edlg.exec_() == QDialog.Accepted:
                    new_actor = edlg.get_actor()
                    self.actor_manager.add(new_actor)
                    self._refresh_completer()
                    list_widget.clear()
                    actors = self.actor_manager.list_actors()
                    bound = [a for a in actors if a.id in self.project_actor_ids]
                    unbound = [a for a in actors if a.id not in self.project_actor_ids]
                    for a in bound + unbound:
                        label = f"● {a.display_name}" if a.id in self.project_actor_ids else f"  {a.display_name}"
                        it = QListWidgetItem(label)
                        it.setData(Qt.UserRole, a.id)
                        if a.id in self.project_actor_ids:
                            it.setForeground(QtGui.QColor("#2980b9"))
                            font = it.font()
                            font.setBold(True)
                            it.setFont(font)
                        list_widget.addItem(it)
        btn_edit.clicked.connect(do_edit)
        btn_bar.addWidget(btn_edit)

        btn_del = QPushButton("删除")
        def do_del():
            item = list_widget.currentItem()
            if not item:
                return
            actor_id = item.data(Qt.UserRole)
            actor = self.actor_manager.get(actor_id)
            if actor and QMessageBox.question(
                dlg, "确认", f"删除演员 {actor.display_name}？",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self.actor_manager.delete(actor_id)
                list_widget.takeItem(list_widget.row(item))
                self._refresh_completer()
        btn_del.clicked.connect(do_del)
        btn_bar.addWidget(btn_del)

        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        dlg.exec_()

    def _refresh_tags(self):
        """刷新演员标签：选中在前，未选中在后；点灰标签选中，点×取消"""
        while self.tags_layout.count() > 0:
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 显示顺序：已选中 → 项目绑定但未选中 → 手动添加但未选中（不太可能）
        all_bound = list(self.project_actor_ids)
        shown = set(all_bound + self.selected_actor_ids)
        ordered = [a for a in self.selected_actor_ids if a in shown]
        ordered += [a for a in all_bound if a not in ordered]
        for a in self.selected_actor_ids:
            if a not in ordered:
                ordered.append(a)

        for aid in ordered:
            if aid not in shown:
                continue
            actor = self.actor_manager.get(aid)
            if not actor:
                continue
            is_selected = aid in self.selected_actor_ids
            tag_text = f"[{actor.country}]{actor.name}"
            if actor.chn_name:
                tag_text += f"({actor.chn_name})"

            tag = QFrame()
            if is_selected:
                tag.setStyleSheet(
                    "QFrame { border: 1px solid #2980b9; border-radius: 8px; "
                    "padding: 2px 8px; }"
                    "QFrame:hover { border-color: #2471a3; }"
                )
            else:
                tag.setStyleSheet(
                    "QFrame { border: 1px solid #555; border-radius: 8px; "
                    "padding: 2px 8px; }"
                    "QFrame:hover { border-color: #2980b9; }"
                )
            tag_layout = QHBoxLayout(tag)
            tag_layout.setContentsMargins(6, 2, 6, 2)
            tag_layout.setSpacing(4)

            lbl = QLabel(tag_text)
            if is_selected:
                lbl.setStyleSheet("font-size: 12px; border: none;")
            else:
                lbl.setStyleSheet("color: #888; font-size: 12px; border: none;")
            tag_layout.addWidget(lbl)

            # 已选中的标签：左移/右移箭头
            if is_selected:
                idx = self.selected_actor_ids.index(aid)
                if idx > 0:
                    btn_l = QPushButton("◀")
                    btn_l.setFixedSize(16, 16)
                    btn_l.setStyleSheet(
                        "QPushButton { background: transparent; color: #999; "
                        "font-size: 10px; font-weight: normal; border: none; }"
                        "QPushButton:hover { color: #2980b9; }"
                    )
                    btn_l.clicked.connect(lambda checked, a=aid: self._move_actor(a, -1))
                    tag_layout.addWidget(btn_l)
                if idx < len(self.selected_actor_ids) - 1:
                    btn_r = QPushButton("▶")
                    btn_r.setFixedSize(16, 16)
                    btn_r.setStyleSheet(
                        "QPushButton { background: transparent; color: #999; "
                        "font-size: 10px; font-weight: normal; border: none; }"
                        "QPushButton:hover { color: #2980b9; }"
                    )
                    btn_r.clicked.connect(lambda checked, a=aid: self._move_actor(a, 1))
                    tag_layout.addWidget(btn_r)

            btn_x = QPushButton("×")
            btn_x.setFixedSize(16, 16)
            btn_x.setStyleSheet(
                "QPushButton { background: transparent; color: #999; "
                "font-size: 12px; font-weight: normal; border: none; }"
                "QPushButton:hover { color: #e74c3c; }"
            )
            btn_x.clicked.connect(lambda checked, a=aid: self._remove_actor(a))
            tag_layout.addWidget(btn_x)

            # 灰标签：点击选中+绑定；蓝标签：点击取消选中（不解除绑定）
            if not is_selected:
                lbl.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
                lbl.mousePressEvent = lambda ev, a=aid: self._select_actor(a)
            else:
                lbl.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
                lbl.mousePressEvent = lambda ev, a=aid: self._deselect_actor(a)

            self.tags_layout.addWidget(tag)

    def _select_actor(self, actor_id: int):
        """点击灰标签 → 选中并绑定项目"""
        if actor_id not in self.selected_actor_ids:
            self.selected_actor_ids.append(actor_id)
        if actor_id not in self.project_actor_ids:
            self.project_actor_ids.append(actor_id)
        self._refresh_tags()
        self.actors_changed.emit()

    def _deselect_actor(self, actor_id: int):
        """点击蓝标签 → 仅取消选中（保持项目绑定）"""
        if actor_id in self.selected_actor_ids:
            self.selected_actor_ids.remove(actor_id)
        self._refresh_tags()
        self.actors_changed.emit()

    def _move_actor(self, actor_id: int, direction: int):
        """移动演员在选中列表中的位置（-1 左移, +1 右移）"""
        if actor_id not in self.selected_actor_ids:
            return
        idx = self.selected_actor_ids.index(actor_id)
        new_idx = idx + direction
        if 0 <= new_idx < len(self.selected_actor_ids):
            self.selected_actor_ids.remove(actor_id)
            self.selected_actor_ids.insert(new_idx, actor_id)
            self._refresh_tags()
            self.actors_changed.emit()

    def _remove_actor(self, actor_id: int):
        """× 按钮：取消选中并解绑项目"""
        if actor_id in self.selected_actor_ids:
            self.selected_actor_ids.remove(actor_id)
        if actor_id in self.project_actor_ids:
            self.project_actor_ids.remove(actor_id)
        self._refresh_tags()
        self.actors_changed.emit()

    def set_actor_ids(self, ids: List[int]):
        self.selected_actor_ids.clear()
        for aid in ids:
            if aid and aid not in self.selected_actor_ids:
                self.selected_actor_ids.append(aid)
        self._refresh_tags()

    def get_actor_ids(self) -> List[int]:
        return list(self.selected_actor_ids)


class ProjectDialog(QDialog):
    """新建 / 编辑项目弹窗：创建时可不填演员"""

    def __init__(self, parent=None, project: Optional[Project] = None,
                 actor_manager: Optional[ActorManager] = None):
        super().__init__(parent)
        self.project = project
        self.actor_manager = actor_manager or ActorManager()
        self.setWindowTitle("编辑项目" if project else "新建项目")
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.ed_movie = QLineEdit(project.movie if project else "")
        self.ed_year = QSpinBox()
        self.ed_year.setRange(1900, 2100)
        self.ed_year.setValue(project.year if project else 2025)

        # 演员选择器（创建时可选，非必填）
        self.actor_selector = ActorSelector(self.actor_manager)
        if project:
            self.actor_selector.set_actor_ids(project.actor_ids)
            self.actor_selector.actors_changed.connect(self._update_actor_display)

        # 演员显示区域
        self.lbl_project_actors = QLabel("项目未绑定演员")
        self.lbl_project_actors.setStyleSheet("color: #666; font-size: 12px;")
        self.lbl_project_actors.setMinimumHeight(20)

        # 剧集勾选 + 季数输入（默认隐藏）
        self.chk_series = QCheckBox("这是剧集")
        self.chk_series.stateChanged.connect(self._on_series_toggle)

        self.season_row = QWidget()
        season_layout = QHBoxLayout(self.season_row)
        season_layout.setContentsMargins(0, 0, 0, 0)
        self.ed_season = QSpinBox()
        self.ed_season.setRange(1, 99)
        self.ed_season.setValue(project.season if project and project.season else 1)
        season_layout.addWidget(QLabel("第"))
        season_layout.addWidget(self.ed_season)
        season_layout.addWidget(QLabel("季"))
        season_layout.addStretch()
        self.season_row.setVisible(False)

        if project and project.is_series:
            self.chk_series.setChecked(True)
            self.season_row.setVisible(True)

        self.ed_source = QLineEdit(project.source_file_path if project else "")
        btn_source = QPushButton("浏览...")
        btn_source.clicked.connect(self._pick_source)
        source_row = QHBoxLayout()
        source_row.addWidget(self.ed_source)
        source_row.addWidget(btn_source)

        self.ed_target = QLineEdit(project.target_base_path if project else r"D:\ffmpeg")
        btn_target = QPushButton("浏览...")
        btn_target.clicked.connect(self._pick_target)
        target_row = QHBoxLayout()
        target_row.addWidget(self.ed_target)
        target_row.addWidget(btn_target)

        form.addRow("影片名称 *", self.ed_movie)
        form.addRow("年份 *", self.ed_year)
        form.addRow("演员（可选）", self.actor_selector)
        form.addRow("", self.lbl_project_actors)
        form.addRow("", self.chk_series)
        form.addRow("", self.season_row)
        form.addRow("源视频文件 *", source_row)
        form.addRow("输出目录 *", target_row)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Save).setText("保存")
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_series_toggle(self, state):
        self.season_row.setVisible(state == Qt.Checked)

    def _pick_source(self):
        default_dir = r"D:\迅雷下载\[M]"
        if not Path(default_dir).exists():
            default_dir = ""
        path, _ = QFileDialog.getOpenFileName(self, "选择源视频", default_dir, "Video Files (*.mp4 *.mkv *.avi *.mov)")
        if path:
            self.ed_source.setText(path)

    def _pick_target(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.ed_target.setText(path)

    def _update_actor_display(self):
        """更新项目演员显示"""
        actor_ids = self.actor_selector.get_actor_ids()
        if actor_ids:
            display_names = []
            for aid in actor_ids:
                actor = self.actor_manager.get(aid)
                if actor:
                    name = f"{actor.name}"
                    if actor.chn_name:
                        name = f"{name} ({actor.chn_name})"
                    display_names.append(name)
            self.lbl_project_actors.setText(f"项目绑定演员：{', '.join(display_names)}")
        else:
            self.lbl_project_actors.setText("项目未绑定演员")

    def _on_save(self):
        if not all([self.ed_movie.text().strip(),
                    self.ed_source.text().strip(), self.ed_target.text().strip()]):
            QMessageBox.warning(self, "提示", "请填写所有带 * 的必填项")
            return

        is_series = self.chk_series.isChecked()
        season = self.ed_season.value() if is_series else None

        actor_ids = self.actor_selector.get_actor_ids()

        self.project = Project.create(
            movie=self.ed_movie.text().strip(),
            year=self.ed_year.value(),
            source_file_path=self.ed_source.text().strip(),
            target_base_path=self.ed_target.text().strip(),
            is_series=is_series,
            season=season,
        )
        self.project.set_actor_ids(actor_ids)
        self.accept()

    def get_project(self) -> Project:
        return self.project


class ProjectListPage(QWidget):
    """项目列表页"""
    project_selected = pyqtSignal(Project)
    theme_toggled = pyqtSignal()

    def __init__(self, manager: ProjectManager, actor_manager: ActorManager):
        super().__init__()
        self.manager = manager
        self.actor_manager = actor_manager
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title = QLabel("影片项目")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        title_row.addWidget(title, stretch=1)

        self.btn_theme_list = QPushButton("🌙")
        self.btn_theme_list.setObjectName("btn_theme_list")
        self.btn_theme_list.setFixedSize(32, 32)
        self.btn_theme_list.setToolTip("切换夜间模式")
        self.btn_theme_list.setStyleSheet(
            "QPushButton { font-size: 16px; border: none; background: transparent; }"
            "QPushButton:hover { background: #e0e0e0; border-radius: 16px; }"
        )
        self.btn_theme_list.clicked.connect(self.theme_toggled.emit)
        title_row.addWidget(self.btn_theme_list)

        layout.addLayout(title_row)

        # 搜索框
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText("搜索项目…")
        self.ed_search.setClearButtonEnabled(True)
        self.ed_search.setMinimumHeight(36)
        self.ed_search.setStyleSheet("font-size: 14px; padding: 4px 8px;")
        self.ed_search.textChanged.connect(self._apply_filter)
        layout.addWidget(self.ed_search)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #dcdcdc;
                border-radius: 6px;
                padding: 4px;
                font-size: 14px;
            }
            QListWidget::item {
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: transparent;
            }
        """)
        self.list_widget.itemDoubleClicked.connect(self._on_open)
        layout.addWidget(self.list_widget, stretch=1)

        btn_bar = QHBoxLayout()

        btn_bar.addStretch()

        btn_new = QPushButton("新建项目")
        btn_new.setStyleSheet("padding: 10px 20px; font-size: 14px;")
        btn_new.clicked.connect(self._on_new)
        btn_bar.addWidget(btn_new)

        btn_open = QPushButton("进入工作台")
        btn_open.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; "
            "padding: 10px 24px; font-size: 14px; font-weight: bold; border-radius: 6px; }"
            "QPushButton:hover { background-color: #2980b9; }"
        )
        btn_open.clicked.connect(self._on_open)
        btn_bar.addWidget(btn_open)

        layout.addLayout(btn_bar)

    def _build_project_row(self, p: Project) -> QWidget:
        """构建项目行：粗体名称 + 编辑/删除按钮"""
        p.resolve_actors(self.actor_manager)
        row = QWidget()
        row.setAutoFillBackground(False)
        row.setStyleSheet("background: transparent;")
        h = QHBoxLayout(row)
        h.setContentsMargins(12, 10, 8, 10)
        h.setSpacing(8)

        name_lbl = QLabel(p.short_name)
        name_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        name_lbl.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        name_lbl.mouseDoubleClickEvent = lambda ev: self._on_open()
        h.addWidget(name_lbl, stretch=1)

        btn_edit = QPushButton("编辑")
        btn_edit.setFixedWidth(50)
        btn_edit.setStyleSheet(
            "QPushButton { font-size: 12px; padding: 4px 8px; color: #2980b9; "
            "border: 1px solid #2980b9; border-radius: 4px; background: transparent; }"
            "QPushButton:hover { color: white; background: #2980b9; }"
        )
        btn_edit.clicked.connect(lambda checked, pid=p.id: self._on_edit_project(pid))
        h.addWidget(btn_edit)

        btn_del = QPushButton("删除")
        btn_del.setFixedWidth(50)
        btn_del.setStyleSheet(
            "QPushButton { font-size: 12px; padding: 4px 8px; color: #c0392b; "
            "border: 1px solid #c0392b; border-radius: 4px; background: transparent; }"
            "QPushButton:hover { color: white; background: #c0392b; }"
        )
        btn_del.clicked.connect(lambda checked, pid=p.id: self._on_delete_project(pid))
        h.addWidget(btn_del)

        return row

    def _refresh_list(self):
        self.list_widget.clear()
        projects = self.manager.list_projects()
        for p in projects:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, p.id)
            item.setSizeHint(QSize(0, 48))
            tooltip = f"{p.display_name}\n源: {p.source_file_path}\n输出: {p.target_base_path}"
            item.setToolTip(tooltip)
            self.list_widget.addItem(item)
            row_widget = self._build_project_row(p)
            self.list_widget.setItemWidget(item, row_widget)

        if not projects:
            empty = QListWidgetItem("暂无项目")
            empty.setFlags(Qt.NoItemFlags)
            empty.setForeground(Qt.gray)
            self.list_widget.addItem(empty)

    def _apply_filter(self):
        """搜索过滤"""
        text = self.ed_search.text().strip().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.flags() == Qt.NoItemFlags:
                continue  # 空状态占位
            row_widget = self.list_widget.itemWidget(item)
            if row_widget:
                name_lbl = row_widget.findChild(QLabel)
                if name_lbl:
                    match = text in name_lbl.text().lower()
                    item.setHidden(not match)

    def _current_project(self) -> Optional[Project]:
        item = self.list_widget.currentItem()
        if not item:
            return None
        pid = item.data(Qt.UserRole)
        if not pid:
            return None
        proj = self.manager.get_project(pid)
        if proj:
            proj.resolve_actors(self.actor_manager)
        return proj

    def _on_new(self):
        dlg = ProjectDialog(self, actor_manager=self.actor_manager)
        if dlg.exec_() == QDialog.Accepted:
            proj = dlg.get_project()
            self.manager.save(proj)
            self._refresh_list()
            for i in range(self.list_widget.count()):
                if self.list_widget.item(i).data(Qt.UserRole) == proj.id:
                    self.list_widget.setCurrentRow(i)
                    break

    def _on_open(self):
        proj = self._current_project()
        if proj:
            self.project_selected.emit(proj)
        else:
            QMessageBox.information(self, "提示", "请先选择一个项目")

    def _on_edit_project(self, pid: int):
        proj = self.manager.get_project(pid)
        if not proj:
            return
        dlg = ProjectDialog(self, proj, self.actor_manager)
        if dlg.exec_() == QDialog.Accepted:
            new_proj = dlg.get_project()
            new_proj._data["id"] = proj.id
            new_proj._data["slug"] = proj.slug
            self.manager.save(new_proj)
            self._refresh_list()

    def _on_delete_project(self, pid: int):
        proj = self.manager.get_project(pid)
        if not proj:
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"删除项目 {proj.short_name}？\n（不会删除已生成的文件）",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.manager.delete(pid)
            self._refresh_list()


class ThumbExtractor(QThread):
    """后台为成功任务的输出文件生成缩略图（视频抽帧 / GIF 取首帧）"""
    done = pyqtSignal()

    def __init__(self, jobs):
        super().__init__()
        self.jobs = jobs   # [(task_id, output_path), ...]

    @staticmethod
    def _probe_duration(path) -> float:
        import subprocess, re
        try:
            r = subprocess.run(f'ffmpeg -i "{path}"', shell=True, capture_output=True,
                               text=True, encoding='utf-8', errors='replace')
            m = re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)', r.stderr or '')
            if m:
                return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        except Exception:
            pass
        return 0.0

    def run(self):
        import subprocess
        thumb_dir = app_data_dir() / "tmp" / "thumbs"
        thumb_dir.mkdir(parents=True, exist_ok=True)
        for tid, out in self.jobs:
            thumb = thumb_dir / f"{tid}.png"
            if thumb.exists() or str(out).lower().endswith(".gif"):
                continue   # GIF 不抽帧（面板直读首帧，预览播放动图）
            dur = self._probe_duration(out)
            candidates = [f"{dur / 2:.3f}"] if dur > 0 else ["1", "0.5", "0"]
            for ss in candidates:
                cmd = f'ffmpeg -y -ss {ss} -i "{out}" -frames:v 1 -vf "scale=640:-1" "{thumb}"'
                subprocess.run(cmd, shell=True, capture_output=True)
                if thumb.exists() and thumb.stat().st_size > 0:
                    break
        self.done.emit()


def _sheet_grid(dur):
    """按时长分级返回 contact-sheet 配置 (帧数, 列, 行)；帧数 0 表示太短，用单帧。"""
    if dur < 10:
        return (0, 0, 0)
    if dur < 60:
        return (4, 2, 2)
    if dur < 300:
        return (6, 3, 2)
    return (9, 3, 3)


class _ZoomImage(QtWidgets.QScrollArea):
    """可缩放图片视图：默认适配视口，Ctrl+滚轮缩放，放大后可滚动。GIF 用 setMovie（原始大小）。"""
    def __init__(self):
        super().__init__()
        self.img = QLabel()
        self.img.setAlignment(Qt.AlignCenter)
        self.img.setMinimumSize(1, 1)
        self._pix = None
        self._zoom = 1.0
        self.setWidget(self.img)
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(420, 280)

    def setFullPixmap(self, pix):
        self._pix = pix
        self._zoom = 1.0
        self.img.setMovie(None)
        self._render()

    def setMovie(self, movie):
        self._pix = None
        self._zoom = 1.0
        self.img.setMovie(movie)
        if movie is not None:
            self.img.adjustSize()
            self.img.resize(self.img.sizeHint())

    def clearImage(self):
        self._pix = None
        self._zoom = 1.0
        self.img.setMovie(None)
        self.img.clear()

    def setText(self, t):
        self._pix = None
        self.img.setMovie(None)
        self.img.setText(t)
        self.img.resize(self.viewport().size())

    def _render(self):
        if self._pix is None or self._pix.isNull():
            return
        vw = max(1, self.viewport().width() - 6)
        vh = max(1, self.viewport().height() - 6)
        fit = self._pix.scaled(vw, vh, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if abs(self._zoom - 1.0) < 1e-6:
            scaled = fit
        else:
            scaled = self._pix.scaled(max(1, int(fit.width() * self._zoom)),
                                      max(1, int(fit.height() * self._zoom)),
                                      Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.img.resize(scaled.size())
        self.img.setPixmap(scaled)

    def wheelEvent(self, e):
        if self._pix is not None and (e.modifiers() & Qt.ControlModifier):
            factor = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
            self._zoom = max(0.1, min(12.0, self._zoom * factor))
            self._render()
            e.accept()
        else:
            super().wheelEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._pix is not None:
            self._render()
        elif self.img.text() and self.img.movie() is None:
            self.img.resize(self.viewport().size())


class _PreviewFrameExtractor(QThread):
    """后台为预览抽取多帧（contact sheet 素材）；Qt 拼接在主线程完成"""
    done = pyqtSignal(int)

    def __init__(self, tid, out, n=9):
        super().__init__()
        self.tid = tid
        self.out = out
        self.n = n

    def run(self):
        import subprocess
        try:
            dur = ThumbExtractor._probe_duration(self.out)
            if dur > 0:
                tmp_dir = app_data_dir() / "tmp" / "thumbs" / f"_sheet_{self.tid}"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                for i in range(self.n):
                    t = dur * (i + 0.5) / self.n
                    fp = tmp_dir / f"{i}.png"
                    subprocess.run(
                        f'ffmpeg -y -ss {t:.3f} -i "{self.out}" -frames:v 1 -vf "scale=320:-1" "{fp}"',
                        shell=True, capture_output=True)
        except Exception:
            pass
        self.done.emit(self.tid)


class _ElideMiddleDelegate(QtWidgets.QStyledItemDelegate):
    """文件名列：过长时中间省略（保留开头与结尾），自适应列宽。"""
    def paint(self, painter, option, index):
        text = index.data(Qt.DisplayRole)
        painter.save()
        if option.state & QtWidgets.QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.brush(QtGui.QPalette.Highlight))
            painter.setPen(option.palette.color(QtGui.QPalette.HighlightedText))
        else:
            painter.setPen(option.palette.color(QtGui.QPalette.Text))
        rect = option.rect.adjusted(6, 0, -6, 0)
        elided = option.fontMetrics.elidedText(
            str(text) if text is not None else "", Qt.ElideMiddle, rect.width())
        painter.drawText(rect, Qt.AlignVCenter | Qt.AlignLeft, elided)
        painter.restore()


class TaskListDialog(QDialog):
    """任务列表面板：查看 进行中/成功/失败/未进行 的任务，支持恢复、终止、删除；成功任务有缩略图，双击预览"""
    STATUS_COLOR = {"进行中": "#e67e22", "成功": "#27ae60", "失败": "#e74c3c", "未进行": "#95a5a6"}

    def __init__(self, workbench):
        super().__init__(workbench)
        self.workbench = workbench
        self.setWindowTitle("任务列表")
        self.setMinimumSize(820, 460)
        self.resize(1080, 560)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self._thumb_busy = False
        self._thumb_worker = None
        self._sheet_workers = []   # 预览用 contact-sheet 后台抽取线程
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        top = QHBoxLayout()
        btn_save = QPushButton("💾 保存当前为任务")
        btn_save.setToolTip("把当前工作台配置（时间段/参数/演员）存为一个「未进行」任务，便于以后恢复重剪")
        btn_save.clicked.connect(self._on_save_preset)
        top.addWidget(btn_save)
        top.addStretch()
        self.lbl_count = QLabel("暂无任务")
        self.lbl_count.setStyleSheet("color:#7f8c8d;")
        top.addWidget(self.lbl_count)
        layout.addLayout(top)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["缩略图", "类型", "状态", "时间", "输出文件", "操作"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setIconSize(QtCore.QSize(96, 56))
        self.table.setColumnWidth(0, 110)
        self.table.setColumnWidth(1, 56)
        self.table.setColumnWidth(2, 70)
        self.table.setColumnWidth(3, 135)
        self.table.setColumnWidth(5, 160)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setItemDelegateForColumn(4, _ElideMiddleDelegate(self.table))
        self.table.cellDoubleClicked.connect(self._on_cell_double_click)
        layout.addWidget(self.table)
        self.refresh()

    def _on_save_preset(self):
        self.workbench._save_task_preset()

    def _thumb_path(self, tid):
        return app_data_dir() / "tmp" / "thumbs" / f"{tid}.png"

    def _sheet_path(self, tid):
        return app_data_dir() / "tmp" / "thumbs" / f"{tid}_sheet.png"

    def _extract_thumb_sync(self, tid, out):
        """同步抽一帧（预览时后台缓存尚未就绪的兜底）"""
        import subprocess
        try:
            thumb = self._thumb_path(tid)
            thumb.parent.mkdir(parents=True, exist_ok=True)
            dur = ThumbExtractor._probe_duration(out)
            cands = [f"{dur / 2:.3f}"] if dur > 0 else ["1", "0.5", "0"]
            for ss in cands:
                subprocess.run(
                    f'ffmpeg -y -ss {ss} -i "{out}" -frames:v 1 -vf "scale=640:-1" "{thumb}"',
                    shell=True, capture_output=True)
                if thumb.exists() and thumb.stat().st_size > 0:
                    break
        except Exception:
            pass

    def _finalize_contact_sheet(self, tid, cols=3, rows=3):
        """主线程：把后台抽好的多帧拼成 contact sheet 缓存"""
        try:
            n = cols * rows
            sheet = self._sheet_path(tid)
            tmp_dir = sheet.parent / f"_sheet_{tid}"
            frame_files = [tmp_dir / f"{i}.png" for i in range(n)]
            frame_files = [f for f in frame_files if f.exists() and f.stat().st_size > 0]
            pixmaps = [QtGui.QPixmap(str(f)) for f in frame_files]
            pixmaps = [p for p in pixmaps if not p.isNull()]
            for f in frame_files:
                try:
                    f.unlink()
                except Exception:
                    pass
            try:
                tmp_dir.rmdir()
            except Exception:
                pass
            if not pixmaps:
                return
            fw = max(p.width() for p in pixmaps)
            fh = max(p.height() for p in pixmaps)
            gap = 2
            sheet_pix = QtGui.QPixmap(cols * fw + (cols + 1) * gap,
                                      rows * fh + (rows + 1) * gap)
            sheet_pix.fill(QtCore.Qt.black)
            painter = QtGui.QPainter(sheet_pix)
            for idx, p in enumerate(pixmaps[:n]):
                r = idx // cols
                c = idx % cols
                x = gap + c * (fw + gap) + (fw - p.width()) // 2
                y = gap + r * (fh + gap) + (fh - p.height()) // 2
                painter.drawPixmap(x, y, p)
            painter.end()
            sheet_pix.save(str(sheet), "PNG")
        except Exception:
            pass

    def refresh(self):
        wb = self.workbench
        if not wb.project:
            return
        tasks = wb.task_manager.list_for_project(wb.project.id)
        self.table.setRowCount(0)
        self.table.setRowCount(len(tasks))
        for row, t in enumerate(tasks):
            self.table.setRowHeight(row, 64)
            thumb_item = QTableWidgetItem()
            thumb_item.setData(Qt.UserRole, t["id"])
            self._load_thumb(thumb_item, t)
            self.table.setItem(row, 0, thumb_item)
            self.table.setItem(row, 1, QTableWidgetItem(t.get("tag") or ""))
            st = t.get("status") or ""
            st_item = QTableWidgetItem(st)
            st_item.setForeground(QtGui.QColor(self.STATUS_COLOR.get(st, "#333333")))
            self.table.setItem(row, 2, st_item)
            self.table.setItem(row, 3, QTableWidgetItem(t.get("created_at") or ""))
            out = t.get("output_path") or ""
            name_item = QTableWidgetItem(Path(out).name if out else "—")
            if out:
                name_item.setToolTip(str(out))
            self.table.setItem(row, 4, name_item)
            self.table.setCellWidget(row, 5, self._make_actions(t["id"], st))
        from collections import Counter
        c = Counter((t.get("status") or "") for t in tasks)
        self.lbl_count.setText("  |  ".join(f"{k} {v}" for k, v in c.items()) if c else "暂无任务")
        self._kickoff_thumbnails(tasks)

    def _load_thumb(self, item, task: dict):
        """成功任务：GIF 直读首帧；视频用抽帧缓存"""
        if task.get("status") != "成功":
            return
        out = task.get("output_path") or ""
        if not out:
            return
        if str(out).lower().endswith(".gif"):
            pix = QtGui.QPixmap(out)
        else:
            thumb = self._thumb_path(task["id"])
            pix = QtGui.QPixmap(str(thumb)) if thumb.exists() else QtGui.QPixmap()
        if not pix.isNull():
            item.setIcon(QtGui.QIcon(pix))

    def _kickoff_thumbnails(self, tasks):
        if self._thumb_busy:
            return
        jobs = []
        for t in tasks:
            if t.get("status") == "成功" and t.get("output_path"):
                out = t["output_path"]
                if str(out).lower().endswith(".gif"):
                    continue   # GIF 面板图标直读首帧，无需抽帧
                if not self._thumb_path(t["id"]).exists() and Path(out).exists():
                    jobs.append((t["id"], out))
        if not jobs:
            return
        self._thumb_busy = True
        self._thumb_worker = ThumbExtractor(jobs)
        self._thumb_worker.done.connect(self._on_thumbs_done)
        self._thumb_worker.start()

    def _on_thumbs_done(self):
        self._thumb_busy = False
        self.refresh()

    def _on_cell_double_click(self, row, col):
        if col != 0:
            return
        item = self.table.item(row, 0)
        st_item = self.table.item(row, 2)
        if not item or not st_item or st_item.text() != "成功":
            return
        tid = item.data(Qt.UserRole)
        if tid is not None:
            self._show_task_preview(int(tid))

    def _make_actions(self, tid: int, status: str):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(2, 2, 2, 2)
        h.setSpacing(4)
        btn_r = QPushButton("恢复")
        btn_r.clicked.connect(lambda *a, tid=tid: self.workbench._restore_task(tid))
        h.addWidget(btn_r)
        if status == "进行中":
            btn_t = QPushButton("终止")
            btn_t.setStyleSheet("color:#e74c3c;")
            btn_t.clicked.connect(lambda *a, tid=tid: self.workbench._terminate_task(tid))
            h.addWidget(btn_t)
        else:
            btn_d = QPushButton("删除")
            btn_d.setStyleSheet("color:#e74c3c;")
            btn_d.clicked.connect(lambda *a, tid=tid: self.workbench._delete_task(tid))
            h.addWidget(btn_d)
        return w

    def _show_task_preview(self, start_tid):
        wb = self.workbench
        if not wb.project:
            return
        tasks = [t for t in wb.task_manager.list_for_project(wb.project.id)
                 if t.get("status") == "成功" and t.get("output_path")]
        if not tasks:
            return
        ids = [t["id"] for t in tasks]
        try:
            pos = ids.index(start_tid)
        except ValueError:
            pos = 0

        dlg = QDialog(self)
        dlg.setWindowTitle("任务预览")
        dlg.setMinimumSize(560, 440)
        dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(8, 8, 8, 8)

        # GIF 用 QMovie 动图；视频显示抽帧拼图（_ZoomImage 自适应窗口 + Ctrl+滚轮缩放）
        lbl_img = _ZoomImage()
        layout.addWidget(lbl_img, stretch=1)

        movie = {"obj": None}

        ctrl = QHBoxLayout()
        btn_open = QPushButton("播放")
        btn_open.setFocusPolicy(Qt.NoFocus)
        btn_open.setVisible(False)
        ctrl.addWidget(btn_open)
        ctrl.addStretch()
        info_lbl = QLabel()
        info_lbl.setStyleSheet("color:#7f8c8d;")
        ctrl.addWidget(info_lbl)
        ctrl.addStretch()
        btn_prev = QPushButton("◀ 上一张")
        btn_prev.setFocusPolicy(Qt.NoFocus)
        btn_next = QPushButton("下一张 ▶")
        btn_next.setFocusPolicy(Qt.NoFocus)
        ctrl.addWidget(btn_prev)
        ctrl.addWidget(btn_next)
        hint_lbl = QLabel("←→ 切换 · Del 删除")
        hint_lbl.setStyleSheet("color:#bdc3c7;")
        ctrl.addWidget(hint_lbl)
        layout.addLayout(ctrl)
        dlg.setFocusPolicy(Qt.StrongFocus)
        dlg.setFocus()

        state = {"pos": pos, "ids": ids, "out": "", "viewing": None, "outs": {}, "alive": True}

        def stop_current():
            if movie["obj"]:
                movie["obj"].stop()
                movie["obj"] = None

        def open_player():
            out = state.get("out")
            if out:
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(out))

        def load(p):
            n = len(state["ids"])
            if n == 0:
                dlg.close()
                return
            if p < 0 or p >= n:
                return
            state["pos"] = p
            stop_current()
            tid = state["ids"][p]
            state["viewing"] = tid
            tinfo = wb.task_manager.get(tid) or {}
            out = tinfo.get("output_path") or ""
            state["out"] = out
            state["outs"][tid] = out
            is_gif = out.lower().endswith(".gif")
            info_lbl.setText(f"{tinfo.get('tag', '')} · {Path(out).name if out else ''}")
            dlg.setWindowTitle(f"任务预览 ({p + 1}/{n})")
            lbl_img.setMovie(None)
            lbl_img.clearImage()
            if is_gif:
                m = QtGui.QMovie(out)
                if m.isValid():
                    lbl_img.setMovie(m)
                    m.start()
                    movie["obj"] = m
                else:
                    lbl_img.setText("(无法加载动图)")
                btn_open.setVisible(False)
            else:
                # 视频：按时长分级（单帧 / 多帧拼图）+ 播放按钮
                btn_open.setVisible(True)
                dur = ThumbExtractor._probe_duration(out)
                n_frames, cols, rows = _sheet_grid(dur)
                if n_frames > 0:
                    sheet = self._sheet_path(tid)
                    pix = QtGui.QPixmap(str(sheet)) if sheet.exists() else QtGui.QPixmap()
                else:
                    # 太短：用单帧（中间帧）
                    tp = self._thumb_path(tid)
                    if not tp.exists():
                        self._extract_thumb_sync(tid, out)
                    pix = QtGui.QPixmap(str(tp)) if tp.exists() else QtGui.QPixmap()
                if not pix.isNull():
                    lbl_img.setFullPixmap(pix)
                elif n_frames > 0:
                    # 拼图未缓存：后台抽帧，完成后主线程拼接并展示
                    lbl_img.setText("正在生成预览拼图…")
                    worker = _PreviewFrameExtractor(tid, out, n_frames)

                    def on_done(done_tid, _state=state, _lbl=lbl_img, _w=worker, _c=cols, _r=rows):
                        self._finalize_contact_sheet(done_tid, _c, _r)
                        try:
                            self._sheet_workers.remove(_w)
                        except Exception:
                            pass
                        if not _state.get("alive") or _state.get("viewing") != done_tid:
                            return
                        sh = self._sheet_path(done_tid)
                        p2 = QtGui.QPixmap(str(sh)) if sh.exists() else QtGui.QPixmap()
                        if p2.isNull():
                            _lbl.setText("(无缩略图)")
                        else:
                            _lbl.setFullPixmap(p2)

                    worker.done.connect(on_done)
                    self._sheet_workers.append(worker)
                    worker.start()
                else:
                    lbl_img.setText("(无缩略图)")
            btn_prev.setEnabled(p > 0)
            btn_next.setEnabled(p < n - 1)

        def go_prev():
            if state["pos"] > 0:
                load(state["pos"] - 1)

        def go_next():
            if state["pos"] < len(state["ids"]) - 1:
                load(state["pos"] + 1)

        def delete_cur():
            if not state["ids"]:
                return
            tid = state["ids"][state["pos"]]
            wb._delete_task(tid)
            try:
                self._thumb_path(tid).unlink()
            except Exception:
                pass
            state["ids"].pop(state["pos"])
            if not state["ids"]:
                dlg.close()
                return
            if state["pos"] >= len(state["ids"]):
                state["pos"] = len(state["ids"]) - 1
            load(state["pos"])

        btn_prev.clicked.connect(go_prev)
        btn_next.clicked.connect(go_next)
        btn_open.clicked.connect(open_player)

        def key(event):
            k = event.key()
            if k == Qt.Key_Left:
                go_prev()
            elif k == Qt.Key_Right:
                go_next()
            elif k == Qt.Key_Delete:
                delete_cur()
            elif k == Qt.Key_Escape:
                dlg.close()
            else:
                QDialog.keyPressEvent(dlg, event)

        dlg.keyPressEvent = key

        def on_finished(*_):
            state["alive"] = False
            stop_current()
        dlg.finished.connect(on_finished)
        load(pos)
        dlg.exec_()


class WorkbenchPage(QWidget):
    """剪辑工作台：剪辑时强制要求演员"""
    back_signal = pyqtSignal()
    theme_toggled = pyqtSignal()

    def __init__(self, manager: ProjectManager, actor_manager: ActorManager):
        super().__init__()
        self.manager = manager
        self.actor_manager = actor_manager
        self.project: Optional[Project] = None
        self._workers: list = []  # 后台任务列表，支持并行
        self.task_manager = TaskManager()
        self._running_tasks: dict = {}  # task_id -> {worker, engine, tag, output_path, terminated}
        self._task_dlg = None           # 任务列表面板（打开时引用）
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 顶部信息栏
        info_bar = QHBoxLayout()

        self.lbl_proj_title = QLabel("-")
        self.lbl_proj_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        info_bar.addWidget(self.lbl_proj_title, stretch=1)

        btn_edit = QPushButton("编辑")
        btn_edit.setToolTip("编辑项目信息")
        btn_edit.clicked.connect(self._on_edit_project)
        info_bar.addWidget(btn_edit)

        btn_archive = QPushButton("归档")
        btn_archive.setToolTip("按国家→演员→电影归类整理输出目录中的文件")
        btn_archive.clicked.connect(self._on_archive)
        info_bar.addWidget(btn_archive)

        btn_tasks = QPushButton("任务")
        btn_tasks.setToolTip("查看/管理任务：进行中·成功·失败·未进行；可恢复、终止、删除")
        btn_tasks.clicked.connect(self._open_task_panel)
        info_bar.addWidget(btn_tasks)

        btn_back = QPushButton("退出")
        btn_back.clicked.connect(self.back_signal.emit)
        info_bar.addWidget(btn_back)

        btn_theme = QPushButton("🌙")
        btn_theme.setObjectName("btn_theme_wb")
        btn_theme.setFixedSize(32, 32)
        btn_theme.setToolTip("切换夜间模式")
        btn_theme.setStyleSheet(
            "QPushButton { font-size: 16px; border: none; background: transparent; }"
            "QPushButton:hover { background: #e0e0e0; border-radius: 16px; }"
        )
        btn_theme.clicked.connect(self.theme_toggled.emit)
        info_bar.addWidget(btn_theme)

        layout.addLayout(info_bar)

        meta_bar = QHBoxLayout()
        self.lbl_proj_source = QLabel("-")
        self.lbl_proj_source.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        self.lbl_proj_source.setWordWrap(True)
        meta_bar.addWidget(self.lbl_proj_source, stretch=2)

        self.lbl_proj_target = QLabel("-")
        self.lbl_proj_target.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        meta_bar.addWidget(self.lbl_proj_target, stretch=1)

        layout.addLayout(meta_bar)

        # 剧集选择（仅剧集项目可见）
        self.episode_row = QWidget()
        ep_layout = QHBoxLayout(self.episode_row)
        ep_layout.setContentsMargins(0, 4, 0, 0)
        ep_layout.addWidget(QLabel("第"))
        self.ed_episode = QSpinBox()
        self.ed_episode.setRange(1, 999)
        self.ed_episode.setValue(1)
        self.ed_episode.valueChanged.connect(self._update_preview)
        ep_layout.addWidget(self.ed_episode)
        ep_layout.addWidget(QLabel("集"))
        ep_layout.addStretch()
        self.episode_row.setVisible(False)
        layout.addWidget(self.episode_row)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(line)

        # Tab 操作区（每个 Tab 内有独立的 ActorSelector）
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_gif_tab(), "GIF 制作")
        self.tabs.addTab(self._build_video_tab(), "视频剪辑")
        self.tabs.addTab(self._build_rename_tab(), "图片重命名")
        layout.addWidget(self.tabs, stretch=1)

        # 预览 + 执行 + 日志
        preview_box = QGroupBox("输出预览")
        preview_layout = QHBoxLayout(preview_box)
        self.lbl_preview = QLabel("-")
        self.lbl_preview.setStyleSheet(
            "font-family: Consolas, Monaco, monospace; "
            "font-size: 13px; color: #27ae60; "
            "padding: 8px; border-radius: 4px;"
        )
        self.lbl_preview.setWordWrap(True)
        preview_layout.addWidget(self.lbl_preview)
        layout.addWidget(preview_box)

        exec_bar = QHBoxLayout()
        self.btn_run = QPushButton("执行")
        self.btn_run.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; "
            "font-size: 14px; font-weight: bold; padding: 10px 24px; "
            "border-radius: 6px; }"
            "QPushButton:hover { background-color: #2980b9; }"
            "QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.btn_run.clicked.connect(self._on_execute)
        exec_bar.addWidget(self.btn_run)

        btn_open_dir = QPushButton("打开输出目录")
        btn_open_dir.clicked.connect(self._open_target_dir)
        exec_bar.addWidget(btn_open_dir)

        exec_bar.addStretch()
        layout.addLayout(exec_bar)

        log_box = QGroupBox("执行日志")
        log_layout = QVBoxLayout(log_box)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFont(QFont("Consolas", 10))
        self.txt_log.setStyleSheet("background-color: #2c3e50; color: #ecf0f1;")
        log_layout.addWidget(self.txt_log)
        layout.addWidget(log_box, stretch=1)

        # 信号连接放在所有 UI 元素创建完成后
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def load_project(self, project: Project):
        self.project = project
        self.project.resolve_actors(self.actor_manager)
        self.lbl_proj_title.setText(project.short_name)
        self.lbl_proj_source.setText(f"源: {project.source_file_path}")
        self.lbl_proj_target.setText(f"输出: {project.target_base_path}")

        # 传递项目已绑定演员到各 Tab 的 ActorSelector
        for i in range(self.tabs.count()):
            sel = self.tabs.widget(i).findChild(ActorSelector)
            if sel:
                sel.set_project_actor_ids(project.actor_ids)

        # 剧集项目显示集数选择
        self.episode_row.setVisible(project.is_series)

        self._update_preview()
        self.txt_log.clear()
        self.log(f"[INFO] 进入工作台: {project.display_name}")

        # 上次残留的「进行中」任务（进程已不存在）标记为「未进行」
        self.task_manager.mark_stale_running(project.id)

        # 恢复上次状态
        self._restore_state()

    def _build_state(self) -> dict:
        """构建当前工作台状态快照（保存项目状态 / 任务快照共用）"""
        segs = []
        if hasattr(self, 'table_segments'):
            segs = self._get_segments()
        state = {
            "tab": self.tabs.currentIndex(),
            "gif": {
                "start": self.ed_gif_start.text(),
                "end": self.ed_gif_end.text(),
                "width": self.cb_gif_width.currentText(),
                "fps": self.cb_gif_fps.currentText(),
                "colors": self.cb_gif_colors.currentText(),
                "brightness_enabled": self.chk_brightness.isChecked(),
                "brightness": self.spin_brightness.value(),
                "contrast_enabled": self.chk_contrast.isChecked(),
                "contrast": self.spin_contrast.value(),
                "speed_enabled": self.chk_speed.isChecked(),
                "speed": self.spin_speed.value(),
            },
            "video": {
                "segments": segs,
                "copy": self.chk_copy.isChecked(),
                "no_audio": self.chk_no_audio.isChecked(),
                "aspect_enabled": self.chk_aspect.isChecked(),
                "aspect": self.cb_aspect.currentText(),
                "audio_idx_enabled": self.chk_audio_idx.isChecked(),
                "audio_idx": self.spin_audio_idx.value(),
            },
            "actors_per_tab": {}
        }
        for i in range(self.tabs.count()):
            sel = self.tabs.widget(i).findChild(ActorSelector)
            if sel:
                state["actors_per_tab"][str(i)] = sel.get_actor_ids()
        return state

    def _snapshot_state_for_task(self) -> dict:
        """任务快照：仅当时间段只有一行且为未改动的默认占位（00:00:00.000–00:00:05.000）时才视为空；
        其余情况（含多段中混有 0–5s）原样保留。"""
        state = self._build_state()
        DEFAULT = ("00:00:00.000", "00:00:05.000")
        vid = state.get("video", {})
        segs = [tuple(s) for s in vid.get("segments", [])]
        if len(segs) == 1 and segs[0] == DEFAULT:
            vid["segments"] = []   # 仅初始占位，不算真实任务
        else:
            vid["segments"] = segs
        return state

    def _save_state(self):
        """保存当前工作台状态到数据库"""
        if not self.project:
            return
        import json
        state = self._build_state()
        self.manager.save_state(self.project.id, json.dumps(state, ensure_ascii=False))

    def _apply_state(self, state: dict):
        """把状态快照应用到工作台（恢复上次状态 / 恢复任务共用）"""
        # GIF 参数
        g = state.get("gif", {})
        if g:
            self.ed_gif_start.setText(g.get("start", "00:00:00.000"))
            self.ed_gif_end.setText(g.get("end", "00:00:05.000"))
            self.cb_gif_width.setCurrentText(g.get("width", "600"))
            self.cb_gif_fps.setCurrentText(g.get("fps", "30"))
            self.cb_gif_colors.setCurrentText(g.get("colors", "256"))
            self.chk_brightness.setChecked(g.get("brightness_enabled", False))
            self.spin_brightness.setValue(g.get("brightness", 0))
            self.chk_contrast.setChecked(g.get("contrast_enabled", False))
            self.spin_contrast.setValue(g.get("contrast", 1))
            self.chk_speed.setChecked(g.get("speed_enabled", False))
            self.spin_speed.setValue(g.get("speed", 1))
        # 视频参数
        v = state.get("video", {})
        if v:
            self.chk_copy.setChecked(v.get("copy", False))
            self.chk_no_audio.setChecked(v.get("no_audio", False))
            self.chk_aspect.setChecked(v.get("aspect_enabled", False))
            self.cb_aspect.setCurrentText(v.get("aspect", "16:9"))
            self.chk_audio_idx.setChecked(v.get("audio_idx_enabled", False))
            self.spin_audio_idx.setValue(v.get("audio_idx", 1))
            segs = v.get("segments", [])
            if segs and hasattr(self, 'table_segments'):
                self.table_segments.blockSignals(True)
                self.table_segments.setRowCount(0)
                for s, e in segs:
                    r = self.table_segments.rowCount()
                    self.table_segments.insertRow(r)
                    self.table_segments.setItem(r, 0, QTableWidgetItem(s))
                    self.table_segments.setItem(r, 1, QTableWidgetItem(e))
                self.table_segments.blockSignals(False)
                if hasattr(self, '_segment_undo_stack'):
                    self._segment_undo_stack.clear()
        # 各 Tab 演员选择
        ap = state.get("actors_per_tab", {})
        for i_str, ids in ap.items():
            i = int(i_str)
            if i < self.tabs.count():
                sel = self.tabs.widget(i).findChild(ActorSelector)
                if sel:
                    sel.set_actor_ids(ids)
        # Tab
        self.tabs.setCurrentIndex(state.get("tab", 0))
        self._update_preview()

    def _restore_state(self):
        """从数据库恢复上次工作台状态"""
        if not self.project:
            return
        import json
        raw = self.manager.load_state(self.project.id)
        if not raw:
            return
        try:
            state = json.loads(raw)
        except Exception:
            return
        self._apply_state(state)

    def _on_edit_project(self):
        if not self.project:
            return
        dlg = ProjectDialog(self, self.project, self.actor_manager)
        if dlg.exec_() == QDialog.Accepted:
            new_proj = dlg.get_project()
            new_proj._data["id"] = self.project.id
            new_proj._data["slug"] = self.project.slug
            self.manager.save(new_proj)
            self.load_project(new_proj)
            QMessageBox.information(self, "成功", "项目信息已更新")

    def _build_gif_tab(self) -> QWidget:
        tab = QWidget()
        hbox = QHBoxLayout(tab)
        hbox.setSpacing(12)

        # === 左侧：剪辑参数 ===
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        row_time = QHBoxLayout()
        row_time.addWidget(QLabel("起始时间:"))
        self.ed_gif_start = QLineEdit("00:00:00.000")
        self.ed_gif_start.textChanged.connect(self._update_preview)
        row_time.addWidget(self.ed_gif_start)
        row_time.addWidget(QLabel("结束时间:"))
        self.ed_gif_end = QLineEdit("00:00:05.000")
        self.ed_gif_end.textChanged.connect(self._update_preview)
        row_time.addWidget(self.ed_gif_end)
        left_layout.addLayout(row_time)

        row_param = QHBoxLayout()
        row_param.addWidget(QLabel("宽度:"))
        self.cb_gif_width = QComboBox()
        self.cb_gif_width.addItems(["320", "480", "600", "720"])
        self.cb_gif_width.setCurrentText("600")
        self.cb_gif_width.currentTextChanged.connect(self._update_preview)
        row_param.addWidget(self.cb_gif_width)
        row_param.addWidget(QLabel("帧率:"))
        self.cb_gif_fps = QComboBox()
        self.cb_gif_fps.addItems(["10", "15", "24", "30"])
        self.cb_gif_fps.setCurrentText("30")
        self.cb_gif_fps.currentTextChanged.connect(self._update_preview)
        row_param.addWidget(self.cb_gif_fps)
        row_param.addWidget(QLabel("颜色:"))
        self.cb_gif_colors = QComboBox()
        self.cb_gif_colors.addItems(["32", "64", "128", "256"])
        self.cb_gif_colors.setCurrentText("256")
        self.cb_gif_colors.currentTextChanged.connect(self._update_preview)
        row_param.addWidget(self.cb_gif_colors)
        row_param.addStretch()
        left_layout.addLayout(row_param)

        adv = QGroupBox("画面调整")
        adv_layout = QGridLayout(adv)
        self.chk_brightness = QCheckBox("亮度")
        self.spin_brightness = QDoubleSpinBox()
        self.spin_brightness.setRange(-1.0, 1.0)
        self.spin_brightness.setSingleStep(0.1)
        self.spin_brightness.setValue(0)
        adv_layout.addWidget(self.chk_brightness, 0, 0)
        adv_layout.addWidget(self.spin_brightness, 0, 1)
        self.chk_contrast = QCheckBox("对比度")
        self.spin_contrast = QDoubleSpinBox()
        self.spin_contrast.setRange(0.0, 2.0)
        self.spin_contrast.setSingleStep(0.1)
        self.spin_contrast.setValue(1)
        adv_layout.addWidget(self.chk_contrast, 0, 2)
        adv_layout.addWidget(self.spin_contrast, 0, 3)
        self.chk_speed = QCheckBox("速度")
        self.spin_speed = QDoubleSpinBox()
        self.spin_speed.setRange(0.1, 10.0)
        self.spin_speed.setSingleStep(0.1)
        self.spin_speed.setValue(1)
        adv_layout.addWidget(self.chk_speed, 1, 0)
        adv_layout.addWidget(self.spin_speed, 1, 1)
        adv_layout.setColumnStretch(4, 1)
        left_layout.addWidget(adv)
        left_layout.addStretch()
        btn_save_gif = QPushButton("保存当前任务")
        btn_save_gif.setToolTip("把当前 GIF 配置存为一个「未进行」任务，便于以后恢复")
        btn_save_gif.clicked.connect(self._save_task_preset)
        _save_row = QHBoxLayout()
        _save_row.addStretch()
        _save_row.addWidget(btn_save_gif)
        left_layout.addLayout(_save_row)

        for w in [self.chk_brightness, self.spin_brightness, self.chk_contrast,
                  self.spin_contrast, self.chk_speed, self.spin_speed]:
            if isinstance(w, QCheckBox):
                w.stateChanged.connect(self._update_preview)
            else:
                w.valueChanged.connect(self._update_preview)

        # === 右侧：演员选择 ===
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        actor_sel = ActorSelector(self.actor_manager, copy_list_button=True)
        actor_sel.actors_changed.connect(self._update_preview)
        actor_sel.actors_changed.connect(lambda s=actor_sel: self._save_tab_actors(s))
        right_layout.addWidget(actor_sel)
        right_layout.addStretch()

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #ccd5de;")
        hbox.addWidget(left, stretch=6)
        hbox.addWidget(sep)
        hbox.addWidget(right, stretch=4)
        return tab

    def _build_video_tab(self) -> QWidget:
        tab = QWidget()
        hbox = QHBoxLayout(tab)
        hbox.setSpacing(12)

        # === 左侧：剪辑参数 ===
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.table_segments = QTableWidget(0, 2)
        self.table_segments.setHorizontalHeaderLabels(["起始时间", "结束时间"])
        self.table_segments.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_segments.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_segments.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table_segments.itemChanged.connect(self._update_preview)
        self._segment_undo_stack = []   # Del 删除前的行快照栈，供 Ctrl+Z 撤销
        # 快捷键（编辑单元格时由编辑器处理，不会触发）：
        # Del 删除选中 / Ctrl+Z 撤销删除 / Ctrl+↑↓ 上下移动 / Ctrl+C 复制 / Ctrl+D 新增
        def _seg_keypress(event):
            key = event.key()
            ctrl = bool(event.modifiers() & Qt.ControlModifier)
            if key == Qt.Key_Delete:
                self._del_segment_row()
            elif ctrl and key == Qt.Key_Z:
                self._undo_segment_delete()
            elif ctrl and key == Qt.Key_Up:
                self._move_segment_row(-1)
            elif ctrl and key == Qt.Key_Down:
                self._move_segment_row(1)
            elif ctrl and key == Qt.Key_C:
                self._copy_segments()
            elif ctrl and key == Qt.Key_D:
                self._add_segment_row()
            else:
                QTableWidget.keyPressEvent(self.table_segments, event)
        self.table_segments.keyPressEvent = _seg_keypress
        self.table_segments.setMinimumHeight(280)
        left_layout.addWidget(self.table_segments, stretch=1)

        btn_bar = QHBoxLayout()
        btn_add = QPushButton("添加")
        btn_add.setToolTip("添加一个时间段")
        btn_add.clicked.connect(self._add_segment_row)
        btn_bar.addWidget(btn_add)
        btn_del = QPushButton("删除")
        btn_del.setToolTip("删除选中的时间段")
        btn_del.clicked.connect(self._del_segment_row)
        btn_bar.addWidget(btn_del)
        btn_load = QPushButton("导入")
        btn_load.setToolTip("从文本批量导入时间段")
        btn_load.clicked.connect(self._load_segments_from_text)
        btn_bar.addWidget(btn_load)
        btn_bar.addSpacing(8)
        btn_up = QPushButton("上移")
        btn_up.setToolTip("上移选中段")
        btn_up.clicked.connect(lambda: self._move_segment_row(-1))
        btn_bar.addWidget(btn_up)
        btn_down = QPushButton("下移")
        btn_down.setToolTip("下移选中段")
        btn_down.clicked.connect(lambda: self._move_segment_row(1))
        btn_bar.addWidget(btn_down)
        btn_sort = QPushButton("排序")
        btn_sort.setToolTip("按起始时间排序")
        btn_sort.clicked.connect(self._sort_segments)
        btn_bar.addWidget(btn_sort)
        btn_copy = QPushButton("复制")
        btn_copy.setToolTip("复制选中段（导入格式）")
        btn_copy.clicked.connect(self._copy_segments)
        btn_bar.addWidget(btn_copy)
        btn_bar.addStretch()
        self.lbl_vid_warn = QLabel("")
        self.lbl_vid_warn.setStyleSheet("color: #e67e22; font-size: 12px;")
        self.lbl_vid_warn.setMaximumWidth(260)
        self.lbl_vid_warn.setWordWrap(False)
        self.lbl_vid_warn.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        self.lbl_vid_warn.mousePressEvent = self._on_warn_clicked
        btn_bar.addWidget(self.lbl_vid_warn)
        left_layout.addLayout(btn_bar)

        opts = QGroupBox("选项")
        opts_layout = QGridLayout(opts)
        self.chk_copy = QCheckBox("流复制")
        self.chk_copy.setToolTip("-codec copy")
        self.chk_copy.stateChanged.connect(self._update_preview)
        opts_layout.addWidget(self.chk_copy, 0, 0)
        self.chk_no_audio = QCheckBox("去音轨")
        self.chk_no_audio.setToolTip("-an")
        self.chk_no_audio.stateChanged.connect(self._update_preview)
        opts_layout.addWidget(self.chk_no_audio, 0, 1)
        self.chk_aspect = QCheckBox("比例")
        self.chk_aspect.setToolTip("强制宽高比 (-aspect)")
        self.chk_aspect.stateChanged.connect(self._update_preview)
        self.cb_aspect = QComboBox()
        self.cb_aspect.addItems(["16:9", "4:3", "1:1"])
        self.cb_aspect.currentTextChanged.connect(self._update_preview)
        opts_layout.addWidget(self.chk_aspect, 1, 0)
        opts_layout.addWidget(self.cb_aspect, 1, 1)
        self.chk_audio_idx = QCheckBox("音轨")
        self.chk_audio_idx.setToolTip("指定音轨索引 (-map 0:a:N)")
        self.chk_audio_idx.stateChanged.connect(self._update_preview)
        self.spin_audio_idx = QSpinBox()
        self.spin_audio_idx.setMinimum(1)
        self.spin_audio_idx.setValue(1)
        self.spin_audio_idx.valueChanged.connect(self._update_preview)
        opts_layout.addWidget(self.chk_audio_idx, 1, 2)
        opts_layout.addWidget(self.spin_audio_idx, 1, 3)
        opts_layout.setColumnStretch(4, 1)
        left_layout.addWidget(opts)
        left_layout.addStretch()
        btn_save_vid = QPushButton("保存当前任务")
        btn_save_vid.setToolTip("把当前视频剪辑配置存为一个「未进行」任务，便于以后恢复")
        btn_save_vid.clicked.connect(self._save_task_preset)
        _save_row = QHBoxLayout()
        _save_row.addStretch()
        _save_row.addWidget(btn_save_vid)
        left_layout.addLayout(_save_row)

        # === 右侧：演员选择 ===
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        actor_sel = ActorSelector(self.actor_manager, copy_list_button=True)
        actor_sel.actors_changed.connect(self._update_preview)
        actor_sel.actors_changed.connect(lambda s=actor_sel: self._save_tab_actors(s))
        right_layout.addWidget(actor_sel)
        right_layout.addStretch()

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #ccd5de;")
        hbox.addWidget(left, stretch=6)
        hbox.addWidget(sep)
        hbox.addWidget(right, stretch=4)

        self._add_segment_row()
        return tab

    def _build_rename_tab(self) -> QWidget:
        """图片批量重命名 Tab"""
        tab = QWidget()
        hbox = QHBoxLayout(tab)
        hbox.setSpacing(12)

        # === 左侧：主操作区 ===
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # 目录选择行
        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("图片目录:"))
        self.ed_rename_dir = QLineEdit()
        self.ed_rename_dir.setPlaceholderText("默认为项目输出目录，可临时修改…")
        self.ed_rename_dir.setToolTip("修改后点击「刷新」扫描新目录")
        dir_row.addWidget(self.ed_rename_dir, stretch=1)
        btn_browse_dir = QPushButton("浏览")
        btn_browse_dir.clicked.connect(self._pick_rename_dir)
        dir_row.addWidget(btn_browse_dir)
        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self._scan_rename_images)
        dir_row.addWidget(btn_refresh)
        left_layout.addLayout(dir_row)

        # 搜索过滤 + 选择按钮
        view_row = QHBoxLayout()

        self.ed_rename_filter = QLineEdit()
        self.ed_rename_filter.setPlaceholderText("搜索文件名…")
        self.ed_rename_filter.setClearButtonEnabled(True)
        self.ed_rename_filter.textChanged.connect(self._on_rename_filter_changed)
        view_row.addWidget(self.ed_rename_filter, stretch=1)

        self.lbl_rename_count = QLabel("")
        self.lbl_rename_count.setStyleSheet("color: #7f8c8d;")
        view_row.addWidget(self.lbl_rename_count)

        btn_sel_all = QPushButton("全选")
        btn_sel_all.clicked.connect(lambda: self._select_all_rename(True))
        view_row.addWidget(btn_sel_all)
        btn_sel_none = QPushButton("清除全选")
        btn_sel_none.clicked.connect(lambda: self._select_all_rename(False))
        view_row.addWidget(btn_sel_none)
        left_layout.addLayout(view_row)

        # 排序 + 过滤选项
        sort_row = QHBoxLayout()

        self.btn_sort_time = QPushButton("时间 ↓")
        self.btn_sort_time.setToolTip("按修改时间排序，点击切换正/逆序")
        self.btn_sort_time.clicked.connect(lambda: self._sort_rename("time"))
        sort_row.addWidget(self.btn_sort_time)
        self.btn_sort_name = QPushButton("名称 ↑")
        self.btn_sort_name.setToolTip("按文件名排序，点击切换正/逆序")
        self.btn_sort_name.clicked.connect(lambda: self._sort_rename("name"))
        sort_row.addWidget(self.btn_sort_name)

        sort_row.addSpacing(16)

        self.chk_hide_renamed = QCheckBox("隐藏已重命名的图片")
        self.chk_hide_renamed.setChecked(True)
        self.chk_hide_renamed.stateChanged.connect(lambda: self._populate_rename_views())
        sort_row.addWidget(self.chk_hide_renamed)

        self.chk_ext_jpg = QCheckBox("jpg")
        self.chk_ext_jpg.setChecked(True)
        self.chk_ext_jpg.stateChanged.connect(lambda: self._populate_rename_views())
        sort_row.addWidget(self.chk_ext_jpg)
        self.chk_ext_png = QCheckBox("png")
        self.chk_ext_png.setChecked(True)
        self.chk_ext_png.stateChanged.connect(lambda: self._populate_rename_views())
        sort_row.addWidget(self.chk_ext_png)

        sort_row.addStretch()
        left_layout.addLayout(sort_row)

        # 详细列表（缩略图 + 文件名 + 新文件名）
        self.detail_table = QTableWidget(0, 4)
        self.detail_table.setHorizontalHeaderLabels(["", "缩略图", "当前文件名", "新文件名"])
        self.detail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.detail_table.setColumnWidth(0, 30)
        self.detail_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.detail_table.setColumnWidth(1, 80)
        self.detail_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.detail_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.detail_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.detail_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.detail_table.verticalHeader().setDefaultSectionSize(60)
        self.detail_table.setStyleSheet("QTableWidget { border: 1px solid #dcdcdc; border-radius: 4px; }")
        self.detail_table.cellDoubleClicked.connect(self._on_rename_image_double_click)
        self.detail_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.detail_table.customContextMenuRequested.connect(self._on_rename_context_menu)
        left_layout.addWidget(self.detail_table, stretch=1)

        # === 右侧：演员选择 ===
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        actor_sel = ActorSelector(self.actor_manager, copy_list_button=True)
        actor_sel.actors_changed.connect(self._on_rename_actor_changed)
        actor_sel.actors_changed.connect(lambda s=actor_sel: self._save_tab_actors(s))
        right_layout.addWidget(actor_sel)
        right_layout.addStretch()

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #ccd5de;")
        hbox.addWidget(left, stretch=6)
        hbox.addWidget(sep)
        hbox.addWidget(right, stretch=4)

        # 内部状态
        self._rename_items = []          # [{path, checked, new_name, size, mtime, is_renamed}, ...]
        self._rename_dir = ""
        self._rename_filtered = []       # 当前过滤后可见的 _rename_items 索引列表
        self._rename_sort = ("time", False)  # (mode, ascending)，默认时间倒序
        self._rename_force_country = ""  # 无演员时强制使用的地区

        return tab

    def _sort_rename_items(self):
        """按当前排序方式排列 _rename_items"""
        mode, asc = self._rename_sort
        reverse = not asc
        if mode == "time":
            self._rename_items.sort(key=lambda it: it.get("mtime", 0), reverse=reverse)
        else:
            self._rename_items.sort(key=lambda it: it["path"].name.lower(), reverse=reverse)

    def _sort_rename(self, mode: str):
        """切换排序方式，同模式则切换正/逆序"""
        cur_mode, cur_asc = self._rename_sort
        if mode == cur_mode:
            self._rename_sort = (mode, not cur_asc)
        else:
            self._rename_sort = (mode, mode == "name")  # 名称默认正序，时间默认倒序
        # 更新按钮箭头
        t_asc = self._rename_sort == ("time", True)
        n_asc = self._rename_sort == ("name", True)
        self.btn_sort_time.setText("时间 " + ("↑" if t_asc else "↓"))
        self.btn_sort_name.setText("名称 " + ("↑" if n_asc else "↓"))
        self._sort_rename_items()
        self._populate_rename_views()
        self._update_preview()

    def _on_tab_changed(self, idx: int):
        """Tab 切换时更新预览，并在切到重命名 Tab 时重置目录并扫描"""
        if idx == 2:
            # 切到图片重命名 Tab：重置目录为项目输出目录
            if self.project:
                target = self.project.target_base_path
                self.ed_rename_dir.blockSignals(True)
                self.ed_rename_dir.setText(target)
                self.ed_rename_dir.blockSignals(False)
                self._rename_dir = target
                self._scan_rename_images()
        self._update_preview()

    def _scan_rename_images(self):
        """扫描目录中的图片文件"""
        if not hasattr(self, 'ed_rename_dir'):
            return

        dir_text = self.ed_rename_dir.text().strip()
        if not dir_text:
            self._rename_items = []
            self._populate_rename_views()
            return

        scan_dir = Path(dir_text)
        if not scan_dir.exists() or not scan_dir.is_dir():
            self._rename_items = []
            self._populate_rename_views()
            return

        self._rename_dir = dir_text

        # 获取源视频文件名（用于识别"未命名"图片）
        keyword = ""
        if self.project:
            src = Path(self.project.source_file_path)
            keyword = src.name  # e.g. "ABC-123.mp4"

        # 只处理 jpg / png
        IMG_EXTS = {'.png', '.jpg', '.jpeg'}
        import re
        # 已重命名的文件：匹配 [Country]... 格式
        RENAMED_RE = re.compile(r'^\[[A-Z]{2,4}\]')

        items = []
        for f in scan_dir.iterdir():
            if not f.is_file():
                continue
            if f.suffix.lower() not in IMG_EXTS:
                continue
            is_renamed = bool(RENAMED_RE.match(f.name))
            # 未重命名且匹配源视频关键词 → 默认勾选
            is_unnamed = bool(not is_renamed and keyword and
                             (f.name.startswith(keyword) or f.name.startswith(Path(keyword).stem)))
            items.append({
                "path": f,
                "checked": is_unnamed,
                "new_name": "",
                "size": f.stat().st_size,
                "mtime": f.stat().st_mtime,
                "is_renamed": is_renamed,
            })

        self._rename_items = items
        self._sort_rename_items()
        self._populate_rename_views()
        self._update_preview()

    def _populate_rename_views(self):
        """根据 _rename_items 填充详细列表"""
        if not hasattr(self, 'detail_table'):
            return

        self._recalc_rename_names()

        # 构建过滤索引列表（子串匹配，忽略大小写）
        filter_text = self.ed_rename_filter.text().strip().lower() if hasattr(self, 'ed_rename_filter') else ""
        if filter_text:
            self._rename_filtered = [
                i for i, it in enumerate(self._rename_items)
                if filter_text in it["path"].name.lower()
            ]
        else:
            self._rename_filtered = list(range(len(self._rename_items)))
        # 隐藏已重命名
        if hasattr(self, 'chk_hide_renamed') and self.chk_hide_renamed.isChecked():
            self._rename_filtered = [
                i for i in self._rename_filtered
                if not self._rename_items[i].get("is_renamed")
            ]
        # 按后缀筛选
        if hasattr(self, 'chk_ext_jpg'):
            allowed = set()
            if self.chk_ext_jpg.isChecked():
                allowed.update({'.jpg', '.jpeg'})
            if self.chk_ext_png.isChecked():
                allowed.add('.png')
            if allowed:
                self._rename_filtered = [
                    i for i in self._rename_filtered
                    if self._rename_items[i]["path"].suffix.lower() in allowed
                ]

        self.detail_table.blockSignals(True)
        self.detail_table.setRowCount(0)
        self.detail_table.setRowCount(len(self._rename_filtered))

        for row, idx in enumerate(self._rename_filtered):
            item = self._rename_items[idx]
            fpath = item["path"]

            # 复选框
            chk = QCheckBox()
            chk.setChecked(item["checked"])
            if item.get("is_renamed"):
                chk.setToolTip("已按命名规则重命名")
            chk.stateChanged.connect(lambda state, p=str(fpath): self._on_rename_check_toggled(p, state == Qt.Checked))
            self.detail_table.setCellWidget(row, 0, chk)

            # 缩略图占位（延迟加载）
            placeholder = QLabel("…")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #ccc;")
            self.detail_table.setCellWidget(row, 1, placeholder)

            # 当前文件名
            name_item = QTableWidgetItem(fpath.name)
            name_item.setToolTip(str(fpath))
            self.detail_table.setItem(row, 2, name_item)

            # 状态 / 新文件名
            if item["checked"]:
                status_text = item["new_name"] or "(待重命名)"
                status_color = "#27ae60"
            elif item.get("is_renamed"):
                status_text = "已重命名"
                status_color = "#95a5a6"
            else:
                status_text = "未重命名"
                status_color = "#e67e22"
            new_item = QTableWidgetItem(status_text)
            new_item.setForeground(QtGui.QColor(status_color))
            self.detail_table.setItem(row, 3, new_item)

        self.detail_table.blockSignals(False)

        # 更新计数标签
        checked = sum(1 for it in self._rename_items if it["checked"])
        total = len(self._rename_items)
        renamed = sum(1 for it in self._rename_items if it.get("is_renamed"))
        shown = len(self._rename_filtered)
        parts = [f"已选 {checked}"]
        if renamed:
            parts.append(f"已重命名 {renamed}")
        if shown < total:
            parts.insert(0, f"显示 {shown}/{total}")
        else:
            parts.insert(0, f"共 {total}")
        self.lbl_rename_count.setText("  |  ".join(parts))

        # 延迟分批加载缩略图，避免阻塞 UI
        self._lazy_thumb_batch = 0
        self._lazy_thumb_total = len(self._rename_filtered)
        self._lazy_load_thumbnails()

    def _lazy_load_thumbnails(self):
        """分批加载缩略图（每批 8 张），不阻塞 UI"""
        BATCH = 8
        start = self._lazy_thumb_batch
        end = min(start + BATCH, self._lazy_thumb_total)

        # 安全检查：表格行数必须与过滤后数量一致，防止旧回调误写
        if self.detail_table.rowCount() != self._lazy_thumb_total:
            return

        for row in range(start, end):
            if row >= len(self._rename_filtered) or row >= self.detail_table.rowCount():
                break
            idx = self._rename_filtered[row]
            if idx >= len(self._rename_items):
                break
            fpath = self._rename_items[idx]["path"]
            try:
                pix = QtGui.QPixmap(str(fpath))
                if not pix.isNull():
                    pix = pix.scaled(70, 52, Qt.KeepAspectRatio, Qt.FastTransformation)
                    lbl = QLabel()
                    lbl.setPixmap(pix)
                    lbl.setAlignment(Qt.AlignCenter)
                    self.detail_table.setCellWidget(row, 1, lbl)
            except Exception:
                pass

        self._lazy_thumb_batch = end
        if self._lazy_thumb_batch < self._lazy_thumb_total:
            QTimer.singleShot(10, self._lazy_load_thumbnails)

    def _recalc_rename_names(self, force_country: str = ""):
        """为勾选的文件计算新文件名（Project 复用，编号自动顺延已有文件）"""
        if not self._rename_items:
            return

        # 构建 Project 一次复用
        proj = None
        if self.project:
            sel = self._get_current_actor_selector()
            actor_ids = sel.get_actor_ids() if sel else []
            display_names = self._resolve_display_names(actor_ids)
            country = ""
            if actor_ids:
                first = self.actor_manager.get(actor_ids[0])
                if first:
                    country = first.country
            if not country:
                country = force_country or self._rename_force_country
            proj = Project(self.project._data.copy())
            proj.set_actor_ids(actor_ids)
            proj._actor_display_names = display_names
            proj._data["country"] = country
            ep = self._get_episode()
            if ep is not None:
                proj._data["episode"] = ep

        # 统一扩展名（取所有勾选文件最常见的）
        ext = "png"
        for item in self._rename_items:
            if item["checked"]:
                ext = item["path"].suffix.lstrip('.')
                break

        # 扫描已有文件，顺延编号
        count = self._find_next_rename_count(proj, ext)

        for item in self._rename_items:
            if item["checked"]:
                if proj:
                    item["new_name"] = NamingEngine.image_name(proj, count, ext)
                else:
                    movie = NamingEngine._safe_name(self.project.movie) if self.project else "Movie"
                    item["new_name"] = f"{movie}-{count}.{ext}"
                count += 1
            else:
                item["new_name"] = ""

    def _find_next_rename_count(self, proj, ext: str) -> int:
        """扫描目录中已有同名文件，返回下一个可用编号"""
        if not proj:
            return 1
        scan_dir = Path(self._rename_dir) if self._rename_dir else (
            Path(self.project.target_base_path) if self.project else Path("."))
        if not scan_dir.exists():
            return 1

        # 用 count=0 生成模板提取前缀
        template = NamingEngine.image_name(proj, 0, ext)  # ...-0.png
        prefix = template.rsplit('-', 1)[0] + '-'         # ...前缀-
        suffix = '.' + ext

        max_n = 0
        for f in scan_dir.iterdir():
            if f.is_file() and f.name.startswith(prefix) and f.name.endswith(suffix):
                try:
                    n = int(f.name[len(prefix):-len(suffix)])
                    if n > max_n:
                        max_n = n
                except ValueError:
                    pass
        return max_n + 1

    def _on_rename_image_double_click(self, row: int, col: int):
        """双击表格行弹出图片预览，支持勾选和左右键切换"""
        if row < 0 or row >= len(self._rename_filtered):
            return
        self._show_image_preview(row)  # 传入过滤列表中的位置

    def _show_image_preview(self, pos: int):
        """图片预览对话框：勾选 + 左右键切换（在过滤结果内导航）"""
        total = len(self._rename_filtered)
        if total == 0 or pos < 0 or pos >= total:
            return

        # 预览窗口状态：pos 是 _rename_filtered 中的位置
        state = {"pos": pos}

        dlg = QDialog(self)
        dlg.setWindowTitle(f"图片预览 ({pos + 1}/{total})")
        dlg.setMinimumSize(400, 300)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(8, 8, 8, 8)

        # 图片显示区
        lbl_img = QLabel()
        lbl_img.setAlignment(Qt.AlignCenter)
        lbl_img.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lbl_img.setMinimumSize(380, 250)
        layout.addWidget(lbl_img, stretch=1)

        # 底部控制栏
        ctrl = QHBoxLayout()

        # 勾选框
        chk = QCheckBox("勾选此项")
        first_idx = self._rename_filtered[pos]
        chk.setChecked(self._rename_items[first_idx]["checked"])

        def on_check(chk_state):
            cur_idx = self._rename_filtered[state["pos"]]
            self._on_rename_check_toggled(str(self._rename_items[cur_idx]["path"]),
                                          chk_state == Qt.Checked)
        chk.stateChanged.connect(on_check)
        ctrl.addWidget(chk)

        ctrl.addStretch()

        # 信息标签
        info_lbl = QLabel()
        info_lbl.setStyleSheet("color: #7f8c8d;")
        ctrl.addWidget(info_lbl)

        ctrl.addStretch()

        # 导航按钮（NoFocus 避免吃掉方向键）
        btn_prev = QPushButton("◀ 上一张")
        btn_prev.setFocusPolicy(Qt.NoFocus)
        btn_next = QPushButton("下一张 ▶")
        btn_next.setFocusPolicy(Qt.NoFocus)
        ctrl.addWidget(btn_prev)
        ctrl.addWidget(btn_next)
        hint_lbl = QLabel("Del 删除·至回收站")
        hint_lbl.setStyleSheet("color: #bdc3c7;")
        ctrl.addWidget(hint_lbl)
        layout.addLayout(ctrl)
        # 对话框自己吃方向键
        dlg.setFocusPolicy(Qt.StrongFocus)
        dlg.setFocus()

        def load_image(p):
            """加载过滤列表中第 p 张图片"""
            total = len(self._rename_filtered)
            if p < 0 or p >= total:
                return
            state["pos"] = p
            idx = self._rename_filtered[p]
            fpath = self._rename_items[idx]["path"]
            try:
                pix = QtGui.QPixmap(str(fpath))
                if pix.isNull():
                    lbl_img.setText("(无法加载)")
                    return
                screen = QApplication.primaryScreen().availableGeometry()
                max_w = int(screen.width() * 0.72)
                max_h = int(screen.height() * 0.65)
                if pix.width() > max_w or pix.height() > max_h:
                    pix = pix.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                lbl_img.setPixmap(pix)
                dlg.setWindowTitle(f"图片预览 ({p + 1}/{total})")
                chk.setEnabled(True)
                chk.blockSignals(True)
                chk.setChecked(self._rename_items[idx]["checked"])
                chk.blockSignals(False)
                ritem = self._rename_items[idx]
                info_lbl.setStyleSheet("color: #7f8c8d;")
                info_lbl.setText(
                    f"{ritem['path'].name}  |  "
                    f"{ritem['size'] / 1024:.1f} KB  |  "
                    f"{pix.width()}×{pix.height()}"
                )
                btn_prev.setEnabled(p > 0)
                btn_next.setEnabled(p < total - 1)
            except Exception as e:
                lbl_img.setText(f"(加载失败: {e})")

        def go_prev():
            if state["pos"] > 0:
                load_image(state["pos"] - 1)

        def go_next():
            total = len(self._rename_filtered)
            if state["pos"] < total - 1:
                load_image(state["pos"] + 1)

        btn_prev.clicked.connect(go_prev)
        btn_next.clicked.connect(go_next)

        # 删除当前图片（移至回收站），不弹确认框
        def delete_current():
            cur = self._rename_filtered
            if not cur:
                return
            p = state["pos"]
            if p < 0 or p >= len(cur):
                return
            idx = cur[p]
            fpath = self._rename_items[idx]["path"]
            if not self._delete_rename_image(idx):
                info_lbl.setStyleSheet("color: #e74c3c;")
                info_lbl.setText(f"删除失败：{fpath.name}")
                return
            new_total = len(self._rename_filtered)
            if new_total == 0:
                # 无图片：保留对话框，显示提示，不关闭
                lbl_img.clear()
                lbl_img.setText("（无图片）")
                chk.blockSignals(True)
                chk.setChecked(False)
                chk.blockSignals(False)
                chk.setEnabled(False)
                btn_prev.setEnabled(False)
                btn_next.setEnabled(False)
                dlg.setWindowTitle("图片预览 (0/0)")
                info_lbl.setStyleSheet("color: #7f8c8d;")
                info_lbl.setText("")
                return
            if p >= new_total:
                p = new_total - 1
            load_image(p)

        # 键盘事件
        def key_handler(event):
            if event.key() == Qt.Key_Left:
                go_prev()
            elif event.key() == Qt.Key_Right:
                go_next()
            elif event.key() == Qt.Key_Delete:
                delete_current()
            elif event.key() == Qt.Key_Escape:
                dlg.close()
            elif event.key() == Qt.Key_Space:
                chk.toggle()
            else:
                QDialog.keyPressEvent(dlg, event)

        dlg.keyPressEvent = key_handler

        load_image(pos)
        dlg.exec_()

    def _delete_rename_image(self, idx: int) -> bool:
        """将 _rename_items 中第 idx 张图片移至回收站，并从列表移除；成功返回 True。"""
        if idx < 0 or idx >= len(self._rename_items):
            return False
        fpath = self._rename_items[idx]["path"]
        # PyQt5 的 moveToTrash 返回 (ok, 回收站内路径) 元组，取首位判断成功
        result = QtCore.QFile.moveToTrash(str(fpath))
        ok = result[0] if isinstance(result, tuple) else result
        if not ok:
            return False
        del self._rename_items[idx]
        self._populate_rename_views()
        self._update_preview()
        return True


    def _on_rename_check_toggled(self, file_path: str, checked: bool):
        """复选框切换：更新模型并重建表格"""
        for item in self._rename_items:
            if str(item["path"]) == file_path:
                item["checked"] = checked
                break
        self._recalc_rename_names()
        self._populate_rename_views()
        self._update_preview()

    def _select_all_rename(self, checked: bool):
        """全选 / 清除全选（仅作用于当前过滤显示的项，全选时跳过已重命名）"""
        for idx in self._rename_filtered:
            if idx < len(self._rename_items):
                if checked and self._rename_items[idx].get("is_renamed"):
                    continue
                self._rename_items[idx]["checked"] = checked
        self._recalc_rename_names()
        self._populate_rename_views()
        self._update_preview()

    def _on_rename_filter_changed(self, text: str):
        """搜索文字变化：先全部取消，再仅选中搜索结果中未重命名的文件"""
        t = text.strip().lower()
        if t:
            # 全部取消
            for it in self._rename_items:
                it["checked"] = False
            # 搜索结果中未重命名的自动勾选
            matching = [i for i, it in enumerate(self._rename_items) if t in it["path"].name.lower()]
            for idx in matching:
                if not self._rename_items[idx].get("is_renamed"):
                    self._rename_items[idx]["checked"] = True
            self._recalc_rename_names()
        self._populate_rename_views()
        self._update_preview()

    def _on_rename_context_menu(self, pos):
        """右键菜单：复制文件名 / 删除"""
        row = self.detail_table.rowAt(pos.y())
        if row < 0 or row >= len(self._rename_filtered):
            return
        idx = self._rename_filtered[row]
        item = self._rename_items[idx]
        fpath = item["path"]
        new_name = item["new_name"] or ""

        menu = QtWidgets.QMenu(self)
        act_copy_cur = menu.addAction("复制当前文件名")
        act_copy_new = menu.addAction("复制新文件名")
        if not new_name:
            act_copy_new.setEnabled(False)
        act_copy_path = menu.addAction("复制完整路径")
        menu.addSeparator()
        act_del = menu.addAction("删除（至回收站）")

        action = menu.exec_(self.detail_table.mapToGlobal(pos))
        if action == act_copy_cur:
            QApplication.clipboard().setText(fpath.name)
        elif action == act_copy_new and new_name:
            QApplication.clipboard().setText(new_name)
        elif action == act_copy_path:
            QApplication.clipboard().setText(str(fpath))
        elif action == act_del:
            if not self._delete_rename_image(idx):
                QMessageBox.warning(self, "删除失败", f"无法将文件移至回收站：\n{fpath.name}")

    def _pick_rename_dir(self):
        """浏览选择目录"""
        start = self.ed_rename_dir.text().strip() or (
            self.project.target_base_path if self.project else ""
        )
        path = QFileDialog.getExistingDirectory(self, "选择图片目录", start)
        if path:
            self.ed_rename_dir.setText(path)
            self._rename_dir = path
            self._scan_rename_images()

    def _on_rename_actor_changed(self):
        """演员变更时重新计算命名并刷新"""
        if self.tabs.currentIndex() != 2:
            return
        self._recalc_rename_names()
        self._populate_rename_views()
        self._update_preview()

    def _on_rename_execute(self):
        """执行批量重命名"""
        if not self._rename_items:
            QMessageBox.warning(self, "提示", "没有可重命名的文件")
            return

        checked_items = [it for it in self._rename_items if it["checked"]]
        if not checked_items:
            QMessageBox.warning(self, "提示", "请至少勾选一个文件")
            return

        # 无演员时弹窗选地区（与视频剪辑一致）
        sel = self._get_current_actor_selector()
        actor_ids = sel.get_actor_ids() if sel else []
        rename_country = ""
        if actor_ids:
            first = self.actor_manager.get(actor_ids[0])
            if first:
                rename_country = first.country
        if not rename_country:
            dlg = QDialog(self)
            dlg.setWindowTitle("选择地区")
            dlg.setMinimumWidth(300)
            dlg_layout = QVBoxLayout(dlg)
            dlg_layout.addWidget(QLabel("请指定地区："))
            cb = QComboBox()
            cb.addItems(["CHN", "JAP", "KOR", "WEST", "SLA", "SEA", "LTA"])
            dlg_layout.addWidget(cb)
            btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            btns.accepted.connect(dlg.accept)
            btns.rejected.connect(dlg.reject)
            dlg_layout.addWidget(btns)
            if dlg.exec_() != QDialog.Accepted:
                return
            self._rename_force_country = cb.currentText()
            # 用选定的地区重新计算命名并刷新
            self._populate_rename_views()
            # 重新获取 checked_items（new_name 已更新）
            checked_items = [it for it in self._rename_items if it["checked"]]

        # 确认
        msg = f"将重命名 {len(checked_items)} 个文件，确认执行？"

        reply = QMessageBox.question(self, "确认重命名", msg, QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # 执行重命名
        success = 0
        errors = []
        for item in checked_items:
            src = item["path"]
            dst = src.parent / item["new_name"]
            try:
                # 冲突处理：自动编号
                final_dst = PathHelper.get_nonconflicting_filename(dst)
                src.rename(final_dst)
                self.log(f"[RENAME] {src.name} → {final_dst.name}")
                success += 1
            except Exception as e:
                err_msg = f"{src.name}: {e}"
                errors.append(err_msg)
                self.log(f"[ERR] {err_msg}")

        self.log(f"[OK] 成功重命名 {success} 个文件" + (f"，失败 {len(errors)} 个" if errors else ""))

        if errors:
            QMessageBox.warning(self, "重命名完成",
                f"成功: {success}\n失败: {len(errors)}\n\n错误详情见日志")
        else:
            QMessageBox.information(self, "完成", f"已成功重命名 {success} 个文件")

        # 刷新扫描
        self._scan_rename_images()

    def _add_segment_row(self):
        row = self.table_segments.rowCount()
        self.table_segments.insertRow(row)
        self.table_segments.setItem(row, 0, QTableWidgetItem("00:00:00.000"))
        self.table_segments.setItem(row, 1, QTableWidgetItem("00:00:05.000"))

    def _del_segment_row(self):
        # 记录删除前的全部行，供 Ctrl+Z 撤销
        snap = []
        for r in range(self.table_segments.rowCount()):
            s = self.table_segments.item(r, 0)
            e = self.table_segments.item(r, 1)
            snap.append((s.text() if s else "", e.text() if e else ""))
        self._segment_undo_stack.append(snap)
        rows = sorted(set(idx.row() for idx in self.table_segments.selectedIndexes()), reverse=True)
        for r in rows:
            self.table_segments.removeRow(r)
        if self.table_segments.rowCount() == 0:
            self._add_segment_row()
        self._update_preview()
        self._validate_segments()

    def _undo_segment_delete(self):
        """Ctrl+Z：恢复最近一次 Del 删除前的行"""
        if not getattr(self, '_segment_undo_stack', None):
            return
        snap = self._segment_undo_stack.pop()
        self.table_segments.blockSignals(True)
        self.table_segments.setRowCount(0)
        for s, e in snap:
            r = self.table_segments.rowCount()
            self.table_segments.insertRow(r)
            self.table_segments.setItem(r, 0, QTableWidgetItem(s))
            self.table_segments.setItem(r, 1, QTableWidgetItem(e))
        self.table_segments.blockSignals(False)
        self._update_preview()
        self._validate_segments()

    def _move_segment_row(self, direction: int):
        """整体上下移动选中的段（支持多行连续选区），移动后选中行数保持不变"""
        n = self.table_segments.rowCount()
        cols = self.table_segments.columnCount()
        selected = sorted(set(idx.row() for idx in self.table_segments.selectedIndexes()))
        if not selected:
            return
        # 整体移动：上移要求最上一行不在顶；下移要求最下一行不在底
        if direction < 0 and selected[0] <= 0:
            return
        if direction > 0 and selected[-1] >= n - 1:
            return

        # 取出全部行数据（先 takeItem，避免 setItem 时重复持有）
        data = [[self.table_segments.takeItem(r, c) for c in range(cols)] for r in range(n)]

        # 划分连续选区（run），每个 run 整体平移一位
        runs = []
        start = prev = selected[0]
        for r in selected[1:]:
            if r == prev + 1:
                prev = r
            else:
                runs.append((start, prev))
                start = prev = r
        runs.append((start, prev))

        new_selected = []
        if direction < 0:
            # 上移：每个 run [s..e] 与其上方一行交换 → 占据 [s-1..e-1]
            for s, e in runs:
                top = data[s - 1]
                for i in range(s - 1, e):
                    data[i] = data[i + 1]
                data[e] = top
                new_selected.extend(range(s - 1, e))
        else:
            # 下移：每个 run [s..e] 与其下方一行交换 → 占据 [s+1..e+1]
            for s, e in runs:
                bot = data[e + 1]
                for i in range(e + 1, s, -1):
                    data[i] = data[i - 1]
                data[s] = bot
                new_selected.extend(range(s + 1, e + 2))

        # 写回
        self.table_segments.blockSignals(True)
        for r in range(n):
            for c in range(cols):
                self.table_segments.setItem(r, c, data[r][c])
        self.table_segments.blockSignals(False)

        # 重新选中移动后的行（先清空再选，保证选中行数不变、不累加）
        self.table_segments.clearSelection()
        sm = self.table_segments.selectionModel()
        flags = QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows
        for r in new_selected:
            sm.select(self.table_segments.model().index(r, 0), flags)

        self._update_preview()
        self._validate_segments()

    def _sort_segments(self):
        """按起始时间排序所有段"""
        segs = self._get_segments()
        if len(segs) <= 1:
            return
        # 排序后清空撤销栈（顺序已变，旧快照不再适用）
        if hasattr(self, '_segment_undo_stack'):
            self._segment_undo_stack.clear()
        # 按起始时间排序
        segs.sort(key=lambda s: s[0])
        self.table_segments.blockSignals(True)
        self.table_segments.setRowCount(0)
        for s, e in segs:
            r = self.table_segments.rowCount()
            self.table_segments.insertRow(r)
            self.table_segments.setItem(r, 0, QTableWidgetItem(s))
            self.table_segments.setItem(r, 1, QTableWidgetItem(e))
        self.table_segments.blockSignals(False)
        self._update_preview()
        self._validate_segments()

    def _copy_segments(self):
        """复制选中段到剪贴板（导入格式: 起始时间,结束时间）"""
        rows = sorted(set(idx.row() for idx in self.table_segments.selectedIndexes()))
        if not rows:
            return
        lines = []
        for r in rows:
            s = self.table_segments.item(r, 0)
            e = self.table_segments.item(r, 1)
            if s and e:
                lines.append(f"{s.text().strip()},{e.text().strip()}")
        if lines:
            QApplication.clipboard().setText("\n".join(lines))
            self.log(f"[复制] 已复制 {len(lines)} 段时间到剪贴板")

    def _validate_segments(self):
        """校验段内和段间时序，返回 (ok, internals, crosses)"""
        if not hasattr(self, 'lbl_vid_warn'):
            return True, [], []
        segs = self._get_segments()
        internals = []  # 段内逆序（硬错误）
        crosses = []    # 段间重叠（警告）
        for i, (s, e) in enumerate(segs):
            if s >= e:
                internals.append(f"第{i+1}段起始≥结束 ({s} ≥ {e})")
        for i in range(len(segs) - 1):
            if segs[i][1] > segs[i+1][0]:
                crosses.append(f"第{i+1}段结束({segs[i][1]}) > 第{i+2}段起始({segs[i+1][0]})")
        all_warns = internals + crosses
        if all_warns:
            full = "; ".join(all_warns)
            self.lbl_vid_warn.setStyleSheet("color: #e74c3c; font-size: 14px; font-weight: bold;")
            self.lbl_vid_warn.setToolTip(full)
            self.lbl_vid_warn.setText("✗")
            return False, internals, crosses
        else:
            n = len(segs)
            ok_text = "✓" if n > 0 else ""
            self.lbl_vid_warn.setStyleSheet("color: #27ae60; font-size: 14px; font-weight: bold;")
            self.lbl_vid_warn.setText(ok_text)
            self.lbl_vid_warn.setToolTip("")
            return True, [], []

    def _on_warn_clicked(self, event):
        """点击警示标签弹出完整内容"""
        tip = self.lbl_vid_warn.toolTip()
        if tip:
            QMessageBox.information(self, "时间校验", tip)

    def _load_segments_from_text(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("导入时间段")
        dlg.setMinimumSize(400, 300)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("每行: 起始时间,结束时间"))
        te = QTextEdit()
        te.setPlainText("00:00:00.000,00:00:05.000")
        layout.addWidget(te)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        if dlg.exec_() != QDialog.Accepted:
            return
        text = te.toPlainText()
        self.table_segments.setRowCount(0)
        for line in text.strip().splitlines():
            line = line.strip()
            if not line or "," not in line:
                continue
            parts = line.split(",")
            if len(parts) >= 2:
                row = self.table_segments.rowCount()
                self.table_segments.insertRow(row)
                self.table_segments.setItem(row, 0, QTableWidgetItem(parts[0].strip()))
                self.table_segments.setItem(row, 1, QTableWidgetItem(parts[1].strip()))
        if hasattr(self, '_segment_undo_stack'):
            self._segment_undo_stack.clear()
        self._update_preview()

    def _get_segments(self) -> list:
        segs = []
        for r in range(self.table_segments.rowCount()):
            s = self.table_segments.item(r, 0)
            e = self.table_segments.item(r, 1)
            if s and e:
                segs.append((s.text().strip(), e.text().strip()))
        return segs

    def _resolve_display_names(self, actor_ids: List[str]) -> List[str]:
        """根据演员ID列表解析显示名，不修改项目"""
        names = []
        for aid in actor_ids:
            actor = self.actor_manager.get(aid)
            if actor:
                name = actor.name.replace(' ', '.')
                if actor.chn_name:
                    name = f"{name}.{actor.chn_name}"
                names.append(name)
        return names

    def _get_current_actor_selector(self) -> Optional[ActorSelector]:
        widget = self.tabs.currentWidget()
        if widget:
            return widget.findChild(ActorSelector)
        return None

    def _get_episode(self) -> Optional[int]:
        """获取集数（仅剧集项目）"""
        if not self.project or not self.project.is_series:
            return None
        return self.ed_episode.value()

    def _save_tab_actors(self, actor_sel: ActorSelector):
        """演员绑定时自动同步到项目并推送到其他 Tab（仅选择不变更绑定）"""
        if not self.project:
            return
        ids = list(actor_sel.project_actor_ids)
        # 仅在绑定的演员列表真正变化时才持久化
        if set(ids) == set(self.project.actor_ids):
            return
        self.project.set_actor_ids(ids)
        self.manager.save(self.project)
        # 同步到其他 Tab
        for i in range(self.tabs.count()):
            sel = self.tabs.widget(i).findChild(ActorSelector)
            if sel and sel is not actor_sel:
                sel.set_project_actor_ids(ids)
                sel._refresh_completer()

    def _update_preview(self):
        if not hasattr(self, 'lbl_preview'):
            return
        if not self.project:
            self.lbl_preview.setText("-")
            return

        # 用当前 Tab 选择的演员生成预览文件名
        sel = self._get_current_actor_selector()
        current_actor_ids = sel.get_actor_ids() if sel else []
        display_names = self._resolve_display_names(current_actor_ids)

        # 获取 country：优先第一个演员的地区
        preview_country = ""
        if current_actor_ids:
            first_actor = self.actor_manager.get(current_actor_ids[0])
            if first_actor:
                preview_country = first_actor.country

        idx = self.tabs.currentIndex()
        try:
            if idx == 0:
                actors_str = NamingEngine._build_actor_str(display_names)
                movie = NamingEngine._safe_name(self.project.movie)
                se = ""
                ep = self._get_episode()
                if self.project.is_series and self.project.season is not None:
                    se = f".S{self.project.season:02d}"
                    if ep is not None:
                        se += f"E{ep:02d}"
                name = f"[{preview_country}]{actors_str} » {movie}.{self.project.year}{se}(1).gif"
                self.lbl_preview.setText(f"{self.project.target_base_path}\\{name}")
            elif idx == 1:
                self._validate_segments()
                segs = self._get_segments()
                if not segs:
                    self.lbl_preview.setText("请输入至少一段")
                elif len(segs) == 1:
                    # 单段：直接剪辑，文件名用 - 分隔
                    start = segs[0][0]
                    end = segs[0][1]
                    actors_str = NamingEngine._build_actor_str(display_names)
                    movie = NamingEngine._safe_name(self.project.movie)
                    se = ""
                    ep = self._get_episode()
                    if self.project.is_series and self.project.season is not None:
                        se = f".S{self.project.season:02d}"
                        if ep is not None:
                            se += f"E{ep:02d}"
                    start_fmt = start.replace(':', '.')
                    end_fmt = end.replace(':', '.')
                    name = f"[{preview_country}]{actors_str} » {movie}.{self.project.year}{se} » {start_fmt}-{end_fmt}.mp4"
                    self.lbl_preview.setText(f"{self.project.target_base_path}\\{name}")
                else:
                    # 多段：拼接导出，文件名用 ~ 分隔
                    actors_str = NamingEngine._build_actor_str(display_names)
                    movie = NamingEngine._safe_name(self.project.movie)
                    se = ""
                    if self.project.is_series and self.project.season is not None:
                        se = f".S{self.project.season:02d}"
                    first_fmt = segs[0][0].replace(':', '.')
                    last_fmt = segs[-1][1].replace(':', '.')
                    name = f"[{preview_country}]{actors_str} » {movie}.{self.project.year}{se} » {first_fmt}~{last_fmt}.mp4"
                    self.lbl_preview.setText(
                        f"{self.project.target_base_path}\\{name}  （共 {len(segs)} 段）")
            elif idx == 2:
                # 图片重命名 Tab：显示命名格式（后缀取第一个勾选文件的实际扩展名）
                actors_str = NamingEngine._build_actor_str(display_names)
                movie = NamingEngine._safe_name(self.project.movie)
                se = ""
                ep = self._get_episode()
                if self.project.is_series and self.project.season is not None:
                    se = f".S{self.project.season:02d}"
                    if ep is not None:
                        se += f"E{ep:02d}"
                # 取实际文件后缀
                ext = "png"
                for it in getattr(self, '_rename_items', []):
                    if it["checked"]:
                        ext = it["path"].suffix.lstrip('.')
                        break
                fmt = f"[{preview_country}]{actors_str} » {movie}.{self.project.year}{se}-1.{ext}"
                self.lbl_preview.setText(f"命名格式: {fmt}")
        except Exception as e:
            self.lbl_preview.setText(f"预览生成失败: {e}")

    def _on_execute(self):
        if not self.project:
            QMessageBox.warning(self, "提示", "项目未加载")
            return

        idx = self.tabs.currentIndex()

        # 图片重命名 Tab 走独立逻辑
        if idx == 2:
            self._on_rename_execute()
            return

        # 获取当前 Tab 选择的演员
        sel = self._get_current_actor_selector()
        current_actor_ids = sel.get_actor_ids() if sel else []

        # 确定地区：优先第一个演员的地区，没有则弹窗让用户选
        clip_country = ""
        if current_actor_ids:
            first = self.actor_manager.get(current_actor_ids[0])
            if first:
                clip_country = first.country
        else:
            # 无演员 → 弹窗选地区
            dlg = QDialog(self)
            dlg.setWindowTitle("选择地区")
            dlg.setMinimumWidth(300)
            dlg_layout = QVBoxLayout(dlg)
            dlg_layout.addWidget(QLabel("请指定地区："))
            cb = QComboBox()
            cb.addItems(["CHN", "JAP", "KOR", "WEST", "SLA", "SEA", "LTA"])
            dlg_layout.addWidget(cb)
            btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            btns.accepted.connect(dlg.accept)
            btns.rejected.connect(dlg.reject)
            dlg_layout.addWidget(btns)
            if dlg.exec_() != QDialog.Accepted:
                return
            clip_country = cb.currentText()

        # 创建临时项目副本，用于生成文件名
        temp_proj = Project(self.project._data.copy())
        temp_proj.set_actor_ids(current_actor_ids)
        temp_proj.resolve_actors(self.actor_manager)
        temp_proj.update(country=clip_country)
        ep = self._get_episode()
        if ep is not None:
            temp_proj._data["episode"] = ep

        if idx == 0:
            kwargs = {
                "proj": temp_proj,
                "start": self.ed_gif_start.text(),
                "end": self.ed_gif_end.text(),
                "width": int(self.cb_gif_width.currentText()),
                "fps": int(self.cb_gif_fps.currentText()),
                "colors": int(self.cb_gif_colors.currentText()),
                "brightness": self.spin_brightness.value() if self.chk_brightness.isChecked() else 0,
                "contrast": self.spin_contrast.value() if self.chk_contrast.isChecked() else 1,
                "speed": self.spin_speed.value() if self.chk_speed.isChecked() else 1,
            }
            self._launch_ffmpeg_task("GIF", "gif", **kwargs)

        elif idx == 1:
            segs = self._get_segments()
            if not segs:
                QMessageBox.warning(self, "提示", "请至少输入一段")
                return
            # 时序校验
            ok, internals, crosses = self._validate_segments()
            if internals:
                QMessageBox.warning(self, "时间错误",
                    "起始时间 ≥ 结束时间：\n" + "\n".join(internals))
                return
            if crosses:
                reply = QMessageBox.question(self, "时间段重叠",
                    "时间段重叠：\n" + "\n".join(crosses) + "\n\n仍然执行？",
                    QMessageBox.Yes | QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return

            if len(segs) == 1:
                kwargs = {
                    "proj": temp_proj,
                    "start": segs[0][0],
                    "end": segs[0][1],
                    "copy": self.chk_copy.isChecked(),
                    "no_audio": self.chk_no_audio.isChecked(),
                    "aspect": self.cb_aspect.currentText() if self.chk_aspect.isChecked() else None,
                    "audio_stream": self.spin_audio_idx.value() if self.chk_audio_idx.isChecked() else None,
                }
                self._launch_ffmpeg_task("视频", "cut", **kwargs)
            else:
                kwargs = {
                    "proj": temp_proj,
                    "segments": segs,
                    "copy": self.chk_copy.isChecked(),
                    "no_audio": self.chk_no_audio.isChecked(),
                    "aspect": self.cb_aspect.currentText() if self.chk_aspect.isChecked() else None,
                    "audio_stream": self.spin_audio_idx.value() if self.chk_audio_idx.isChecked() else None,
                }
                self._launch_ffmpeg_task("拼接", "concat", **kwargs)

    def _launch_ffmpeg_task(self, tag: str, mode: str, **kwargs):
        """启动后台 FFmpeg 任务，支持多任务并行；同时记录到任务面板"""
        import json
        self.log(f"── {tag} 开始 ──")
        engine = FFmpegEngine()
        worker = Worker(engine, mode, **kwargs)
        # 任务快照 + 持久化记录
        state = self._snapshot_state_for_task()
        task_id = self.task_manager.create(
            self.project.id, mode, tag, "进行中", "",
            json.dumps(state, ensure_ascii=False))
        worker.log_signal.connect(lambda msg, t=tag: self.log(f"[{t}] {msg}"))
        worker.done_signal.connect(lambda ok, path, tid=task_id: self._on_task_done(tid, ok, path))
        worker.start()
        self._running_tasks[task_id] = {
            "worker": worker, "engine": engine, "tag": tag,
            "output_path": "", "terminated": False,
        }
        # 保持线程引用，清理已完成的任务
        self._workers.append(worker)
        self._workers = [w for w in self._workers if w.isRunning()]
        self._refresh_task_panel()

    def _on_task_done(self, task_id: int, ok: bool, path: str):
        info = self._running_tasks.pop(task_id, None)
        if info is None:
            return  # 已被终止流程处理
        if ok and path:
            self.task_manager.update_status(task_id, "成功", path)
            self.log(f"[{info['tag']}] ✓ {Path(path).name}")
        else:
            self.task_manager.update_status(task_id, "失败")
            self.log(f"[{info['tag']}] ✗ 失败")
        self._refresh_task_panel()

    def _terminate_task(self, task_id: int):
        info = self._running_tasks.get(task_id)
        if not info:
            return
        info["terminated"] = True
        engine = info["engine"]
        engine.kill()
        self._cleanup_task_files(engine, info["tag"])
        self._running_tasks.pop(task_id, None)
        self.task_manager.update_status(task_id, "未进行", "")
        self.log(f"[{info['tag']}] ⊘ 已终止")
        self._refresh_task_panel()

    def _cleanup_task_files(self, engine, tag: str):
        """终止后清理未完成文件：输出文件 + 拼接临时段"""
        out = getattr(engine, "target_path", None)
        self._safe_unlink(out)
        if tag == "拼接":
            try:
                tmp_dir = app_data_dir() / "tmp" / "concat"
                for f in tmp_dir.glob("*.mp4"):
                    self._safe_unlink(f)
            except Exception:
                pass

    @staticmethod
    def _safe_unlink(path, tries: int = 6, delay: float = 0.1):
        """删除文件，容忍终止后短暂的句柄占用（重试几次）"""
        import time
        if not path:
            return
        p = Path(path)
        for _ in range(tries):
            try:
                if p.exists():
                    p.unlink()
                return
            except Exception:
                time.sleep(delay)

    def _refresh_task_panel(self):
        if self._task_dlg is not None and self._task_dlg.isVisible():
            # 延迟到下一轮事件循环，避免在按钮信号处理中销毁按钮 widget
            QTimer.singleShot(0, self._task_dlg.refresh)

    def _open_task_panel(self):
        if self._task_dlg is None:
            self._task_dlg = TaskListDialog(self)
        self._task_dlg.refresh()
        self._task_dlg.show()
        self._task_dlg.raise_()
        self._task_dlg.activateWindow()

    def _save_task_preset(self):
        """把当前工作台配置存为一个「未进行」任务"""
        if not self.project:
            return
        import json
        tab = self.tabs.currentIndex()
        type_ = "gif" if tab == 0 else "video"
        tag = "GIF" if tab == 0 else "视频"
        state = self._snapshot_state_for_task()
        self.task_manager.create(self.project.id, type_, tag, "未进行", "",
                                 json.dumps(state, ensure_ascii=False))
        self.log("[任务] 已保存当前配置为任务")
        self._refresh_task_panel()

    def _restore_task(self, task_id: int):
        """恢复任务：把任务的完整快照载入工作台"""
        if not self.project:
            return
        import json
        t = self.task_manager.get(task_id)
        if not t:
            return
        try:
            state = json.loads(t.get("state_json") or "{}")
        except Exception:
            return
        self._apply_state(state)
        self.log(f"[任务] 已载入任务配置（{t.get('tag')}）")

    def _delete_task(self, task_id: int):
        """删除任务：记录 + 输出文件（移至回收站）"""
        if task_id in self._running_tasks:
            self._terminate_task(task_id)
        t = self.task_manager.get(task_id)
        if not t:
            return
        out = t.get("output_path") or ""
        if out and Path(out).exists():
            result = QtCore.QFile.moveToTrash(str(out))
            ok = result[0] if isinstance(result, tuple) else result
            if not ok:
                self.log(f"[任务] 输出文件删除失败：{Path(out).name}")
        self.task_manager.delete(task_id)
        self._refresh_task_panel()

    def _open_target_dir(self):
        import subprocess
        import platform
        if self.project:
            path = Path(self.project.target_base_path)
            PathHelper.ensure_dir(path)
            if platform.system() == "Windows":
                subprocess.run(["explorer", str(path)])
            else:
                subprocess.run(["xdg-open", str(path)])

    def _on_archive(self):
        """打开归档整理对话框"""
        source = self.project.target_base_path if self.project else ""
        archive_root = r"F:\DB\影视\Clip"
        dlg = ArchiveDialog(self, source_dir=source, archive_root=archive_root)
        dlg.exec_()

    def log(self, msg: str):
        self.txt_log.append(msg)
        scrollbar = self.txt_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Movie Toolkit")
        self.resize(480, 420)

        # 居中显示
        screen = QApplication.primaryScreen().availableGeometry()
        self.move((screen.width() - 480) // 2, (screen.height() - 420) // 2)

        # 设置窗口图标
        icon_path = resource_path("icon.svg")
        if icon_path.exists():
            self.setWindowIcon(QtGui.QIcon(str(icon_path)))

        self.actor_manager = ActorManager()
        self.manager = ProjectManager(actor_manager=self.actor_manager)

        self.stack = QStackedWidget()
        self.list_page = ProjectListPage(self.manager, self.actor_manager)
        self.workbench = WorkbenchPage(self.manager, self.actor_manager)

        self.list_page.project_selected.connect(self._enter_workbench)
        self.workbench.back_signal.connect(self._back_to_list)
        self.list_page.theme_toggled.connect(self._toggle_theme)
        self.workbench.theme_toggled.connect(self._toggle_theme)

        self.stack.addWidget(self.list_page)
        self.stack.addWidget(self.workbench)

        self.setCentralWidget(self.stack)
        self.stack.setCurrentIndex(0)

        # 加载偏好配置
        import json
        self._config_path = app_data_dir() / ".filmcutter_config.json"
        config = {}
        if self._config_path.exists():
            try:
                config = json.loads(self._config_path.read_text(encoding='utf-8'))
            except Exception:
                pass

        # 自动根据时间选择日间/夜间模式（18:00 ~ 05:59 为夜间），用户偏好优先
        from datetime import datetime
        hour = datetime.now().hour
        if "dark" in config:
            self._dark = config["dark"]
        else:
            self._dark = (hour >= 18 or hour < 6)
        self._light_palette = None  # 延迟到首次切换前保存（确保 Fusion 已生效）
        if self._dark:
            self._light_palette = QPalette(QApplication.instance().palette())
            QApplication.instance().setPalette(self._dark_palette())
            self.list_page.btn_theme_list.setText("☀")
            wb_btn = self.workbench.findChild(QPushButton, "btn_theme_wb")
            if wb_btn:
                wb_btn.setText("☀")
            self._set_title_bar(True)

    def _set_title_bar(self, dark: bool):
        """Windows 标题栏暗色模式"""
        if sys.platform == 'win32':
            try:
                import ctypes
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                hwnd = int(self.winId())
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                    ctypes.byref(ctypes.c_int(1 if dark else 0)),
                    ctypes.sizeof(ctypes.c_int))
            except Exception:
                pass

    def _enter_workbench(self, project: Project):
        self.workbench.load_project(project)
        self.stack.setCurrentIndex(1)
        self.showMaximized()

    def _back_to_list(self):
        self.workbench._save_state()
        self.list_page._refresh_list()
        self.stack.setCurrentIndex(0)
        self.showNormal()

    def closeEvent(self, event):
        self.workbench._save_state()
        event.accept()

    @staticmethod
    def _dark_palette():
        p = QPalette()
        p.setColor(QPalette.Window, QColor(45, 45, 45))
        p.setColor(QPalette.WindowText, QColor(220, 220, 220))
        p.setColor(QPalette.Base, QColor(35, 35, 35))
        p.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
        p.setColor(QPalette.ToolTipBase, QColor(45, 45, 45))
        p.setColor(QPalette.ToolTipText, QColor(220, 220, 220))
        p.setColor(QPalette.Text, QColor(220, 220, 220))
        p.setColor(QPalette.Button, QColor(53, 53, 53))
        p.setColor(QPalette.ButtonText, QColor(220, 220, 220))
        p.setColor(QPalette.BrightText, QColor(255, 80, 80))
        p.setColor(QPalette.Link, QColor(42, 130, 218))
        p.setColor(QPalette.Highlight, QColor(42, 130, 218))
        p.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        p.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
        p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
        return p

    def _toggle_theme(self):
        self._dark = not self._dark
        app = QApplication.instance()
        if self._dark:
            if self._light_palette is None:
                self._light_palette = QPalette(app.palette())
            app.setPalette(self._dark_palette())
        else:
            app.setPalette(self._light_palette)
        # 强制刷新所有 widget
        app.setStyleSheet("/* */")
        app.setStyleSheet("")
        # 更新按钮图标：夜间显示☀，日间显示🌙
        icon = "☀" if self._dark else "🌙"
        self.list_page.btn_theme_list.setText(icon)
        wb_btn = self.workbench.findChild(QPushButton, "btn_theme_wb")
        if wb_btn:
            wb_btn.setText(icon)
        self._set_title_bar(self._dark)
        # 持久化偏好
        import json
        try:
            self._config_path.write_text(json.dumps({"dark": self._dark}), encoding='utf-8')
        except Exception:
            pass



if __name__ == "__main__":
    import ctypes
    import platform

    app = QApplication(sys.argv)

    # 设置应用图标（影响任务栏显示）
    icon_path = Path(__file__).parent / "icon.svg"
    if icon_path.exists():
        app_icon = QtGui.QIcon(str(icon_path))
        app.setWindowIcon(app_icon)

    # Windows 任务栏图标需要设置 AppUserModelID
    if platform.system() == "Windows":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FilmCutter.MovieToolkit")
        except Exception:
            pass

    app.setStyle("Fusion")
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())