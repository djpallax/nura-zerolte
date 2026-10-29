#!/usr/bin/python3
import socket,sys
assert len(sys.argv)==2 and sys.argv[1] in ('capabilities','off','reboot','recovery')
s=socket.socket(socket.AF_UNIX);s.settimeout(4);s.connect('/run/s6-power/control');s.sendall(sys.argv[1].encode());print(s.recv(1024).decode().strip())
