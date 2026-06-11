"""
pytest 配置 — 让 tests/ 能 import src/ 下的模块
"""
import sys
from pathlib import Path

# 把项目根目录加到 sys.path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "src"))
