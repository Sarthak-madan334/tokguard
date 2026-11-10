"""tokguard.mcp_server entrypoint."""

import sys
from pathlib import Path

pkg_dir = Path(__file__).resolve().parent
parent_dir = pkg_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from tg.mcp_server import main, app

if __name__ == "__main__":
    main()

