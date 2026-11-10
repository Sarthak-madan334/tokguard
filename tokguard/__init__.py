"""tokguard package compatibility alias for tg."""

import sys
from pathlib import Path

# Add parent directory to sys.path if not present
pkg_dir = Path(__file__).resolve().parent
parent_dir = pkg_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from tg import *

