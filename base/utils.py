import time, os, pickle, sh, tempfile, base64, traceback, re, inspect, json
from tqdm import tqdm
import io, psutil, socket, sys, random, glob, hashlib, subprocess
import shutil
import soundfile as sf
from fractions import Fraction
from omegaconf import OmegaConf
from functools import partial
from contextlib import closing
from pydub import AudioSegment
from threading import Lock
import requests, threading
from itertools import cycle
import sounddevice as sd
from threading import Thread
import redis
from walrus import Database
from addict import Dict
import numpy as np
from multiprocessing import Process, Queue

class Task:
    tasks = []
    max_tasks = 64


    def __init__(self, func, *args, **argv) -> None:
        self.q = Queue()
        self.id = str(random.randint(0, 999999))
        self.func = func 
        self.args = args
        self.argv = argv
        self._result = None
        self.db_cache = Database(decode_responses=False).Hash('task/ids')

    def _run_in_child(self):
        try:
            ret = self.func(*self.args, **self.argv)
        except Exception as e:
            #self.q.put(e)
            self.db_cache[self.id] = pickle.dumps(e)
            return
        self.db_cache[self.id] = pickle.dumps(ret)
        #self.q.put(ret)

    @classmethod
    def get_running_tasks_number(cls):
        for p in cls.tasks:
          if not p.is_alive():
             cls.tasks.remove(p)
        return len(cls.tasks) 
    
    def run(self):
        p = Process(target=self._run_in_child)
        self.p = p
        self.tasks.append(p)

        while True:
          if self.get_running_tasks_number() > self.max_tasks:
            time.sleep(1)
            continue
          break
            
        p.start()

    @classmethod
    def join_all(cls):
      while True:
        if cls.get_running_tasks_number() > 0:
          time.sleep(1)
          continue
        break

    def get_result(self):
        if self._result is None:
          self.p.join()
          #self._result = self.q.get()
          self._result = pickle.loads(self.db_cache[self.id])
          del self.db_cache[self.id]
        if type(self._result) != Exception:
            return self._result
        raise Exception('child exception:' + str(self._result))
    
    @property
    def is_running(self):
        return self.p.is_alive()




def run_task(func):
    def wrapper(*args, **kwargs):
        t = Task(func, *args, **kwargs)
        t.run()
        return t
    return wrapper

config_file = './config.yaml'
config = Dict(OmegaConf.to_container(OmegaConf.load(config_file)))
redis_conf = config.network.redis

#db = Database(decode_responses=True)
#r = redis.Redis(decode_responses=True)
r = redis.Redis(host=redis_conf.ip, port=redis_conf.port, db=0, password=redis_conf.passwd, decode_responses=True)
db = Database(host=redis_conf.ip, port=redis_conf.port, db=0, password=redis_conf.passwd, decode_responses=True)
r.config_set('client-output-buffer-limit',
      'normal 0 0 0 slave 268435456 67108864 60 pubsub 1530554432 1800388608 60')

r_local = redis.Redis(decode_responses=True)
db_local = Database(decode_responses=True)
r_local.config_set('client-output-buffer-limit',
      'normal 0 0 0 slave 268435456 67108864 60 pubsub 1530554432 1800388608 60')


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


_print = print
if not Misc().is_notebook():
  # print can't rename in jupyer notebook
  def printfunc(*args):
    '''
    redefine print to add class name in front of every line
    '''
    stack = inspect.stack()
    local = stack[1][0].f_locals
    prefix = ''
    if 'self' in local:
      prefix = local["self"].__class__.__name__
    else:
      prefix = stack[1][0].f_code.co_name
    _print(prefix,':',  *args)
  print = printfunc

class NetUtil:
  ''' 
  network utils, get free port,
  '''
  def get_free_port():
      with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
          s.bind(('', 0))
          s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
          return s.getsockname()[1]

class Utils:
  def __init__(self) -> None:
    pass
  
  # float number to fraction ,return numerator and denominator
  def float_to_fraction(self, float_num):
      fraction = Fraction(float_num).limit_denominator()
      numerator = fraction.numerator
      denominator = fraction.denominator
      return numerator, denominator
  
  # speed up audio tempo
  audio_speed_up_method_librosa = 'librosa'
  audio_speed_up_method_pydub = 'pydub'
  audio_speed_up_method_torch = 'torch'
  def audio_speed_up(self, audio:np.ndarray, fs, rate, method='librosa'):
    if method == self.audio_speed_up_method_librosa:
      import librosa 
      if audio.dtype != np.float32:
        audio = self.audio_change_dtype(audio, fs)
      return librosa.effects.time_stretch(audio, rate=rate)
    
    if method == self.audio_speed_up_method_pydub:
      from pydub.effects import speedup
      from pydub import AudioSegment
      
      audio_file = self.audio_to_byte_io(audio, fs)
      audio = AudioSegment.from_file(audio_file)
      
      audio = speedup(audio, playback_speed=rate)
      
      audio_np = np.array(audio.get_array_of_samples())

      if audio.channels == 2:
          audio_np = audio_np.reshape((-1, 2))
      return audio_np
          
      
    if method == self.audio_speed_up_method_torch:
      import  torch
      import torch as torch_time_stretch
      if audio.dtype == np.int16:
        sample = self.audio_change_dtype(audio, fs, 'float32')
      else:
        sample = audio
      if len(sample.shape) == 1:
        sample = sample.reshape(1, -1)
      else:
        sample.shape = (sample.shape[1], -1)
      sample = sample.T
      sample = torch.tensor(
          [np.swapaxes(sample, 0, 1)],  # (samples, channels) --> (channels, samples)
          dtype=torch.float32,
          device="cuda" if torch.cuda.is_available() else "cpu",
      ) 
      
      numer, deno = self.float_to_fraction(rate)
      up = torch_time_stretch.time_stretch(sample,
            torch_time_stretch.Fraction(deno, numer) , fs)
      audio = up.cpu().numpy()[0][0]
      return audio


      
  # write audio into byte io
  def audio_to_byte_io(self, audio, fs):
    audio_file = io.BytesIO()

    sf.write(audio_file, audio, fs, format='wav')
    audio_file.seek(0)
    
    return audio_file
    
  
  # change audio dtype
  def audio_change_dtype(self, audio, fs, dtype='float32'):
    if dtype == 'float32':
      audio_file = self.audio_to_byte_io(audio, fs)
      import librosa 
      wav, _ = librosa.load(audio_file, sr=fs, dtype=dtype, mono=True)
      return wav
    
    if dtype == 'int16':
      return (audio* 32767).astype(np.int16)
    
    raise Exception('only support float32 int16')
        
  # md5 hash
  def md5_hash(self, text):
    md5_hash = hashlib.md5()
    md5_hash.update(text.encode('utf-8'))
    return md5_hash.hexdigest()
  
    
  
  def mp3_bytes_to_numpy(audio_bytes):
      audio_stream = io.BytesIO(audio_bytes)
      audio_segment = AudioSegment.from_file(audio_stream, format='mp3')
      audio_array = np.array(audio_segment.get_array_of_samples())
      return audio_array
    
utils = Utils()

class Directory:
  ''' 
  a directory use as favorites or trash dir
  '''
    
  def __init__(self, root):
    if not os.path.exists(root):
      os.mkdir(root)
    self.root = root
    self.db = db.List(self._hash(root))
  
  def _hash(self, text):
    md5_hash = hashlib.md5()
    md5_hash.update(text.encode('utf-8'))
    return md5_hash.hexdigest()
  
  def move_in(self, fpath):
    if not os.path.exists(fpath):
      print('file no exists', fpath)
      return
    
    ext = os.path.splitext(fpath)[1]
    fname = f'{self._hash(fpath)}{ext}'
    tpath = os.path.join(self.root, fname)
    track = Dict()
    track.src = fpath
    track.dst = tpath
    
    print(fpath, tpath)
    try:
      shutil.move(fpath, tpath)
    except :
      traceback.print_exc()
    self.db.append(json.dumps(track))
    
  class FileNoFound(Exception):
    def __init__(self) -> None:
      pass
    
  class FileAlreadyExists(Exception):
    def __init__(self) -> None:
      pass
    
  def copy_in(self, fpath):
    fname = os.path.basename(fpath)
    tpath = os.path.join(self.root, fname)
    
    if not os.path.exists(fpath):
      raise self.FileNoFound()
    if os.path.exists(tpath):
      raise self.FileAlreadyExists()
    
    shutil.copyfile(fpath, tpath)
    
  
  def move_out(self, fpath=None):
    if not self.db:
      print('nothing to move')
      return
    
    if fpath is None:
      track = self.db.popright()
      track = Dict(json.loads(track))
      shutil.move(track.dst, track.src)
      return track.src
    else:
      for track in self.db:
        track = Dict(json.loads(track))
        if track.src == fpath:
          shutil.move(track.dst, track.src)
          r.lrem(self._hash(self.root), 0, json.dumps(track))
          return
      print('nothing to move')
          