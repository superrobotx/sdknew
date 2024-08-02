import sys
from manager.cmd import *

# no args
if len(sys.argv) < 2:
  print("Usage: python -m manager <arg1>")
  sys.exit(1)

a1 = sys.argv[1]

if a1 in ['backup', 'back']:
  backup()
  sys.exit(0)

if a1 in ['gen', 'generate']:
  generator.code_generate()
  sys.exit(0)

# two args
if a1 in ['ui']:
  ui_cmd(sys.argv[2:])
  sys.exit(0)

if a1 in ['backend']:
  backend_cmd(sys.argv[2:])
  sys.exit(0)

if a1 in ['app']:
  app_cmd(sys.argv[2:])
  sys.exit(0)

if a1 in ['remote']:
  remote_cmd(sys.argv[2:])
  sys.exit(0)

if a1 in ['desk']:
  desk_cmd(sys.argv[2:])
  sys.exit(0)

if a1 in ['web']:
  web_cmd(sys.argv[2:])
  sys.exit(0)


if a1 in ['test']:
  test()
  sys.exit(0)
  

print('unknow command', a1)