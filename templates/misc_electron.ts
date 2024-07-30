//@ts-ignore
import { createClient, RedisClient } from "redis";
import {
  useMemo,
  useState,
//@ts-ignore
} from "react";

//@ts-ignore
import { commandOptions } from "redis";

let print = console.log;

print("fuck");

export async function callRemote(
  cls: any,
  init_args: any,
  func: any,
  args: any
) {
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
  client: RedisClient;

  //  redis constructor
  constructor() {
    this.client = createClient();
    this.client.on("error", (err: Error) =>
      console.log("Redis Client Error", err)
    );
  }

  async connect() {
    await this.client.connect();
  }

  async lget(k: string, st = 0, ed = -1) {
    // lget comment
    function lgetx() {}
    return await this.client.lRange(k, st, ed);
  }

  async rpush(k: string, v: any) {
    await this.client.rPush(k, v);
  }

  async blpop(k: string, timeout = 6) {
    return await this.client.blPop(
      commandOptions({ isolated: true }),
      k,
      timeout
    );
  }

  async delete(k: string) {
    this.client.del(k);
  }

  set(k: string, v: any) {
    this.client.set(k, v);
  }

  async get(k: string) {
    this.client.get(k);
  }

  async hset(name: string, k: string, v: any) {
    await this.client.hSet(name, k, v);
  }

  async hget(name: string, k: any) {
    return await this.client.hGet(name, k);
  }

  async disconnect() {
    await this.client.disconnect();
  }

  async subscribe(name: string, callback: Function) {
    const subscriber = this.client.duplicate();
    subscriber.on("error", (err: Error) => console.error(err));
    await subscriber.connect();
    await subscriber.subscribe(name, callback);
    return subscriber;
  }

  async publish(name: string, msg: string) {
    await this.client.publish(name, msg);
  }
}

export const r = new Redis();

class StateHub {
  channelName = "{{channel_name}}";
  reidsCacheName = "ui/states_cache/{{channel_name}}";
  setVals: { [key: string]: Function[] } = {};
  caches: { [key: string]: any } = {}
  subs: any[] = [];
  sub: any = null;
  constructor() {}

  async init() {
    await r
      .subscribe(this.channelName, this._dispatch.bind(this))
      .then((sub) => {
        this.sub = sub;
      });
  }

  _dispatch(msgStr: string) {
    let msg: any = JSON.parse(msgStr);
    if (msg.name in this.setVals) {
      try {
        for (const f of this.setVals[msg.name]) {
          f(msg.data);
        }
      } catch (e) {
        print("error: " + e);
        print(this.setVals[msg.name]);
      }
    }
  }

  addSub(sub: any) {
    this.subs.push(sub);
  }

  destory() {
    this.sub?.disconnect();
    for (const sub of this.subs) {
      sub.disconnect();
    }
  }

  set(name: string, data: any) {
    r.hset(this.reidsCacheName, name, JSON.stringify(data));
    this.caches[name] = data;
  }

  register(name: string, setVal: Function) {
    if (!(name in this.setVals)) {
      this.setVals[name] = [];
    }
    if (this.setVals[name].includes(setVal)) {
      return;
    }
    this.setVals[name].push(setVal);
  }

  publish(name: string, data: any) {
    const msg = {
      name,
      data,
    };
    r.publish(this.channelName, JSON.stringify(msg));
  }

  get(name:string) {
    return this.caches[name];
  }
}
// initialize
const stateHub = new StateHub();

export function setProperty(name: string, data: any) {
  stateHub.set(name, data);
}

export function getProperty(name: string, default_: any) {
  return stateHub.get(name) ?? default_;
}

export function sendProperty(name: string, data: any) {
  stateHub.publish(name, data);
}

export function useProperty(name: string, default_: any) {
  const [data, SetV] = useState(default_);
  stateHub.set(name, data);

  useMemo(function () {
    stateHub.register(name, SetV);
  }, []);
  return data;
}

async function init() {
  await r.connect();
  await stateHub.init();
}

init();
