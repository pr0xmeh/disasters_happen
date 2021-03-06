import os.path, sys
from hashlib import md5

from Disasterous.paths  import fp_json, fp_branches
from Disasterous.jsondb import Jsondb

class SyncFS:
    def __init__(self, service):
        self.service = service
        print(service)

    def push(self):
        pass

    def pull(self):
        pass

    def file_mode(self):
        # 1. Check if last know file-location exists.
        # ...

        # 2. If so, see if the data has changed. (diff)
        # ...

        # 3. If not, see if the same data is anywhere else. (mv)
        # ...

        # 4. Otherwise, mark the file as removed. (rm)
        # ...


class LocalFS:
    def __init__(self, config):
        # Config.
        self.config = config

        # Branch.
        self.branch_json = Jsondb(fp=fp_branches[self.config.branch])
        self.branch_store = self.branch_json.store

        # File tracking.
        self.track_json  = Jsondb(fp=fp_json['tracking'])
        self.track_store = self.track_json.store
        self.track_files()

        # Update persistent-storage.
        self.branch_json.save()

    def track_files(self):
        for package_name in self.track_store:
            package = self.track_store[package_name]
            package_file = File(package['dir'])
            package_top_dir = package_file.path

            # Make a list of potential files.
            package_files = []
            if package['discoverable']:
                for dirpath, dirnames, filenames in os.walk(package_top_dir):
                    package_dir = dirpath.replace(package_top_dir, '')
                    for file_name in filenames:
                        if package_dir.__len__() != 0:
                            package_file.join([package_dir, file_name])
                        else:
                            package_file.join(file_name)
                        package_files.append(package_file.last_path)
            else:
                for file_name in package_file['files']:
                    package_file.join([package_name, file_name])
                    package_files.append(package_file.last_path)
                
            # Compare to ignored names.
            for file_name in package_files:
                track = True
                for ignore_key in self.config.ignore:
                    if ignore_key in file_name:
                        track = False
                if track:
                    file_obj = File(file_name)
                    self.branch_store[file_obj.last_path] = file_obj.json()

class File:
    def __init__(self, fp):
        self.path = os.path.expanduser(fp)
        self.last_path = self.path

    def __repr__(self):
        return '<File {path}>'.format(path=self.path)

    def json(self):
        ''' Returns a Json representation of the file obj '''
        return {
            'checksum': self.checksum(),
            'size': self.size()
        }

    def obj(self, mode='rb'):
        return open(self.path, mode)

    def join(self, path):
        '''
        https://docs.python.org/3/library/os.path.html#os.path.join

        If a component is an absolute path, all previous components are 
        thrown away and joining continues from the absolute path component.
        '''

        if type(path) is str:
            self.last_path = os.path.join(self.path, path)
        elif type(path) is list:
            path = [x[1:] if x[0] is '/' else x for x in path]
            self.last_path = os.path.join(self.path, *path)
        return self.last_path

    def checksum(self):
        try:
            with open(self.last_path, 'rb') as f:
                return md5(f.read()).hexdigest()
        except: # File does not exist yet.
            return ""

    def exists(self):
        return os.path.isfile(self.last_path)

    def size(self):
        return os.path.getsize(self.last_path)

    def echoable(self):
        return self.path.replace(os.last_path.expanduser('~/'), '')