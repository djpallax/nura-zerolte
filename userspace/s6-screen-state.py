#!/usr/bin/python3
import subprocess,sys,time
from pathlib import Path
mode=sys.argv[1]
assert mode in ('on','off')
subprocess.run(['kscreen-doctor','--dpms',mode],timeout=5,check=True)
Path('/run/s6-native/screen-state').write_text(mode)
if mode=='on':Path('/run/s6-native/last-screen-wake').write_text(str(time.monotonic()))
