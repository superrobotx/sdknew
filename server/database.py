import base64
import redis
from .utils import config
import threading, json
from walrus import Database

redis_conf = config.network.redis

r = redis.Redis(host=redis_conf.ip, port=redis_conf.port, db=0, password=redis_conf.passwd, decode_responses=True)
db = Database(host=redis_conf.ip, port=redis_conf.port, db=0, password=redis_conf.passwd, decode_responses=True)


class RedisBase:
  def delete(self):
    db.delete(self.name)

  @property
  def name(self):
    return self._data.key
  
  def load(self, bytes):
    self.delete()
    r.restore(self.name, ttl=0, value=bytes)

  def dump(self):
    return r.dump(self.name)
  
class RedisList(RedisBase):
  ''' 
  cache value in redis, persistant variable, list
  '''

  def __init__(self, name, default) -> None:
    self.name = name
    if not r.exists(name):
      self.set_list(default)
    
  def set_list(self, vals):
    r.delete(self.name)
    for v in vals:
      r.rpush(self.name, json.dumps(v))
    
  def __getitem__(self, index):
    if isinstance( index, slice ) :
      l = r.lrange(self.name, start=index.start or 0, end=index.stop or -1)
      return [json.loads(v) for v in l]
     
    val = r.lindex(self.name, index)
    if val is not None:
      return json.loads(val)
    raise IndexError()
  
  def __setitem__(self, index, val):
    r.lset(self.name, index, json.dumps(val))
    
  def append(self, val):
    r.rpush(self.name, json.dumps(val))
    
  def remove(self, val):
    r.lrem(self.name, 0, json.dumps(val))
    
  def __len__(self):
    return r.llen(self.name)
  
  def clear(self):
    r.delete(self.name)
  
  
class RedisHash(RedisBase): 
  ''' 
  cache value in redis, persistant variable, hash
  '''
  def __init__(self,name, default=None):
    self._data = db.Hash(name)
    if not db.exists(name) and default:
      self._data.update(default)
      

  def __getitem__(self, key):
    val = self._data[key]
    if val is not None:
      return json.loads(val)

  def __setitem__(self, key, value):
      self._data[key] = json.dumps(value)

  def __delitem__(self, key):
      del self._data[key]

  def __len__(self):
      return len(self._data)

  def __contains__(self, key):
      return key in self._data

  def keys(self):
      return self._data.keys()

  def values(self):
      return self._data.values()

  def items(self):
      return self._data.items()
    
  def set_val(self, val):
    self._data.clear()
    for k,v in val.items():
      self[k] = v
    
  def clear(self):
    self._data.clear()


class RedisSet(RedisBase):
  ''' 
  cache value in redis, persistant variable, set
  '''

  def __init__(self, name, default) -> None:
    self.name = name
    self.db = db.Set(name)
    if not r.exists(name):
      self.set(default)
    
  def set(self, vals):
    r.delete(self.name)
    for v in vals:
      self.db.add(json.dumps(v))
    
  def __setitem__(self, index, val):
    r.lset(self.name, index, json.dumps(val))
    
  def add(self, val):
    self.db.add(json.dumps(val))
    
  def remove(self, val):
    self.db.remove(json.dumps(val))
    
  def clear(self):
    self.db.clear()
    
  def __len__(self):
    return len(self.db)
  
  def __contains__(self, item):
    return item in self.db

  class Iter:
    def __init__(self, iter) -> None:
      self.iter = iter 
      
    def __next__(self):
      return json.loads(next(self.iter))
    
  def __iter__(self):
    return self.Iter(iter(self.db))

  def __str__(self):
    return str(self.db)

    

class RedisCached:
  ''' 
  cache value in redis, persistant variable
  ''' 
  _name = 'redis_cached'

  def __init__(self, default) -> None:
    self.default = default
      

  def __get__(self, obj, cls):
    # set
    if type(self.default) == set:
      return RedisSet(self.name, self.default)
    
    # list
    if type(self.default) == list:
      return RedisList(self.name, self.default)
    
    # dict
    if type(self.default) == dict:
      return RedisHash(self.name, self.default)

    # other
    value = r.hget(self._name, self.name)
    if value is None:
      return self.default

    value = json.loads(value)
    if type(self.default) != type(value): 
      print('unmatched value type')
      return self.default
    return value 

  def __set_name__(self, cls, name):
    self.name = f'{config.name}/{cls.__name__}/{name}'  
    print(self.name)
    if type(self.default) == dict and db.type(self.name) != 'hash':
      db.delete(self.name)
    if type(self.default) == list and db.type(self.name) != 'list':
      db.delete(self.name)

  def __set__(self, obj, value):
    # set
    if type(self.default) == set:
      l = RedisSet(self.name, self.default)
      l.set(value)
      
    # list
    if type(self.default) == list:
      l = RedisList(self.name, self.default)
      l.set_list(value)
      
    # dict
    if type(self.default) == dict:
      RedisHash(self.name, self.default).set_val(value)
    
    # other
    r.hset('redis_cached', self.name, json.dumps(value))

  @classmethod
  def clear_legacy(cls):
    db.Hash(cls._name).clear()

class Database:
  def __init__(self) -> None:
    pass

  def load_from_file(self, fpath):
    with open(fpath, 'r') as f:
      data = json.loads(f.read())
    for k,v in data.items():
      r.delete(k)
      r.restore(k, ttl=0, value=base64.b64decode(v))

  def dump_to_file(self, fpath):
    data = {}
    for x in dir(self):
      if x.startswith('_'):
        continue
      y = getattr(self, x)
      if isinstance(y,  RedisBase):
        data[y.name] = base64.b64encode(y.dump()).decode('utf8')
    with open(fpath, 'w') as f:
      f.write(json.dumps(data))

  def test(self):
    pass

