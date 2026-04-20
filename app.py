import os

NAME_DEFAULT = ''
ORDER_DEFAULT = 0
TIMEOUT_DEFAULT = 300
LAUNCH_DEFUALT = None
MACROS_DEFAULT = []

class App:
    def __init__(self, appdata):
        self.name    = appdata.get('name',    NAME_DEFAULT)
        self.order   = appdata.get('order',   ORDER_DEFAULT)
        self.launch  = appdata.get('launch',  LAUNCH_DEFUALT)
        self.timeout = appdata.get('timeout', TIMEOUT_DEFAULT)
        self.macros  = appdata.get('macros',  MACROS_DEFAULT)

    @staticmethod
    def load_all(dir):
        apps = []

        try:
            files = os.listdir(dir)
        except OSError as err:
            print(err)
            return apps

        for filename in files:
            if filename.endswith('.py'):
                try:
                    module = __import__(dir + '/' + filename[:-3])
                    apps.append(App(module.app))
                except (SyntaxError, ImportError, AttributeError, KeyError, NameError, IndexError, TypeError) as err:
                    print("Macro Error: ", err)
                    pass

        apps.sort(key=lambda m:m.order)
        return apps
