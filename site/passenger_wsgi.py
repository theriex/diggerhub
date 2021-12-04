import sys, os
INTERP = "USERHOME/diggerhub.com/venv/bin/python"
if sys.executable != INTERP:
    # INTERP is present twice so that the newly instantiated Python
    # interpreter gets the actual executable path.
    os.execl(INTERP, INTERP, *sys.argv)
sys.path.append(os.getcwd())
from main import app as application
