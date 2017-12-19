import gnupg
import os
import re
from app.exceptions.base_exceptions import DefaultException
from cfoundation import Service
from os import path
from pydash import _
from shutil import copyfile

gpg = gnupg.GPG(homedir=path.join(path.expanduser('~'), '.gnupg'))

class GpgService(Service):

    def create_key(self, name, comment, passphrase, email):
        s = self.app.services
        s.task_service.started('create_key')
        keys = gpg.list_keys()
        key_exists = False
        for key in keys:
            if (name + ' <' + email + '>') == _.keys(key['sigs'])[0]:
                key_exists = True
        if not key_exists:
            input_data = gpg.gen_key_input(
                key_type='RSA',
                key_length=1024,
                subkey_type='ELG-E',
                subkey_length=2048,
                name_real=name,
                name_email=email,
                expire_date=0,
                passphrase=passphrase
            )
            key = gpg.gen_key(input_data)
        s.task_service.finished('create_key')

    def generate_keyfile(self, name, comment, passphrase, email, workdir):
        s = self.app.services
        s.task_service.started('generate_keyfile')
        filesystem_path = path.join(workdir, 'filesystem')
        keyring = os.popen('find * -maxdepth 1 -name "ubuntu-keyring*" -type d -print').read().split('\n')[0]
        if len(keyring) <= 0:
            os.system('apt-get source ubuntu-keyring')
            keyring = os.popen('find * -maxdepth 1 -name "ubuntu-keyring*" -type d -print').read().split('\n')[0]
            if len(keyring) <= 0:
                raise DefaultException('Cannot grab keyring source')
        keyid = self.get_key_id(name, email)
        os.chdir(path.join(keyring, 'keyrings'))
        if not path.exists('ubuntu-archive-keyring-original.gpg'):
            os.rename('ubuntu-archive-keyring.gpg', 'ubuntu-archive-keyring-original.gpg')
        with open('ubuntu-archive-keyring-original.gpg', 'r') as f:
            gpg.import_keys(f.read())
        keyids = ['FBB75451', '437D05B5', 'C0B21F32', 'EFE21092', keyid]
        keydata_public = gpg.export_keys(keyids)
        keydata_private = gpg.export_keys(keyids, True)
        with open('ubuntu-archive-keyring.gpg', 'w') as f:
            f.write(keydata_public)
            f.write(keydata_private)
            f.close()
        os.chdir(path.abspath('..'))
        os.system('dpkg-buildpackage -rfakeroot -m"' + keyid + '" -k"' + keyid + '"')
        keyfile = path.join(os.getcwd(), 'keyrings', 'ubuntu-archive-keyring.gpg')
        os.system('sudo cp ' + keyfile + ' ' + path.join(filesystem_path, '/etc/apt/trusted.gpg'))
        os.system('sudo cp ' + keyfile + ' ' + path.join(filesystem_path, '/usr/share/keyrings/ubuntu-archive-keyring.gpg'))
        os.system('sudo cp ' + keyfile + ' ' + path.join(filesystem_path, '/var/lib/apt/keyrings/ubuntu-archive-keyring.gpg'))
        s.task_service.finished('generate_keyfile')

    def get_key_id(self, name, email):
        result = os.popen('gpg --list-keys ' + name).read()
        match = re.search('(pub\s+[^\/]+\/)([^\s]+)', result)
        return match.group(2)
