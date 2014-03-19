import os
import ConfigParser

class Settings(object):
    def __init__(self):
        self.settings = ConfigParser.ConfigParser()

        self.path = os.environ.get('XDG_CONFIG_HOME', os.path.join(os.path.expanduser("~"), '.config', 'jenna', 'settings.ini'))

        if not os.path.exists(self.path):
            if not os.path.exists(os.path.dirname(self.path)):
                os.makedirs(os.path.dirname(self.path))

            with open(self.path, 'a') as config_file:
                config_file.write('[jenna]')

        self.settings.read(self.path)

    def get(self, key):
        return self.settings.get('jenna', key)

    def set(self, key, value):
        self.settings.set('jenna', key, value)

        with open(self.path, 'w') as config_file:
            self.settings.write(config_file)
