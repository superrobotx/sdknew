import glob
import socket
import json
import shutil
from omegaconf import OmegaConf
import re
from addict import Dict
from jinja2 import Environment, FileSystemLoader
from .utils import config
import ast, os

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

  def get_local_ip(self):
    # Create a socket object
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Connect to a remote address that is unlikely to exist
        sock.connect(('10.255.255.255', 1))
        # Get the local IP address
        ip_address = sock.getsockname()[0]
    except Exception:
        # If the above method fails, fallback to getting the hostname
        ip_address = socket.gethostbyname(socket.gethostname())
    finally:
        # Close the socket
        sock.close()

    return ip_address


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

def render(fname, **argv):
  dir = os.path.abspath(os.path.join('./sdk/templates'))
  environment = Environment(loader=FileSystemLoader(dir))
  template = environment.get_template(fname)

  content = template.render(**argv)
  return content


class PyMapProvider:
  ''' 
  provider codeMap for vscode
  '''
  
  # varible
  reg_oneline_comments = re.compile(r'^\s*#\s+(.*)$')
  comment_icon_outline = Icons.cat_outline
  comment_icon = Icons.cat
  function_icon_outline = Icons.robot_outline
  function_icon = Icons.robot
  class_icon_outline = Icons.flower_outline
  class_icon = Icons.flower
  
  def __init__(self, code):
    self.code = code

  def _parse_func(self, code, node:ast.FunctionDef):
    lines = code.split('\n')
    info = Dict()
    info.name = node.name
    info.args = [arg.arg for arg in node.args.args]
    info.children = self._parse_comments('\n'.join(lines[1:]),node.lineno+1)
    info.iconPath = self.function_icon_outline
    info.lineno = node.lineno 
    return info
    
  def _parse_comments(self, code, base_line):
    tmp = []
    for i, l in enumerate(code.split('\n')):
      m =  re.match(self.reg_oneline_comments, l)
      if m:
        info = Dict()
        info.name = m.group(1).strip()
        info.iconPath = self.comment_icon_outline
        info.lineno = base_line + i
        info.children = []
        tmp.append(info)
    return tmp
        
  def _parse_class(self, code, cls_node):
    lines = code.split('\n')
    base_line = cls_node.lineno
      
    info = Dict()
    info.name = cls_node.name
    info.line_start = base_line
    info.lineno = base_line
    info.iconPath = self.class_icon_outline
    
    
    children = []
    last_end_line = base_line
    for i, node in enumerate(ast.iter_child_nodes(cls_node)):
        
      # doc
      if isinstance(node, ast.Expr) and i == 0:
        info.doc = node.value.value.strip()
        continue
      
      # lines between nodes
      line_no = node.lineno
      comment_code = '\n'.join(lines[last_end_line-base_line: line_no-base_line])
      
      if line_no - last_end_line > 1:
        comments = self._parse_comments(comment_code, last_end_line+1)
        if comments:
          children += comments
      last_end_line = node.end_lineno + 1
      
      node_code = '\n'.join(lines[node.lineno-1-base_line: node.end_lineno-base_line])
      # class
      if isinstance(node, ast.ClassDef):
        child = self._parse_class(node_code, node)
        if child is not None:
          children.append(child)
          
      # function
      if isinstance(node, ast.FunctionDef):
        child = self._parse_func(node_code, node)
        if child is not None:
          children.append(child)
    info.children = children
    return info

  def _first_layer(self, code):
    lines = code.split('\n')
    try:
      tree = ast.parse(code)
    except:
      return None
    tmp = []
    for i, node in enumerate(ast.iter_child_nodes(tree)):
      if isinstance(node, ast.ClassDef):
        cls_code = '\n'.join(lines[node.lineno:node.end_lineno+1])
        tmp.append(self._parse_class(cls_code, node))
    return tmp
  
  def _post_process(self, code_map):
    for node in code_map:
      self._post_process(node.children)
    
    
  @property
  def code_map(self):
    code = self.code
    code_map = self._first_layer(code)
    if code_map:
      self._post_process(code_map)
    return code_map
  
  def __getitem__(self, name):
    for cls in self.code_map:
      if cls.name == name:
        return cls
      
    

class PyUICodeGenerator:
  ''' 
  generate states.py file from state.yml file, python code generator
  '''

  def generate(self, target_file):

    classes = []
    for cls_name_snake, props in config.state.items():
      cls = Dict()
      cls.name_snake = cls_name_snake
      cls.name = Misc().snake_to_camel(cls_name_snake)

      cls.props = []
      for prop_name, default_ in props.items():
        prop = Dict()
        default_ = json.dumps(default_)
        default_ = default_.replace('true', 'True'
                          ).replace('false', 'False'
                          ).replace('null', 'None')
        prop.default = default_
        prop.name = prop_name
        cls.props.append(prop)
      classes.append(cls)

    # render jinja 
    channel_name = config.name
    text = render('state.py.j2', classes=classes, channel_name=channel_name)


    with open(target_file, 'w') as f:
      f.write(text)


class JsUICodeGenerator:
  ''' 
  generate states.js file from state.yml file, js code generator
  '''

  def _key_word_filter(self, default):
    if type(default) == str:
      default = json.dumps(default)

    if default is False:
      default = 'false'

    elif default is True:
      default = 'true'

    elif default is None:
      default = 'null'

    return default
  
  def generate(self, target_file):
    classes = []
    for cls_name_snake, props_ in config.state.items():
      cls = Dict()
      cls.name_snake = cls_name_snake
      cls.name = Misc().snake_to_camel(cls_name_snake)

      props = []
      for prop_name, default in props_.items():
        prop = Dict()

        prop.name = prop_name

        prop.channel_name = f'{cls.name}/{prop_name}' 

        prop.default_value = self._key_word_filter(default)

        props.append(prop)
      cls.props = props

      classes.append(cls)

    text = render('state.js.j2', classes=classes, misc_file='misc')
    with open(target_file, 'w') as f:
      f.write(text)

class DartUICodeGenerator:
  ''' 
  generate states.js file from state.yml file, js code generator
  '''

  def _key_word_filter(self, default):
    if type(default) == str:
      default = json.dumps(default)

    if default is False:
      default = 'false'

    elif default is True:
      default = 'true'

    elif default is None:
      default = 'null'

    return default
  
  def generate(self, target_file):
    classes = []
    for cls_name_snake, props_ in config.state.items():
      cls = Dict()
      cls.name_snake = cls_name_snake
      cls.name = Misc().snake_to_camel(cls_name_snake)

      props = []
      for prop_name, default in props_.items():
        prop = Dict()

        prop.name = prop_name

        prop.channel_name = f'{cls.name}/{prop_name}' 

        prop.default_value = self._key_word_filter(default)

        props.append(prop)
      cls.props = props

      classes.append(cls)

    text = render('state.dart.j2', classes=classes)
    with open(target_file, 'w') as f:
      f.write(text)

class DartRemoteCodeGenerator:   
  ''' 
  auto generate js remote code when this file changed
  '''
  def generate(self, target_file):

    classes = []
    with open(config.backend_file, 'r') as f:
      text = f.read()
    for cls_node in PyMapProvider(text).code_map:
      cls = Dict()
      if 'Backend' in cls_node.name:
        cls.name = cls_node.name
        cls.funcs = self._generate_cls_funcs(cls_node)
    classes.append(cls)

    backend_ip = config.network.backend_ip
    if backend_ip in ['localhost', '0.0.0.0']:
      backend_ip = Misc().get_local_ip()
    backend_url = f'http://{config.network.backend_ip}:{config.network.backend_port}'
    text = render('remote.dart.j2', classes=classes, backend_url=backend_url)
    with open(target_file, 'w') as f:
      f.write(text)

    
  def _generate_cls_funcs(self, cls_node):

    funcs = []
    for func_node in cls_node.children:
      func = Dict()
      func.name = func_node.name
      parameters = func_node.args
      parameters = [p for p in parameters if p != 'self']
      parameters = list(map(lambda p: 'default_' if p=='default' else p, parameters))
      if func.name[0] == '_':
          continue
      args = ','.join(parameters)
      args_dict = ','.join([f'"{p}":{p}' for p in parameters])
      func.args = args
      func.args_dict = args_dict
      funcs.append(func)

    return funcs
    
  


class JSRemoteCodeGenerator:   
  ''' 
  auto generate js remote code when this file changed
  '''
  def generate(self, target_file):

    classes = []
    with open(config.backend_file, 'r') as f:
      text = f.read()
    for cls_node in PyMapProvider(text).code_map:
      cls = Dict()
      if 'Backend' in cls_node.name:
        cls.name = cls_node.name
        cls.funcs = self._generate_cls_funcs(cls_node)
    classes.append(cls)

    text = render('remote.js.j2', classes=classes, misc_file='misc')
    with open(target_file, 'w') as f:
      f.write(text)

    
  def _generate_cls_funcs(self, cls_node):

    funcs = []
    for func_node in cls_node.children:
      func = Dict()
      func.name = func_node.name
      parameters = func_node.args
      parameters = [p for p in parameters if p != 'self']
      parameters = map(lambda p: 'default_' if p=='default' else p, parameters)
      if func.name == '__init__':
          args = ','.join(parameters)
      elif func.name[0] == '_':
          continue
      else:
        args = ','.join(parameters)
      func.args = args
      funcs.append(func)

    return funcs
    
  

    
class PyRemoteCodeGenerator:
  def __init__(self) -> None:
    pass

  def generate(self, config, target_file):
    classes = []

    with open(config.backend_file, 'r') as f:
      text = f.read()

    for cls in PyMapProvider(text).code_map:
      if not cls['name'].lower().endswith("backend"):
        continue
      cls_ = {}
      cls_['name'] = cls['name']
      cls_['children'] = []

      for func in cls['children']:
        if func['name'][0] == '_':
          continue

        if func['args'][0] == 'self':
          func['args'].pop(0)
        cls_['children'].append(func)
      classes.append(cls_)


    content = render('remote.py.j2', classes=classes, port=config.backend_port)

    with open(target_file, 'w') as f:
      f.write(content)


    
class JSMiscCodeGenerator: 
  def __init__(self) -> None:
    pass

  def generate(self, target_file):
    if config.dev_mode:
      state_hub_url = f'http://{config.network.backend_ip}:{config.network.backend_port}/listen/{config.name}'
      remote_url = f'http://{config.network.backend_ip}:{config.network.backend_port}/stream'
      local_url = f'http://localhost:{config.network.backend_port}/stream'

    args = {
      'channel_name': config.name,
      'state_hub_url': state_hub_url,
      'remote_url': remote_url,
      'auth': config.auth,
      'local_url': local_url
    }
    content = render('misc.ts', **args)
    with open(target_file, 'w') as f:
      f.write(content)

    ''' 
    content = render('misc_electron.js', **args)
    target_file = './generated/misc_electron.js'
    with open(target_file, 'w') as f:
      f.write(content)
    '''

class DockerConfigGenerator:
  def __init__(self) -> None:
    pass

  def generate(self, config, target_file):
    args = {
      'UI': f'{config.name}_ui',
      'BACKEND': f'{config.name}_backend'
    }
    content = render('compose.example.yaml', **args)
    with open(target_file, 'w') as f:
      f.write(content)

class ViteConfigGenerator:
  def __init__(self) -> None:
    pass

  def generate(self, config, target_file):
    args = {
      'PORT': config.network.vite_port
    }
    content = render('vite.config.js.j2', **args)
    with open(target_file, 'w') as f:
      f.write(content)

class FrpConfigGenerator:
  def __init__(self) -> None:
    pass

  def generate(self):
    # frpc 

    args = {
      'remote_ip': config.network.frp.client.ip,
      'remote_port': config.network.frp.client.remote_port,
      'local_port': config.network.frp.client.local_port,
    }
    src_fname = 'frpc.toml.j2'
    content = render(src_fname, **args)
    target_file = './tmp/{}'.format(
      src_fname.replace(".j2", "")
    )
    with open(target_file, 'w') as f:
      f.write(content)

    # frps

    args = {
    }
    src_fname = 'frps.toml.j2'
    content = render(src_fname, **args)
    target_file = './tmp/{}'.format(
      src_fname.replace(".j2", "")
    )
    with open(target_file, 'w') as f:
      f.write(content)

class AndroidManifestGenerater:
  def __init__(self) -> None:
    pass

  def generate(self, target_file):
    args = {
      'permissions': config.app.permissions,
      'label': config.name
    }
    src_fname = 'AndroidManifest.xml.j2'
    content = render(src_fname, **args)
    with open(target_file, 'w') as f:
      f.write(content)

class AssetsGenerator:
  def __init__(self) -> None:
    pass

  def cut_image_to_square(self, img_path, tag='up'):
    from PIL import Image
    """
    Cuts an image to a square shape based on the specified tag position.

    Parameters:
    - img_path: Path to the image file.
    - tag: Position to focus on when cropping ('up', 'left', 'right', 'center', 'down').

    Returns:
    - A PIL Image object of the cropped square image.
    """
    # Open the image
    img = Image.open(img_path)
    width, height = img.size

    # Determine the size of the square (the side length of the square is the smaller dimension of the image)
    side_length = min(width, height)

    # Calculate the cropping box coordinates based on the tag
    if tag == 'up':
        left = (width - side_length) / 2
        upper = 0
    elif tag == 'left':
        left = 0
        upper = (height - side_length) / 2
    elif tag == 'right':
        left = width - side_length
        upper = (height - side_length) / 2
    elif tag == 'center':
        left = (width - side_length) / 2
        upper = (height - side_length) / 2
    elif tag == 'down':
        left = (width - side_length) / 2
        upper = height - side_length
    else:
        raise ValueError("Invalid tag. Choose from 'up', 'left', 'right', 'center', 'down'.")

    # Calculate right and lower coordinates for the cropping box
    right = left + side_length
    lower = upper + side_length

    # Crop the image
    img_cropped = img.crop((left, upper, right, lower))

    return img_cropped

  def generate(self, app_dir):
    # copy assets from res to app/assets
    tmp = []
    for dpath in config.app.assets:
      destination_dir = os.path.join(app_dir, 'assets', os.path.basename(dpath))
      fpaths = glob.glob(f'{destination_dir}/*')
      tmp += [re.match('.*(assets.*)', f).group(1) for f in fpaths]

      if os.path.exists(destination_dir):
        shutil.rmtree(destination_dir)
      shutil.copytree(dpath, destination_dir)

    shutil.copy2('./config.yaml', './app/assets/')

    # add assets to pubspec.yaml
    x = OmegaConf.load('./app/pubspec.yaml')
    x.flutter.assets = tmp
    x.flutter.assets.append('assets/config.yaml')
    OmegaConf.save(x, './app/pubspec.yaml')

    # icon generate
    os.chdir('./app')
    data = {'flutter_icons':config.app.flutter_icons.to_dict()}
    conf = OmegaConf.create(dict(data))
    file_path = './flutter_icons.yaml'
    OmegaConf.save(conf, file_path)

    image_path = config.app.flutter_icons.image_path
    self.cut_image_to_square(image_path, tag='center').save(image_path)
    os.system(f'flutter pub run flutter_launcher_icons -f {file_path}')

    # rename package
    data = {'package_rename_config':config.app.package_rename_config.to_dict()}
    conf = OmegaConf.create(dict(data))
    file_path = './rename_config.yaml'
    OmegaConf.save(conf, file_path)
    os.system(f'dart run package_rename --path="{file_path}"')

    # add utils lib
    pubspec_file = './pubspec.yaml'
    conf = OmegaConf.load(pubspec_file)
    conf['dependencies']['utils'] = {'path': '../sdk/utils/dart'}
    OmegaConf.save(conf, pubspec_file)



def code_generate():
  print('generate python states')
  if not os.path.exists('./backend/generated'):
    os.makedirs('./backend/generated')
  PyUICodeGenerator().generate('./backend/generated/state.py')

  print('generate js states')
  if not os.path.exists('./web/src/generated'):
    os.makedirs('./web/src/generated')
  JsUICodeGenerator().generate('./web/src/generated/state.js')
  JSMiscCodeGenerator().generate('./web/src/generated/misc.ts')
  JSRemoteCodeGenerator().generate('./web/src/generated/remote.js')

  print('generate androidmanifest')
  AndroidManifestGenerater().generate('./app/android/app/src/main/AndroidManifest.xml')


  print('dart states remote generate')
  os.makedirs('./app/lib/generated', exist_ok=True)
  DartRemoteCodeGenerator().generate('./app/lib/generated/remote.dart')
  DartUICodeGenerator().generate('./app/lib/generated/state.dart')

  FrpConfigGenerator().generate()

def web_generate():
  print('yarn link')
  curdir = os.path.abspath(os.curdir)
  os.chdir('./sdk/utils/js')
  os.system('yarn link')
  os.chdir(f'{curdir}/web')
  os.system('yarn link utils')

def app_generate():
  print('generate android icon')
  AssetsGenerator().generate(app_dir='./app')
