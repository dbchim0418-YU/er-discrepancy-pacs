import sys
from pathlib import Path

# 프로젝트 루트를 import 경로에 추가 (tests/에서 core, imaging, workflow를 불러오기 위해)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
