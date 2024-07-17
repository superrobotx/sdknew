from .utils import * 
from werkzeug.serving import run_simple
from flask import Flask, request
import pathlib
    
class Log: 
  '''  
  logging, currently no used
  '''
  def log(self, *args):
    print(self.__class__.__name__, ':', *args)

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


class Base:
  '''  
  basic class 
  '''
  vscode_tmp = {
    'base.py': '/home/haha/.config/Code/Backups/609bf73bbd112bdfa81352729abf16bf/file/-779faf9a', 
    'configs.yml': '/home/haha/.config/Code/Backups/609bf73bbd112bdfa81352729abf16bf/file/5a3fcbfb '
  }
  @property
  def root_dir(self):
    #return os.path.dirname(__file__)
    return '/media/haha/data'
  
  def get_abs_path(self, relative):
    ''' 
    get abs paths relative this file
    '''
    return os.path.join(self.root_dir, relative)     

  
class Icons: 
  robot_outline = '/media/haha/cerulean/king/res/icons/robot-outline.svg'
  robot = '/media/haha/cerulean/king/res/icons/robot.svg'
  
  cat_outline = '/media/haha/cerulean/king/res/icons/cat-outline.svg'
  cat = '/media/haha/cerulean/king/res/icons/cat.svg' 
  
  flower_outline = '/media/haha/cerulean/king/res/icons/flower-outline.svg'
  flower = '/media/haha/cerulean/king/res/icons/flower.svg'
  
  nuclear_outline = '/media/haha/cerulean/king/res/icons/nuclear-outline.svg'
  nuclear = '/media/haha/cerulean/king/res/icons/nuclear.svg'
  
  robot_black_outline = '/media/haha/cerulean/king/res/icons/robot-black-outline.svg'
  robot_black = '/media/haha/cerulean/king/res/icons/robot-black.svg'
  
  shield_outline = '/media/haha/cerulean/king/res/icons/shield-outline.svg'
  shield = '/media/haha/cerulean/king/res/icons/shield.svg'
  react = '/media/haha/cerulean/king/res/icons/react-logo.svg'
  python = '/media/haha/cerulean/king/res/icons/python-logo.svg'
  riyu = '/media/haha/cerulean/king/res/icons/riyu.svg'
  
class Configs(object):  
  ''' 
  configs 
  '''

  _conf_path = os.path.join(Base().root_dir, 'configs.yml')
  _last_load_time = 0
  _conf_cache = None

  def __new__(cls):
    #if not hasattr(cls, 'instance'):
    #  cls.instance = super(Configs, cls).__new__(cls) 
    #return cls.instance
    cls._load_config()
    return cls._conf_cache 

  @classmethod
  def _load_config(cls):
    mt = pathlib.Path(cls._conf_path).stat().st_mtime

    if mt > cls._last_load_time or cls._conf_cache == None:
      print('load')
      cls._conf_cache = Dict(OmegaConf.to_container(
        OmegaConf.load(os.path.join(Base().root_dir, 'configs.yml'))
      ))
      cls._last_load_time = time.time() 

class HttpClient:
  ''' 
  http client, remotely execute python backend process, rpc  
  '''
  def __init__(self, proc_name=None, port=None) -> None:
    if proc_name is not None:
      self.port = Configs().daemon[proc_name].port
      cls = Configs().daemon[proc_name].cls
      if cls:
        cls = PyCodeParser().get_cls_by_name(cls)
        self._add_funcs(cls)
    if port is not None:
      self.port = port

  def _add_funcs(self, cls):
    for func_name, func in inspect.getmembers(cls, predicate=lambda m: inspect.isfunction(m)):
      setattr(self, func_name, partial(self._get, func_name))
 
  def get(self, func_name, args):
    ret = requests.get(f'http://localhost:{self.port}/{func_name}', json=args)
    if ret.status_code == 200:
      return ret.json()
    return ret 
      
  
  def _get(self, _func_name, **args):
    ret = requests.get(f'http://localhost:{self.port}/{_func_name}', json=args)
    if ret.status_code == 200:
      return ret.json()
    return ret 

class _Singleton(type):
    """ A metaclass that creates a Singleton base class when called. """
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Singleton(_Singleton('SingletonMeta', (object,), {})): pass

class ProcessInfo:
  ''' 
  process pawn by zygote, log, pid, cpu usage,
  '''


  class _State:
    starting = 'starting'
    running = 'running'
    stopped = 'stopped'
    
  _ports = db.Hash('ProcessInfo/ports')
  _pids = db.Hash('ProcessInfo/pids')
  _start_times = db.Hash('ProcessInfo/start_times')

  def __init__(self, proc_name) -> None:
    self.proc_name = proc_name

  @property
  def is_running(self):
    if self.status == self._State.running:
      return True
    return False

  @property
  def port(self):
    return self._ports[self.proc_name]
  
  @port.setter
  def port(self, port:int):
    self._ports[self.proc_name] = port
  
  
  @property
  def pid(self):
    pid = self._pids[self.proc_name]
    return int(pid) if pid is not None else None

  @pid.setter
  def pid(self, pid:int):
    self._pids[self.proc_name] = pid

  @property
  def status(self):
    if not self.pid:
      return self._State.stopped

    try:
      p = psutil.Process(self.pid)
      return self._State.running if p.is_running else self._State.stopped
    except psutil.NoSuchProcess:
      return self._State.stopped
  
  @property
  def log_channel(self):
    return f'/log/{self.proc_name}'

  @property
  def status_channel(self):
    return f'/status/{self.proc_name}'

  @property
  def log(self):
    return '\n'.join(db.List(f'log_{self.proc_name}'))
  
  @property
  def start_time(self):
    return psutil.Process(self.pid).create_time()
  
  @start_time.setter
  def start_time(self, v):
    self._start_times[self.proc_name] = v
    


class Process(Log, ProcessInfo):
  ''' 
  backend process, daemon, with fixed process name
  '''

  @classmethod
  def get_pid_by_port(cls, port):
    connections = psutil.net_connections()
    for connection in connections:
      if connection.status == 'LISTEN' and connection.laddr.port == port:
        return connection.pid
    return None


  def __init__(self, proc_name) -> None:
    self.proc_name = proc_name

  def _python_run_server_cmd(self):
    conf = self.conf

    # assert port
    port = conf.port
    if not port:
      port = NetUtil().get_free_port()
    assert port

    return f'python -m base -s {conf.cls} -p {port}'

  def _python_run_once_cmd(self):
    conf = self.conf

    return f'python -m base -r {conf.cls_func} '


  @property
  def conf(self):
    return Configs().daemon[self.proc_name]


  def start(self, cmd=None):
    proc_name = self.proc_name

    # return if proc alreading running
    pi = ProcessInfo(proc_name)
    if pi.status == pi._State.running:
      print(f'{proc_name} already started')
      return

    if not cmd:
      if self.conf.type == 'run_server':
        cmd = self._python_run_server_cmd()
      elif self.conf.type == 'run_once':
        cmd = self._python_run_once_cmd()
      else:
        cmd = self.conf.cmd

    assert cmd, proc_name

    # send starting signal
    r.publish(pi.status_channel, json.dumps(pi._State.starting))
    # send to zygote
    ret = HttpClient(port=Configs().zygote_port).get('start_process', 
                  {'proc_name': proc_name, 'cmd':cmd})

    print('start', self.proc_name)
    
  def stop(self):
    proc_name = self.proc_name
    pi = ProcessInfo(proc_name)
    if pi.status == pi._State.stopped:
      print(f'{proc_name} already stopped')
      return
    
    psutil.Process(pi.pid).terminate()
    print(f'{proc_name} stopped')

  def restart(self, timeout=6):
    pi = ProcessInfo(self.proc_name)
    if pi.is_running:
      self.stop()

    st = time.time()
    while True:
      if time.time() - st > timeout:
        raise Exception('timeout, process not stop in timeout')
      if not pi.is_running:
        break

    self.start()




class Zygote:
  ''' 
  generate process, 
  '''
  def __init__(self) -> None:
    Thread(target=self.load_watch_pig).start()

  def load_watch_pig(self):
    time.sleep(1)
    Process('watch_pig').start()

  def _start_process(self, proc_name, cmd):
    p= ProcessInfo(proc_name)

    if p.status == p._State.running:
        l = f'{proc_name} is already running'
        print(l)
        return p.pid
        
    l_args = cmd.split()
    bin = l_args[0]
    args = l_args[1:]

    # log
    log_name = f'log_{proc_name}'
    db.delete(log_name)
    log = db.List(log_name)
    def f(l):
        line = {'time':time.time(), 'data': l}
        r.publish(p.log_channel, json.dumps(line))
        log.append(l.strip())
        
    # args
    proc_args = Dict()
    proc_args._bg = True
    proc_args._bg_exc = False
    proc_args._out = f
    proc_args._err = f


    pid = getattr(sh, bin)(*args, **proc_args.to_dict()).pid
    print('pid:', pid)

    p.pid = pid
    p.start_time = time.time()
    l = f'start {proc_name}'
    print(l)
    return p.pid

  def start_process(self, proc_name, cmd):
    print('run', proc_name, cmd)
    return self._start_process(proc_name, cmd) 

class TraceBack:
  
  def __str__(self):
    type, value, tb = traceback.sys.exc_info()
    tb = traceback.extract_tb(tb)
    formatted_frames = []
    for frame in tb:
        filename, line_number, function_name, code = frame
        if '/home/haha/anaconda3' in filename:
          continue
        formatted_frame = f'"{filename}" : {line_number}, in {function_name}\n    {code}'
        formatted_frames.append(formatted_frame)
    trace = '\n'.join(formatted_frames)
    error = f'{type} {value}'
    return f'{error}\n{trace}'


class Processor:
  class OutSream:
    lock = Lock()
    def __init__(self,org_stream, cache_name, src_name):
      self.log_cache = db.List(cache_name)
      self.log_cache.clear()
      
      self.src_name = src_name
      
      self.org_steam = org_stream
      

    cache_str = ''
    def write(self, output):
      self.lock.acquire()

      try:
        self.cache_str += output
        if output and output[-1] == '\n':
          #r.publish('/log/process', json.dumps({'src': self.src_name, 'data': self.cache_str}))

          log = Dict()
          log.src = self.src_name
          log.content = self.cache_str
          #FrameWorkBackend().send_backend_log(log)
          self.cache_str = ''
      except Exception as e:
        self.org_steam.write('outstream:'+str(e))

      self.log_cache.append(output)
      self.org_steam.write(output)

      self.lock.release()

    def flush(self):
      self.org_steam.flush()
        
  proc_cache = db.Hash('/process/name2id')
  #proc_infos = RedisCached({})
  
  def __init__(self, proc_name, block=True):
    self.proc_name = proc_name
    self.block = block
    
  @property 
  def _log_error_cache_name(self):
    return f'/log/{self.proc_name}/cache/error'
  
  @property 
  def _log_out_cache_name(self):
    return f'/log/{self.proc_name}/cache/out'
  
  @property 
  def log(self):
    return '\n'.join(db.List(self._log_out_cache_name))
  
  @property 
  def info(self):
    pid = self.proc_cache[self.proc_name]
    if pid:
      info = Dict()
      pid = int(pid)
      info.pid = pid
      
      if pid not in psutil.pids():
        info.status = 'stopped'
      else:
        info.status = psutil.Process(pid).status()
      return info
    
  def _init_env(self):
    # stdout stderr
    sys.stdout = self.OutSream(sys.stdout, self._log_out_cache_name, self.proc_name)
    sys.stderr = self.OutSream(sys.stderr, self._log_error_cache_name, self.proc_name)
    
    # clear pipe
    self.pipe_in = db.List(f'{self.proc_name}/in')
    self.pipe_in.clear()
    
    # clear log 
    db.List(self._log_error_cache_name).clear()
    db.List(self._log_out_cache_name).clear()
    
    # process info
    pid = self.proc_cache[self.proc_name]
    if pid and int(pid) in psutil.pids():
      boot_timestamp = psutil.boot_time()
      info = self.proc_infos[self.proc_name]
      if info is not None and info['start_time'] > boot_timestamp:
        return False

    info = Dict()
    info.start_time = time.time()
    self.proc_infos[self.proc_name] = info
    
    self.proc_cache[self.proc_name] = os.getpid()
    
    return True
  
  def _on_create(self):
    pass
    
  def _get_data_in(self):
    while True:
      data = self.pipe_in.popleft()
      if data is None and self.block:
        time.sleep(0.01)
        continue
      
      if data is not None:
        data = Dict(json.loads(data))
      return data
    
  def _send_data_out(self, channel_id, data):
    channel_name = f'{self.proc_name}/{channel_id}'
    r.publish(channel_name, json.dumps(data))
    
  def start(self):
    subprocess.Popen(
        f'python -m base -r {self.__class__.__name__}.loop',
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        shell=True,
      )
    
  def stop(self):
    pid = self.proc_cache[self.proc_name]
    if pid and int(pid) in psutil.pids():
      psutil.Process(int(pid)).terminate()
      
  def terminate(self):
    pid = self.proc_cache[self.proc_name]
    if pid and int(pid) in psutil.pids():
      psutil.Process(int(pid)).terminate()
      
    
  def restart(self):
    self.terminate()
    self.start()
    
  def loop(self):
    if not self._init_env():
      print({
        'type': 'error',
        'data': f'{self.__class__.__name__}\n\t process already started'
      })
      return
    self._on_create()
    while True:
      try:
        data = self._get_data_in()
        if data is not None:
          channel_id = data['channel_id']
          data = data['data']
          ret_data = self._step(data)
          self._send_data_out(channel_id, ret_data)
        else:
          ret_data = self._step(data)
      except Exception as e:
        print({
          'type': 'error',
          'data': self.__class__.__name__ + '\n\n' + str(TraceBack())
        })
        break
    
   
   
 
class TestProcessor(Processor):
  def __init__(self):
    super().__init__('test', block=False)
    
  def _step(self, data):
    for i in range(10):
      print(i)
      time.sleep(1)
    return data+'cao'
  