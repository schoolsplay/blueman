#!/home/stas/Github/SchoolsplayRepos/blueman/.venv3.8/bin/python3.8
import sys
import os

import gettext

from blueman import SPLogging

# support running uninstalled
_dirname = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path = [_dirname] + sys.path
os.environ["GSETTINGS_SCHEMA_DIR"] = os.path.join(_dirname, "data")
os.environ['BLUEMAN_SOURCE'] = '1' # See Constants.py

print(f"sys.path: {sys.path}")
gettext.textdomain("blueman")

from blueman.main.Manager import Blueman
from blueman.Functions import set_proc_title

log_level = 'debug'
SPLogging.set_level(log_level)
SPLogging.start()

app = Blueman()
set_proc_title()
app.run()

