//@ts-ignore
import { useMemo, useState } from "react";

let print = console.log;

export async function callRemote(cls:any, init_args:any, func:any, args:any) {
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

  //const res = await fetch("https://{{backend_ip}}:{{backend_port}}/call", {
  const res = await fetch("{{ remote_url}}", {
    method: "POST", // or 'PUT'
    mode: "no-cors",
    headers: {
      "Content-Type": "application/json",
      "auth": "{{auth}}"
    },
    body: JSON.stringify(data),
  });

  clearTimeout(timeoutId);
  //return await res.json()
}

class StateHub {
  setVals: { [key: string]: any } = {};
  caches: { [key: string]: any } = {};
  sse: EventSource | null = null;
  constructor() {
    try {
      this.sse = new EventSource(
        //`https://{{backend_ip}}:{{backend_port}}/listen/${this.channelName}`
        //`{{state_hub_url}}/listen/${this.channelName}`
        '{{state_hub_url}}'
      );

      this.sse.addEventListener("update", (e) => {
        this._dispatch(e.data);
      });
    } catch (e) {
      print("fuck no sse");
    }
  }

  _dispatch(msg: string) {
    let state: { name: string; data: any } = JSON.parse(msg);
    if (state.name in this.setVals) {
      try {
        for (const setV of this.setVals[state.name]) {
          setV(state.data);
        }
      } catch (e) {
        print("error: " + e);
        print(this.setVals[state.name]);
      }
    }
  }

  destory() {
    this.sse?.close();
  }

  set(name: string, data: any) {
    this.caches[name] = data;
  }

  register(name: string, setVal: any) {
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
    this._dispatch(JSON.stringify(msg));
  }

  get(name: string) {
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
