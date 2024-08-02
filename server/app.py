from flask import Flask, Response, make_response, redirect, request, send_from_directory, stream_with_context
from omegaconf import OmegaConf
from .utils import *
from werkzeug.serving import run_simple
from . import chains
from flask_cors import CORS


import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
CORS(app)


dist_dir = os.path.abspath('./web/dist')


@app.route('/')
def index():
  print(request.headers)
  if config.dev_mode:
    return redirect(f"http://{config.network.local.backend_ip}:{config.network.vite_port}/", code=302)
  print(request.headers)
  if request.cookies.get('auth') != config.auth:
    return '<h1>fuck</h1>', 200
  return send_from_directory(dist_dir, 'index.html')

@app.route('/ping')
def ping():
  return '<b>hello</b>', 200

# Serve static files
@app.route('/<path:path>')
def serve_static(path):
  if request.cookies.get('auth') != config.auth:
    return 'fuck', 200
  print('serve', path)
  return send_from_directory(dist_dir, path)


@app.route('/stream', methods=['GET', 'POST'])
def stream():
    try:
      data = Dict(json.loads(request.get_data()))
      #data = chains.PreventResend(data)()
      call_backend = chains.CallBackend(data)
      call_backend.stream()

      return Response(stream_with_context(call_backend.stream_response()), status=200)

    except Exception as e:
      print(e)  
      traceback.print_exc()
      print('data:', request.get_data())
      return json.dumps({}), 500

@app.route('/call', methods=['GET', 'POST'])
def call():
    try:
      data = Dict(json.loads(request.get_data()))
      #data = chains.PreventResend(data)()
      ret = chains.CallBackend(data).call_func()

      return ret or {}, 200

    except Exception as e:
      print(e)  
      traceback.print_exc()
      print('data:', request.get_data())
      return json.dumps({}), 500


@app.route('/listen/<name>', methods=['GET'])
def listen(name):
  print('listen on', name)

  def stream():
    sub = r.pubsub()
    sub.subscribe(name)
    while True:
      try:
        msg = sub.get_message(timeout=1) # don't set too hight so sse can't exit
        if msg and type(msg['data']) == str:
          event = 'update'
          data = msg['data']
          print('data from', name, json.loads(data)['name'], len(data))
          yield f'event: {event}\ndata: {data}\n\n'
        elif msg is not None:
          print('sse listen recieve unhandle msg', msg)
      except Exception as e:
        print(e)
        traceback.print_exc()

  
  #response.headers['Cache-Control'] = 'no-cache'
  #response.headers['Connection'] = 'keep-alive',
  #response.headers['x-no-compression'] = 'true'
  headers = {
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'x-no-compression':'true',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET',
    'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, '
  }
  response = make_response(Response(stream(), mimetype='text/event-stream', headers=headers))

  del response.headers['Transfer-Encoding']



  return response

