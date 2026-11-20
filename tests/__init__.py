"""
Test package initialization ensuring hirist_mcp is discoverable.
"""
import sys
from pathlib import Path

# Add project root and workspace root to sys.path
workspace_dir = Path(__file__).resolve().parent.parent.parent
if str(workspace_dir) not in sys.path:
    sys.path.insert(0, str(workspace_dir))
