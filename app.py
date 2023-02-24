from docker_connect import docker_connect



docker = docker_connect()

print(docker.get_all_containers_names())
docker.remove_container('unruffled_almeida')
print(docker.get_all_containers_names())