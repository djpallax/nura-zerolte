#!/usr/bin/python3
"""Single-seat power broker: fixed actions, UID check and mandatory RO guard."""
import json,os,socket,struct,subprocess,threading,time
from pathlib import Path
ROOT=Path('/run/s6-power');ROOT.mkdir(mode=0o750,exist_ok=True)
SOCK=ROOT/'control';busy=threading.Lock()
def log(s):
 with (ROOT/'actions.log').open('a') as f:f.write(f'{time.monotonic():.3f} {s}\n')
def poweroff_available():
 p=Path('/sys/bus/platform/drivers/syscon-poweroff')
 return p.exists() and any(x.is_symlink() and x.name!='module' for x in p.iterdir())
def execute(action):
 try:
  log('prepare '+action)
  led=Path('/sys/class/leds/s6::kbd_backlight/brightness')
  if led.exists():led.write_text('0')
  subprocess.run(['/etc/init.d/s6-plasma-native','stop'],timeout=15,check=True)
  subprocess.run(['/bin/sync'],timeout=15,check=True)
  subprocess.run(['/bin/mount','-o','remount,ro','/'],timeout=10,check=True)
  assert any(x.split()[1]=='/' and 'ro' in x.split()[3].split(',') for x in Path('/proc/mounts').read_text().splitlines())
  log('ROOT_RO_VERIFIED '+action)
  time.sleep(1)
  argv={'recovery':['/sbin/reboot-recovery'],'reboot':['/sbin/reboot','-f'],'off':['/sbin/poweroff','-f']}[action]
  subprocess.run(argv,timeout=8,check=True)
 except Exception as e:
  log('FAILED '+type(e).__name__+' '+str(e))
  subprocess.run(['/bin/mount','-o','remount,rw','/'],timeout=10,check=False)
  subprocess.run(['/etc/init.d/s6-plasma-native','start'],timeout=20,check=False)
 finally:busy.release()
if SOCK.exists():SOCK.unlink()
s=socket.socket(socket.AF_UNIX);s.bind(str(SOCK));os.chown(ROOT,0,1000);os.chmod(ROOT,0o750);os.chown(SOCK,0,1000);os.chmod(SOCK,0o660);s.listen(4)
log('broker ready')
while True:
 c,_=s.accept()
 with c:
  c.settimeout(3)
  _,uid,_=struct.unpack('3i',c.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
  try:
   if uid not in (0,1000):raise PermissionError('unauthorized peer')
   action=c.recv(64).decode().strip()
   if action=='capabilities':result={'reboot':True,'recovery':True,'off':poweroff_available()}
   elif action not in ('reboot','recovery','off'):raise ValueError('unsupported action')
   elif action=='off' and not poweroff_available():raise RuntimeError('poweroff driver unavailable')
   elif not busy.acquire(blocking=False):raise RuntimeError('power action already in progress')
   else:
    result={'accepted':action};threading.Thread(target=execute,args=(action,),daemon=True).start()
   c.sendall((json.dumps(result)+'\n').encode())
  except Exception as e:c.sendall((json.dumps({'error':str(e)})+'\n').encode())
