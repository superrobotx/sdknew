import code
import sys, os
from .utils import config

from manager.docker import Docker
from . import generator as generator
from .vps import VPS

def run_ui():
  os.chdir('./web')
  os.system('yarn run dev')

def ui_cmd(args):
  if not args:
    print("Usage: python -m manager ui <arg2>")
    sys.exit(1)
  a2 = args[0]
  if a2 in ['run']:
    run_ui()
    sys.exit(0)
  else:
    print('unknown command: ui', a2)
  sys.exit(1)

def backend_cmd(args):
  if not args:
    print("Usage: python -m manager backend <arg2>")
    sys.exit(1)
  a2 = args[0]
  if a2 in ['run']:
    if len(args) == 1:
      os.system('python backend')
    elif len(args) == 2:
      a3 = args[1]
      if a3 in ['remote']:
        #os.system('python backend remote')
        print('remote')
    else:
      print('unknown command: backend', args)
      sys.exit(1)
    sys.exit(0)
  elif a2 in ['login']:
    Docker().login(f'{config.name}_backend')
    sys.exit(0)
  else:
    print('unknown command: backend', args)
  sys.exit(1)

def app_cmd(args):
  if not args:
    print("Usage: python -m manager app <arg2>")
    sys.exit(1)
  a2 = args[0]
  if a2 in ['run']:
    print('ufck')
    sys.exit(0)
  if a2 in ['gen', 'generate']:
    generator.app_generate()
    sys.exit(0)
  else:
    print('unknown command: app', a2)
  sys.exit(1)

def remote_cmd(args):
  if not args:
    print("Usage: python -m manager remote <arg2>")
    sys.exit(1)
  a2 = args[0]
  if a2 in ['install']:
    VPS().install_requirements()
    sys.exit(0)
  if a2 in ['push']:
    VPS().push_to_remote(args[1])
    sys.exit(0)
  if a2 in ['login']:
    VPS().login()
    sys.exit(0)
  if a2 in ['log']:
    VPS().print_log()
    sys.exit(0)
  if a2 in ['run']:
    if len(args) == 1:
      VPS().run_backend()
    elif len(args) == 2:
      a3 = args[1]
      if a3 in ['frps']:
        VPS().run_frps()
      elif a3 in ['frpc']:
        VPS().run_frpc()
      elif a3 in ['backend', 'back']:
        VPS().run_backend()
      else:
        print('unknown command: remote', args)
        sys.exit(1)
    sys.exit(0)
  if a2 in ['frps']:
    VPS().run_frps()
    sys.exit(0)
  if a2 in ['test']:
    VPS().test()
    sys.exit(0)
  print('unknown command: remote', a2)
  sys.exit(1)

def backup():
  os.system('./sdk/scripts/backup.sh')

def test():
  VPS().test()