from .app import app
from .utils import *
from .hub import *

def run():
  if config.dev_mode:
    print('------- run in dev -------')

  args = sys.argv
  if len(args) == 1:
    port = config.network.backend_port

    print(f'service {config.name} run at {port}')

    if config.dev_mode:
      app.run(
        host='0.0.0.0', port=port, 
        use_reloader=False, threaded=True,
        processes=1
      )
    else:
      context = ('./res/certificate.crt', './res/private.key')
      app.run(
        host='0.0.0.0', port=port, 
        ssl_context=context, use_reloader=False, threaded=True,
        processes=1
      )
  if len(args) == 2 and args[1] == 'remote':
    print('remote')
