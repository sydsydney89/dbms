# wsgi.py - PythonAnywhere entry point
# In the PythonAnywhere Web tab, set:
#   Source code:      /home/<username>/<projectdir>
#   Working dir:      /home/<username>/<projectdir>
#   WSGI config file: (point to this file)
import sys
import os

# Add the project directory to the path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from app import app as application  # noqa: F401
