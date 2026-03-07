import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

GOLDEN_FIXTURES = ROOT / "tests" / "golden" / "fixtures"


def copy_golden_fixture(name: str, tmp_path: Path) -> Path:
    source = GOLDEN_FIXTURES / name
    destination = tmp_path / name
    shutil.copytree(source, destination)
    return destination
