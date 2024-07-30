from contextlib import closing
from omegaconf import OmegaConf
from addict import Dict
import time, json, requests, traceback, sys, os
import inspect
import socket
import sys, re

class Misc:
  ''' 
  misc
  '''
  def is_notebook(self) -> bool:
    try:
        shell = get_ipython().__class__.__name__ # type: ignore 
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False 

  def camel_to_snake(self, name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
  
  def snake_to_camel(self, name):
    return ''.join(word.title() for word in name.split('_'))

  def get_local_ip(self):
    # Create a socket object
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Connect to a remote address that is unlikely to exist
        sock.connect(('10.255.255.255', 1))
        # Get the local IP address
        ip_address = sock.getsockname()[0]
    except Exception:
        # If the above method fails, fallback to getting the hostname
        ip_address = socket.gethostbyname(socket.gethostname())
    finally:
        # Close the socket
        sock.close()

    return ip_address

class NetUtil:
  ''' 
  network utils, get free port,
  '''
  def get_free_port():
      with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
          s.bind(('', 0))
          s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
          return s.getsockname()[1]


class PyCodeParser: 
  ''' 
  parse python code, generate document, jump to code, code location
  '''
  def get_classes(self_, module_name):
    return {cls_name:cls 
            for cls_name, cls in inspect.getmembers(sys.modules[module_name], predicate=lambda m:inspect.isclass(m) and m.__module__ == module_name )}

  def get_cls_by_name(self, cls_name, module_name):
    return self.get_classes(module_name)[cls_name]

  def jump_to_class(
      self, fpath:str=__file__, member_name:str='PyCodeParser')->None:
    ''' 
    jump to member definition in vscode
    '''
    return
    if '.' in member_name:
      cls_name, func_name = member_name.split('.')
    else:
      cls_name, func_name = member_name, ''

    cls = globals()[cls_name]
    member = getattr(cls, func_name) if func_name else cls
    line = inspect.findsource(member)[1] + 1

    #subprocess.Popen(f'code -g {fpath}:{line}',  cwd='/media/haha/cerulean/lab/backend/', shell=True)
    state = VSCodeBackend.VSCodeState()
    state.fpath = fpath
    state.lineno = line
    os.system('xdotool search "Visual Studio Code" windowactivate --sync key --clearmodifiers')


  def generate_doc(self):
    tmp = []
    for cls_name, cls in self.classes.items():
      doc = Dict()
      doc.cls_name = cls_name
      doc.doc = cls.__doc__ or ''
      for func_name, func in inspect.getmembers(cls, predicate=inspect.isfunction):
        if func_name[0] != '_':
          doc.func_doc[func_name].signature = str(inspect.signature(func))
          doc.func_doc[func_name].doc = func.__doc__ or ''
      tmp.append(doc)
    return tmp 

config_file = './config.yaml'
config = OmegaConf.load(config_file)
if config['network']['backend_ip'] == 'localhost':
  config.network.backend_ip = Misc().get_local_ip()
