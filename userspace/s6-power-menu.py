#!/usr/bin/python3
import subprocess,json
from pathlib import Path
import fcntl
with Path('/run/s6-native/power-menu.lock').open('a') as lock:
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:raise SystemExit(0)
 subprocess.run(['/usr/local/bin/s6-screen-state','on'],timeout=6,check=False)
 r=subprocess.run(['kdialog','--title','Energía — Galaxy S6','--menu','Elegí una acción','off','Apagar','reboot','Reiniciar','recovery','Reiniciar en recovery'],text=True,stdout=subprocess.PIPE,timeout=120)
 action=r.stdout.strip()
 if r.returncode==0 and action in ('off','reboot','recovery'):
  answer=subprocess.check_output(['/usr/local/bin/s6-power-client',action],text=True,timeout=5)
  value=json.loads(answer)
  if 'error' in value:subprocess.run(['kdialog','--error',value['error']],timeout=30)
