import os
import sys
from mock import Mock

import sgtk

# Mock Qt since we don't have it.
sgtk.platform.qt.QtCore = Mock()
sgtk.platform.qt.QtGui = Mock()

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(repo_root, "python"))
