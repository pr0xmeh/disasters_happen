import os, sys, json
from math import floor
from time import strftime

from Disasterous.console  import Console
from Disasterous.fs       import File
from Disasterous.services import Dropbox
from Disasterous.config   import Config
from Disasterous.paths    import fp_json
from Disasterous.jsondb   import Jsondb

import dropbox

class MyApp:
    def __init__(self):
        # Init self.
        self.config = Config()
        if self.config.verbosity:
            self.term = Console()

        # Init API service.
        self.service = self.init_service()

        # Be polite.
        if self.config.verbosity:
            msg = 'Welcome!\nLogged in to {service}...\n'.format(service=self.config.service)
            self.term.secho(msg)

        # Init database.
        self.branch_json = Jsondb(fp=fp_json['branches'])
        self.branch_store = self.branch_json.store

        # Populate.
        self.remote_files = self.get_remote_files()
        self.get_local_files(db_obj = self.branch_store)

        # Backup!
        self.push()

    def init_service(self):
        s = None
        name = self.config.service
        if name == 'Dropbox':
            s = Dropbox()
        else: #Default to Dropbox
            s = Dropbox()
        return s.service

    def push(self):
        # Init.
        file_mode = dropbox.files.WriteMode('overwrite')
        local_branch  = self.branch_store['local']
        remote_branch = self.branch_store['remote'] 

        # Iterate through packages.
        for package_name in local_branch:
            # Get package.
            package = local_branch[package_name]

            # Create remote package if not exists.
            if package_name not in remote_branch:
                remote_branch[package_name] = {}

            # Iterate files.
            for file_key in package['files']:
                # Path must end in / for path-joining.
                discovery_path = os.path.expanduser(package['dir']) + '/'

                # ...
                if file_key[0] == '/':
                    file_name = file_key[1:]
                else:
                    file_name = file_key

                # Paths.
                local_path  = os.path.join(discovery_path, file_name)
                remote_path = '/{package}/{file}'.format(package = package_name,
                    file = file_name
                )

                # Compare checksums.
                upload = False
                local_checksum = package['files'][file_key]['checksum']
                if file_key not in remote_branch[package_name]:
                    remote_branch[package_name][file_key] = {}
                    remote_branch[package_name][file_key]['checksum'] = local_checksum
                    upload = True
                else:
                    if local_checksum != remote_branch[package_name][file_key]['checksum']:
                        remote_branch[package_name][file_key]['checksum'] = local_checksum
                        upload = True

                # Do upload?
                if upload:
                    # File obj
                    local_file = File(fp=local_path)

                    # Verbosity.
                    if self.config.verbosity:
                        msg_args = {
                            'local_path': local_file.echoable(),
                            'remote_path': remote_path,
                            'time': strftime('%I:%M'),
                            'est': self.term.est_upload_time(local_file.size() / (500 * 1024))
                        }
                        self.term.echo(args=msg_args)

                    # Do.
                    if self.upload_file(remote_path = remote_path, local_path = local_path):
                        if not self.config.development:
                            self.branch_json.save()
                        

    def upload_file(self, local_path, remote_path):
        # Uploader.
        file_obj = File(fp=local_path)
        uploader = self.service.get_chunked_uploader(file_obj.obj(), length = file_obj.size())
        while uploader.offset < file_obj.size():
            try:
                upload = uploader.upload_chunked(chunk_size=self.config.chunks)
            except:
                print(sys.exc_info()[0], sys.exc_info()[2].tb_lineno)
                return False
                # perform error handling and retry logic
        uploader.finish(path = remote_path, overwrite = True)
        return True

    def get_local_files(self, db_obj):
        # Init.
        local_files = []
        branch = db_obj['local']
        packages = [key for key in branch]
        
        # Iterate packages.
        for package_name in packages:
            # Get package. 
            package = branch[package_name]
            
            # Is discoverable mode?
            if package['discoverable']:
                discovery_path = os.path.expanduser(package['dir'])

                # Iterate files and directories.
                for dirpath, dirnames, filenames in os.walk(discovery_path):
                    sub_package_name = dirpath.replace(discovery_path, '')
                    if sub_package_name.__len__() == 0:
                        sub_package_name = None

                    # Iterate files.
                    for file_name in filenames:
                        file_obj = File(discovery_path)
                        if sub_package_name:
                            # Init.
                            file_key = '{sub_package}/{file_name}'.format(
                                sub_package=sub_package_name, 
                                file_name=file_name
                            )
                            file_obj.join([sub_package_name, file_name])
                            if not file_obj.exists():
                                print(file_obj)
                                sys.exit()
                        else:
                            file_key = file_name
                            file_obj.join(file_key)

                        # Discovery should be bi-directional.
                        checksum = file_obj.checksum()
                        if file_key in package:
                            # Compare checksums.
                            if package['files'][file_key]['checksum'] != checksum:
                                package['files'][file_key]['checksum'] = checksum
                        else:
                            # Insert.
                            package['files'][file_key] = {
                                'checksum': checksum
                            }
            
            # Not discoverabe, probably secret.
            else:
                for file_key in package['files']:
                    file_obj = File(fp=package['dir'])
                    file_obj.join(file_key)                    
                    checksum = file_obj.checksum()
                    package['files'][file_key]['checksum'] = checksum

            # Update branch.
            branch[package_name] = package

        return branch

    def get_remote_files(self):
        #return [entry for entry in self.service.files_list_folder('').entries]
        return None

def main():
    x = MyApp()
    
if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        sys.exit('\nGoodbye!')