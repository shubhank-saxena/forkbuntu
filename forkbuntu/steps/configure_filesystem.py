from ..step import Step
from munch import munchify
from os import path

class ConfigureFilesystem(Step):
    messages = munchify({
        'past': 'configured filesystem',
        'present': 'configuring filesystem',
        'cache': 'using configured filesystem cache'
    })
    requires = [
        'create_extras'
    ]

    def __init__(self, name, app):
        super().__init__(name, app)
        c = app.conf
        self.checksum_paths = [path.join(c.paths.iso)]

    def run(self):
        s = self.app.services
        s.configure.filesystem()