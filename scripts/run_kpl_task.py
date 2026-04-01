#!/usr/bin/env python3
"""开盘啦任务统一入口。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.apps.kaipanla.entry import main


if __name__ == "__main__":
    raise SystemExit(main())
