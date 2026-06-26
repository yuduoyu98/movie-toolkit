"""回归测试：在 ActorSelector 里"新增"演员，必须同时绑定到项目（project_actor_ids），
否则 _save_tab_actors 只同步 project_actor_ids，新演员不会出现在其它 Tab。

无测试框架，直接 `python test_actor_sync.py` 运行（用临时 db，不碰真实数据）。
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
import movie_core
import movie_gui


# 自动接受"新建演员"对话框，返回一个确定的演员（避免模态阻塞）
class _FakeActorDlg:
    def __init__(self, parent=None):
        pass

    def exec_(self):
        return movie_gui.QDialog.Accepted

    def get_actor(self):
        return movie_core.Actor.create("ZyzTestActor", "JAP", "测试员")


movie_gui.ActorEditDialog = _FakeActorDlg

app = QApplication.instance() or QApplication(sys.argv)

tmp_db = os.path.join(tempfile.gettempdir(), "fc_actor_sync_test.db")
if os.path.exists(tmp_db):
    os.remove(tmp_db)

mgr = movie_core.ActorManager(db_path=tmp_db)
sel = movie_gui.ActorSelector(mgr)
sel.set_project_actor_ids([])      # 全新项目，无已绑定演员

sel._on_new_actor()                # 模拟点"新增"并自动确认

created = [a for a in mgr.list_actors() if a.name == "ZyzTestActor"]
assert len(created) == 1, f"演员未创建: {created}"
aid = created[0].id

assert aid in sel.selected_actor_ids, f"未加入 selected: {sel.selected_actor_ids}"
# 根因断言：必须绑定到 project_actor_ids，才能同步到其它 Tab
assert aid in sel.project_actor_ids, (
    f"BUG: 新增演员未绑定到 project_actor_ids: {sel.project_actor_ids}"
)

print("PASS: 新增演员已绑定到 project_actor_ids（会同步到其它 Tab）")
