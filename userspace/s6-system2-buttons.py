#!/usr/bin/python3
"""S6-only input handler for native Plasma; no grabs and no keyboard logging."""
import glob,os,select,struct,subprocess,time,re
from pathlib import Path
import dbus,dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
DBusGMainLoop(set_as_default=True)
bus=dbus.SessionBus();off=False;led_deadline=0.0
active_app="";power_down=None;power_long=False;power_wake=False
class Controls(dbus.service.Object):
 @dbus.service.method('org.s6.Controls',in_signature='s',out_signature='')
 def SetActiveApp(self,value):
  global active_app
  active_app=str(value)
 @dbus.service.method('org.s6.Controls',in_signature='',out_signature='s')
 def GetActiveApp(self):return active_app
bus_owner=dbus.service.BusName('org.s6.Controls',bus)
controls=Controls(bus,'/Controls')
context=GLib.MainContext.default()
led=Path('/sys/class/leds/s6::kbd_backlight/brightness')
def run(*a):
 try:subprocess.run(a,timeout=3,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 except (OSError,subprocess.TimeoutExpired):pass
def light(value):
 try:led.write_text(str(value))
 except OSError:pass
def shortcut(name):
 bus.get_object('org.kde.kglobalaccel','/component/kwin').invokeShortcut(name,dbus_interface='org.kde.kglobalaccel.Component',timeout=2)
def pressed(code,value):
 global off,led_deadline,power_down,power_long,power_wake
 if code==116:
  if value==1:
   power_down=time.monotonic();power_long=False
   try:state=Path('/run/s6-native/screen-state').read_text().strip()
   except OSError:state='on'
   try:wake=float(Path('/run/s6-native/last-screen-wake').read_text())
   except (OSError,ValueError):wake=0
   power_wake=state=='off' or time.monotonic()-wake<0.8
   print('Power press, wake intent:',power_wake,flush=True)
  elif value==0 and power_down is not None:
   if not power_long:
    off=not power_wake;run('/usr/local/bin/s6-screen-state','on' if power_wake else 'off')
    if off:light(0);led_deadline=0
   power_down=None
  return
 if code==330 and value==1:off=False
 if value not in (1,2):return
 if value==1 and code in (116,172,580,158,115,114):print("S6 button:",code,flush=True)
 if code in (172,580,158,115,114,330) and not off:
  light(1);led_deadline=time.monotonic()+3
 try:
  if code==172 and value==1:
   bus.get_object('org.kde.KWin','/KWin').showDesktop(True,dbus_interface='org.kde.KWin',timeout=2)
  elif code==580 and value==1:shortcut('Mobile Task Switcher')
  elif code==158 and value==1:
   mobile=bus.get_object('org.kde.plasmashell','/Mobile')
   if mobile.isActionDrawerOpen(dbus_interface='org.kde.plasmashell',timeout=2):
    mobile.closeActionDrawer(dbus_interface='org.kde.plasmashell',timeout=2);return
   keyboard=bus.get_object('org.kde.KWin','/VirtualKeyboard')
   if keyboard.Get('org.kde.kwin.VirtualKeyboard','visible',dbus_interface='org.freedesktop.DBus.Properties',timeout=2):
    keyboard.Set('org.kde.kwin.VirtualKeyboard','active',dbus.Boolean(False),dbus_interface='org.freedesktop.DBus.Properties',timeout=2);return
   if 'qmlkonsole' in active_app.lower():
    bus.get_object('org.kde.KWin','/KWin').showDesktop(True,dbus_interface='org.kde.KWin',timeout=2)
  elif code in (115,114):
   try:
    raw=subprocess.check_output(['pactl','get-sink-volume','@DEFAULT_SINK@'],timeout=2,text=True)
    current=int(re.search(r'(\d+)%',raw)[1]);volume=max(0,min(100,current+(5 if code==115 else -5)))
    run('pactl','set-sink-volume','@DEFAULT_SINK@',str(volume)+'%')
    bus.get_object('org.kde.plasmashell','/org/kde/osdService').volumeChanged(dbus.Int32(volume),dbus.Int32(100),dbus_interface='org.kde.osdService',timeout=2)
   except (OSError,subprocess.SubprocessError,ValueError,TypeError):print('No PulseAudio sink for volume control',flush=True)
 except dbus.DBusException as e:print('button action failed:',code,e.get_dbus_name(),flush=True)
fds={};buffers={};last_discovery=0
try:
 while True:
  now=time.monotonic()
  while context.pending():context.iteration(False)
  if power_down is not None and not power_long and now-power_down>=1.2:
   power_long=True;off=False
   subprocess.Popen(['/usr/local/bin/s6-power-menu'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  if now-last_discovery>5:
   for path in glob.glob('/dev/input/event*'):
    try:
     name=Path('/sys/class/input',Path(path).name,'device/name').read_text().strip()
     if name not in ('Galaxy S6 Edge STM FTS','Galaxy S6 capacitive keys','Galaxy S6 physical keys','gpio-keys') or path in fds.values():continue
     fd=os.open(path,os.O_RDONLY|os.O_NONBLOCK);fds[fd]=path;buffers[fd]=b'';print('S6 input registered:',name,path,flush=True)
    except OSError:pass
   last_discovery=now
  if led_deadline and now>=led_deadline:light(0);led_deadline=0
  ready,_,_=select.select(list(fds),[],[],0.25)
  for fd in ready:
   try:data=os.read(fd,24*32)
   except OSError:data=b''
   if not data:os.close(fd);del fds[fd];del buffers[fd];continue
   buffers[fd]+=data
   while len(buffers[fd])>=24:
    _,_,kind,code,value=struct.unpack('qqHHi',buffers[fd][:24]);buffers[fd]=buffers[fd][24:]
    if kind==1:pressed(code,value)
finally:light(0)
