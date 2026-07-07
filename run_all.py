"""収集→分析→ダッシュボード生成→デプロイを1つのコマンドでまとめて実行する。

GitHub Actionsの定時実行(毎朝06:30 JST)を待たず、任意のタイミングで
手元のPCからすぐに更新したいときに使う。

使い方: python run_all.py
"""
import subprocess
import sys

from config import BASE_DIR

# (スクリプト名, 失敗したら全体を止めるか)
# collect_x.py はX API側のプラン制限で失敗することがあるため、失敗しても後続を続行する
STEPS = [
    ("collect_x.py", False),
    ("collect_market.py", True),
    ("analyze.py", True),
    ("build_dashboard.py", True),
    ("deploy.py", True),
]


def run_step(script: str, required: bool) -> bool:
    print(f"\n=== {script} ===")
    result = subprocess.run([sys.executable, script], cwd=BASE_DIR)
    if result.returncode != 0:
        print(f"[run_all] {script} failed (exit code {result.returncode})", file=sys.stderr)
        if required:
            return False
    return True


def main() -> None:
    for script, required in STEPS:
        if not run_step(script, required):
            print(f"[run_all] stopping: {script} failed", file=sys.stderr)
            sys.exit(1)
    print("\n[run_all] done")


if __name__ == "__main__":
    main()
