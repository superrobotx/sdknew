import os

class Docker:
  @classmethod 
  def get_container_id_by_name(self, name):
    cmd = f'docker ps -aqf "name={name}"'
    return os.popen(cmd).read().strip()


  def __init__(self) -> None:
    pass

  def login(self, container_name):
    container_id = Docker.get_container_id_by_name(container_name)
    if not container_id:
      print(f'Container {container_name} not found')
      return
    os.system(f'docker exec -it {container_id} /bin/bash')