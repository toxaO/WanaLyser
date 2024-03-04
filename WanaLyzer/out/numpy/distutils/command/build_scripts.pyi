from _typeshed import Incomplete
from distutils.command.build_scripts import build_scripts as old_build_scripts
from numpy.distutils import log as log
from numpy.distutils.misc_util import is_string as is_string

class build_scripts(old_build_scripts):
    def generate_scripts(self, scripts): ...
    scripts: Incomplete
    def run(self): ...
    def get_source_files(self): ...
