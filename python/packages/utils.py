import os
import shutil
import logging
Log = logging.getLogger()

class Utils(object):
    @staticmethod
    def clean_directory(directory):
        files = os.listdir(directory)
        for f in files:
            file = os.path.join(directory, f)
            Log.info("Deleting {0}".format(file))
            if os.path.isfile(file):
                os.remove(file)
            elif os.path.isdir(file):
                shutil.rmtree(os.path.join(directory, f))
            else:
                raise RuntimeError("Impossible to delete unspported format : {0}".format(file))


def vaargCallback(option, opt_str, value, parser):
    assert value is None
    value = []
    def floatable(str):
        try:
            float(str)
            return True
        except ValueError:
            return False

    for arg in parser.rargs:
        # stop on --foo like options
        if arg[:2] == "--" and len(arg) > 2:
            break
        # stop on -a, but not on -3 or -3.0
        if arg[:1] == "-" and len(arg) > 1 and not floatable(arg):
            break
        value.append(arg)

    del parser.rargs[:len(value)]
    setattr(parser.values, option.dest, value)
