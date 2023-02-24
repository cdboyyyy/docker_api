import docker
import os
import platform
import shlex
import json
import yaml

class docker_connect:
    def __init__(self):
        self.client_env = docker.from_env()
        try:
            self.client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        except:
            self.client = docker.DockerClient()
        
    def check_platform(self):
        if platform.system() == 'Windows':
            self.seperator = '\\'
        elif platform.system() == 'Linux':
            self.seperator = '/'
        return self.seperator  

    def read_env_file(self, location):
        env = {}
        with open(location, 'r') as file:
            env_data = file.read()
        env_lines = env_data.split('\n')
        env_lines = [line for line in env_lines if line]
        env_dict = {line.split('=')[0]: line.split('=')[1] for line in env_lines}
        return env_dict

    def get_all_containers_objects(self):
        return self.client.containers.list('all')
    
    def get_container_id_by_object(self,container):
        return container.id
    
    def get_container_id_by_name(self,container):
        return self.get_container_object(container).attrs['Id']
    
    def get_container_name(self, container_object):
        return container_object.name
    
    def get_all_containers_names(self):
        list = []
        for container in self.get_all_containers_objects():
            list.append(self.get_container_name(container))
        return list
       
    def get_container_object(self, container_name):
        try:
            return self.client.containers.get(container_name)
        except:
            return 'NotFound'

    def get_container_attributes(self, container):
        return self.get_container_object(container).attrs

    def get_container_network(self,container):
        return self.get_container_attributes(container)['NetworkSettings']
    
    def get_container_ip(self, container):
        return self.get_container_attributes(container)['NetworkSettings']['IPAddress']

    def get_container_gateway(self, container):
        return self.get_container_attributes(container)['NetworkSettings']['Gateway']
    
    def get_container_mac(self, container):
        return self.get_container_attributes(container)['NetworkSettings']['MacAddress']

    def get_container_volumes(self, container):
        return self.get_container_attributes(container)['HostConfig']['Binds']

    def get_container_platform(self, container):
        return self.get_container_attributes(container)['Platform']
    
    def get_container_image_id(self, container):
        return self.get_container_attributes(container)['Image']
    
    def get_container_image_name(self, container):
        return self.get_container_attributes(container)['Config']['Image']
    
    def get_container_hostname(self, container):
        return self.get_container_attributes(container)['Config']['Hostname']

    def get_container_status(self, container):
        try:
            return self.get_container_object(container).status
        except:
            return self.get_container_object(container)
        
    def get_image_id_by_name(self, image_name):
        for image_id in self.get_all_image_ids():
            name = self.get_image_name_by_id(image_id)
            if name.split(':')[0] == image_name:
                return image_id
        return 'NotFound'
 
    def stop_container(self, container):
        self.get_container_object(container).stop()
   
    def start_container(self, container):
        self.get_container_object(container).start()

    def remove_container(self, container):
        container_status = self.get_container_status(container)
        if container_status == 'running':
            self.stop_container(container)
            self.get_container_object(container).remove()
            return 'Container Removed'
        elif container_status == 'NotFound':
            return 'Continer was not found'
        else: 
            self.get_container_object(container).remove()

    def remove_none_running_containers(self):
        for container in self.get_all_containers_objects():
            container_name = self.get_container_name(container)
            if self.get_container_status(container_name) == 'exited':
                self.remove_container(container_name)
            if self.get_container_status(container_name) == 'created':
                self.remove_container(container_name)

    def run(self,json_data):
        data = json_data
        try:
            image = data['image']
        except:
            image = ''
        try:
            container_name = data['container_name']
        except:
            container_name = data['image']
        try:
            hostname = data['hostname']
        except:
            hostname = container_name
        try:
            env = data['env_file']
        except:
            env = {}
        try:
            vol = data['volumes']
        except:
            vol = {}
        try:
            port = data['ports']
        except:
            port = {}
        try:
            cmd = data['command']
        except:
            cmd = ''
        try:
            ram = data['mem_limit']
        except:
            ram = ''
        try:
            detach = data['detach']
        except:
            detach = True
        try:
            container = self.client.containers.run(
                image,
                name=container_name,
                detach=detach,
                hostname=hostname,
                environment=env,
                volumes=vol,
                ports=port,
                command=cmd,
                mem_limit=ram            
            )
            return container
        except:
            # for conTainer in self.get_all_containers_objects():
            #     print(self.get_container_hostname(conTainer))
            return 'container was already up'
    
    def compose_to_json(self, container_name,compose_file_yml):
        dummy_json = {}
        with open(compose_file_yml) as f:
            try:
                data=yaml.safe_load(f)
            except yaml.YAMLError as exc:
                print(exc)
        data = data['services'][container_name]
        
        for object in data:
            if object == 'env_file':
                for file in data[object]:
                    env = self.read_env_file(file)
                    for var in env:
                        dummy_json[var] = env[var]
                data['env_file'] = dummy_json
                        
            if object == 'ports':
                ports = {}
                portlist = data[object]
                for port in portlist:
                    key, value = port.split(':')
                    d = {}
                    d[value] = key
                    ports.update(d)
                data['ports'] = ports
                
            if object == 'volumes':
                vol_list = []
                for vol in data[object]:
                    if vol.rfind(self.check_platform()) != -1:
                        vol_list.append(vol)
                data['volumes'] = vol_list      
        return data
          
    def build(self,json_data,cache=True):
        '''
        building image function need to get service name and 
        compose file location
        '''
        # data = self.compose_to_json(container_name,compose_file)
        data = json_data
        try:
            # location = data['location']
            location = data['build']['context']
            # print(location)
        except:
            location = '.'
        try:
            # Dockerfile = data['dockerfile_name']
            dockerfile = data['build']['dockerfile']
            # print(dockerfile)
        except:
            dockerfile = 'Dockerfile'
        try:
            image_name = data['image']
            # print(image_name)
        except:
            image_name = 'unnamed'
            # print(image_name)
        print(self.client_env.images.build(
            path=location, 
            dockerfile=dockerfile, 
            tag=image_name,
            nocache=cache
        ))
             
    def get_image_object(self, image):
        return self.client.images.get(image)
    
    def get_all_images_objects(self):
        return self.client.images.list()

    def get_object_image_id(self, image):
        return self.get_image_object(image).id

    def get_all_image_ids(self):
        list = []
        for image in self.get_all_images_objects():
            list.append(image.id)
        return list
    
    def get_image_name_by_id(self,image_id):
        try:
            return self.client_env.images.get(image_id).tags[0]
        except:
            return '<none>'
    
    def get_image_tags(self,image):
        img = self.get_image_object(image)
        return img.tags
    
    def get_image_attribute(self,image):
        return self.get_image_object(image).attrs
    
    def delete_image(self, image):
        try:
            return self.client_env.images.get(image).remove()
        except:
            for tag in self.get_image_tags(image):
                counter = len(image)+1
                format_image = f'{image}:'
                if format_image in tag[:counter]:
                    self.client_env.images.remove(tag,force=True)

    def delete_none_images(self):
        for image in self.get_all_images_objects():
            if self.get_image_name(image.id) == '<none>':
                self.delete_image(image.id)
        return 'Done'

    def pull_image(self,image):
        return self.client.images.pull(image)