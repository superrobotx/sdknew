import { createClient } from 'redis';
import {useMemo, useRef, useState, Component, createRef, PureComponent, memo } from 'react'
import { commandOptions } from 'redis';

let print = console.log;

export async function callRemote(cls, init_args, func, args) {
  const data = {
    cls_name: cls,
    func_name: func,
    init_args: init_args,
    func_args: args,
  };

  const timeoutId = setTimeout(() => {
    new AbortController().abort();
    console.log("abort " + func);
  }, 20000);

  const res = await fetch("{{local_url}}", {
    method: "POST", // or 'PUT'
    mode: "no-cors",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  clearTimeout(timeoutId);
}

class Redis {
  //  redis constructor
  constructor() {
    this.client = createClient()
    this.client.on('error', err => console.log('Redis Client Error', err));
  }

  async connect() {
    await this.client.connect();
  }

  async lget(k, st = 0, ed = -1) {
    // lget comment
    function lgetx() { }
    return await this.client.lRange(k, st, ed)
  }

  async rpush(k, v) {
    await this.client.rPush(k, v)
  }

  async blpop(k, timeout = 6) {
    return await this.client.blPop(
      commandOptions({ isolated: true }),
      k, timeout)
  }

  async delete(k) {
    this.client.del(k)
  }

  set(k, v) {
    this.client.set(k, v)
  }

  async get(k) {
    this.client.get(k)
  }

  async hset(name, k, v) {
    await this.client.hSet(name, k, v)
  }

  async hget(name, k) {
    return await this.client.hGet(name, k)
  }

  async disconnect() {
    await this.client.disconnect();
  }

  async subscribe(name, callback) {
    const subscriber = this.client.duplicate();
    subscriber.on('error', err => console.error(err));
    await subscriber.connect();
    await subscriber.subscribe(name, callback);
    return subscriber
  }

  async publish(name, msg) {
    await this.client.publish(name, msg);
  }
}

export const r = new Redis()


class StateHub {
  channelName = '{{channel_name}}'
  reidsCacheName = 'ui/states_cache/{{channel_name}}'
  setVals = {}
  caches = {}
  subs = []
  sub = null
  constructor() {
  }

  async init() {
    await r.subscribe(this.channelName, this._dispatch.bind(this)).then(sub => {
      this.sub = sub
    })
  }

  _dispatch(msg) {
    msg = JSON.parse(msg)
    if (msg.name in this.setVals)
    {
      try
      {
        for (const f of this.setVals[msg.name])
        {
          f(msg.data)
        }
      } catch (e)
      {
        print('error: ' + e)
        print(this.setVals[msg.name])
      }
    }
  }

  addSub(sub) {
    this.subs.push(sub)
  }

  destory() {
    this.sub.disconnect()
    for (const sub of this.subs)
    {
      sub.disconnect()
    }
  }

  set(name, data) {
    r.hset(this.reidsCacheName, name, JSON.stringify(data))
    this.caches[name] = data
  }

  register(name, setVal) {
    if (!(name in this.setVals))
    {
      this.setVals[name] = []
    }
    if (this.setVals[name].includes(setVal))
    {
      return
    }
    this.setVals[name].push(setVal)
  }

  publish(name, data) {
    const msg = {
      name,
      data
    }
    r.publish(this.channelName, JSON.stringify(msg))
  }

  get(name) {
    return this.caches[name]
  }
}
// initialize 
const stateHub = new StateHub()

export function setProperty(name, data) {
  stateHub.set(name, data)
}

export function getProperty(name, default_) {
  return stateHub.get(name) ?? default_
}

export function sendProperty(name, data) {
  stateHub.publish(name, data)
}

export function useProperty(name, default_) {
  const [data, SetV] = useState(default_)
  stateHub.set(name, data)

  useMemo(function () {
    stateHub.register(name, SetV)
  }, [])
  return data
}

async function init(){
  await r.connect()
  await stateHub.init()
}

init()
