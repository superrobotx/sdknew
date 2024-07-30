import queue
from typing import Any
from flask import Flask, Response, make_response, redirect, request, send_from_directory
from omegaconf import OmegaConf
from .hub import queues
from .utils import *
from werkzeug.serving import run_simple

class PreventResend:
  ''' 
  run python class as http server in backend process
  '''
  last_cmd = ('cmd', 0)
  
  class CmdResend(Exception):
    pass
  
  def __init__(self, data) -> None: 
    self.data = data
    
  cmds = {}
  def _prevent_cmd_resend(self, func_name, args):
    if 'paint' in func_name:
      return True
    cmd = f'{func_name}/{json.dumps(args)}'
    t = time.time()
    if cmd in self.cmds:
      prev_t = self.cmds[cmd]
    else:
      prev_t = 0
    
    self.cmds[cmd] = t
    if t - prev_t < 0.01:
      print('prevent')
      return False
    return True
    
  def __call__(self) -> Any:
    return self.data


class CallBackend(Thread):
  ''' 
  run  python code remotely,
   rpc, http server

  '''
  cached_cls = {}

  def __init__(self, data) -> None:
    super().__init__()
    self.data = data

  def stream_response(self):
    while True:
      data = queues[self.tid].get()
      if data is None:
        break
      if type(data) == dict:
        tmp = {}
        for k,v in data.items():
          tmp[k] = len(v)
        print('yield', tmp)
      else:
        print('yield', data)
      yield json.dumps(data) + '\n' 

  def call_cls_func(self, cls_name, func_name, init_args={}, func_args={}):

    if not cls_name.lower().endswith('backend'):
      print('forbid cls name', cls_name)
      return
    
    try:
      if cls_name in self.cached_cls:
        ins = self.cached_cls[cls_name]
      else:
        cls = PyCodeParser().get_cls_by_name(cls_name, 'backend')
        ins = cls(**init_args)
        self.cached_cls[cls_name] = ins
      print('call', func_name)
      return getattr(ins, func_name)(**func_args)
    except Exception as e:
      traceback.print_exc()

  tid = None
  def run(self) -> Any:
    self.tid = threading.current_thread().ident
    queues[self.tid] = queue.Queue()
    self.call_cls_func(**self.data)
    queues[self.tid].put(None)

  def stream(self):
    self.start()

  def call_func(self):
    return self.call_cls_func(**self.data)

