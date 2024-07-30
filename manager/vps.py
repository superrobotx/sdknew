import os 
from .utils import config

''' 
mkdir -p ~/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
rm -rf ~/miniconda3/miniconda.sh
'''

class VPS:
  def __init__(self) -> None:
    pass

  @property
  def ssh_url(self):
    return f"{config.network.ssh.username}@{config.network.ssh.ip}"

  def _run_remote(self, cmd):
    remote_cmd = f'sshpass -p "{config.network.ssh.passwd}"\
        ssh {self.ssh_url} \
        "{cmd}"'
    print(remote_cmd)
    os.system(remote_cmd)

  def _push_to_remote(self, src, dst):
    remote_cmd = 'sshpass -p "{}" scp -r {} {}:/home/ubuntu/{}'.format(
      config.network.ssh.passwd, 
      src, self.ssh_url, dst
    )
    print(remote_cmd)
    os.system(remote_cmd)

  def install_requirements(self):

    self._push_to_remote('requirements.txt', 'requirements.txt')
    self._run_remote('pip install -r requirements.txt')

    ''' 
    self._run_remote('sudo apt install ffmpeg')
    self._run_remote('sudo apt-get install portaudio19-dev')
    self._run_remote('sudo apt install redis-server')
    '''


  def push_to_remote(self, file):
    self._run_remote(f'mkdir -p {config.name}')
    self._push_to_remote(file, config.name)
    ''' 
    for file in [
        'sdk', 'backend', 'config.yaml'
      ]:
      print(f'push {file}.....')
      self._push_to_remote(file, config.name)
    '''

  def login(self):
    #sshpass -p 'x#XdZa4;z2UJ_' ssh ubuntu@101.43.17.243
    cmd = f'sshpass -p "{config.network.ssh.passwd}" ssh {self.ssh_url}'
    os.system(cmd)

  _env = 'PYTHONPATH=./sdk:../sdk/:../:./:$PYTHONPATH/'
  def run_backend(self):
    self._run_remote(f'lsof -ti :{config.network.backend_port} | xargs kill')
    self._run_remote(f"nohup bash -c 'cd {config.name} && {self._env} /usr/bin/python backend ' > out.txt 2>error.txt &")
    #self._run_remote(f"cd {config.name} && {self._env} /usr/bin/python backend ")

  def run_frps(self):
    self.push_to_remote('./tmp/frps.toml')
    self._run_remote(f'cd {config.name} && PATH=./sdk/bin:$PATH frps -c frps.toml')

  def run_frpc(self):
    cmd = f'./sdk/bin/frpc -c ./tmp/frpc.toml'
    os.system(cmd)

  def print_log(self):
    self._run_remote(f'cd {config.name} && cat out.txt error.txt')

  def test(self):
    self._run_remote('cat out.txt')
