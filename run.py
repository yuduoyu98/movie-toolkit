"""热更新启动器：检测改动→关闭→静默等待→无新改动后重启"""
import subprocess
import sys
import time
import os

WATCH = ["movie_core.py", "movie_gui.py"]
COOLDOWN = 2.0  # 最后一次改动后等几秒再重启


def get_mtimes():
    return {f: os.path.getmtime(f) for f in WATCH if os.path.exists(f)}


def main():
    proc = None
    last_mt = get_mtimes()
    pending_restart = False

    while True:
        if proc is None or proc.poll() is not None:
            if pending_restart:
                print("[run] 无新改动，重启…")
                pending_restart = False
            proc = subprocess.Popen([sys.executable, "movie_gui.py"])
            last_mt = get_mtimes()
            time.sleep(1)
            continue

        time.sleep(0.5)
        current = get_mtimes()
        if current != last_mt:
            changed = [f for f in WATCH if current.get(f) != last_mt.get(f)]
            last_mt = current
            if proc and proc.poll() is None:
                print(f"[run] 检测到改动: {', '.join(changed)}，关闭…")
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                proc = None
                pending_restart = False

        # 进程被杀后，等 COOLDOWN 秒无新改动再重启
        if proc is None and not pending_restart:
            pending_restart = True
            last_mt = get_mtimes()

        if pending_restart and proc is None:
            if get_mtimes() == last_mt:
                # 这段时间没新改动
                stale = time.time()
                while get_mtimes() == last_mt:
                    if time.time() - stale >= COOLDOWN:
                        break
                    time.sleep(0.3)
                if get_mtimes() == last_mt:
                    proc = subprocess.Popen([sys.executable, "movie_gui.py"])
                    pending_restart = False
                    last_mt = get_mtimes()
                    time.sleep(1)
            else:
                last_mt = get_mtimes()  # 有新改动，重置计时


if __name__ == "__main__":
    main()
