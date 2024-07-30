import redis, threading
import json
from base.utils import r_local

queues = {

}

class Property:
  ''' 
  propery in states.py
  '''
  def __init__(self,default_, js_channnel_name) -> None:
    self.default_ = default_
    self.js_channel_name = js_channnel_name

  def __get__(self, obj, cls):
    value = r_local.hget(f'ui/states_cache/{self.js_channel_name}', self.name)
    if value is None:
      return self.default_
    return json.loads(value)

  def __set_name__(self, cls, name):
    self.name = f'{cls.__name__}/{name}'

  def __set__(self, obj, value):
    #r.publish(self.name, json.dumps(value))
    r_local.hset(f'ui/states_cache/{self.js_channel_name}', self.name, json.dumps(value))
    r_local.publish(self.js_channel_name, json.dumps({'name':self.name,'data':value}))
    tid = threading.current_thread().ident
    if tid in queues:
      queues[tid].put({
        'name':self.name,
        'data':value
      })

  
class PropertyElectron:
  ''' 
  propery in states.py
  '''
  def __init__(self,default_, js_channnel_name) -> None:
    self.default_ = default_
    self.js_channel_name = js_channnel_name

  def __get__(self, obj, cls):
    value = r_local.hget('ui/states_cache', self.name)
    if value is None:
      return self.default_
    return json.loads(value)

  def __set_name__(self, cls, name):
    self.name = f'{cls.__name__}/{name}'

  def __set__(self, obj, value):
    #r.publish(self.name, json.dumps(value))
    r_local.hset('ui/states_cache', self.name, json.dumps(value))
    r_local.publish(self.js_channel_name, json.dumps({'name':self.name,'data':value}))
  