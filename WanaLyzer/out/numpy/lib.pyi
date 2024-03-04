from numpy._pytesttester import PytestTester as PytestTester
from numpy.lib import scimath as scimath
from numpy.version import version as version

test: PytestTester
__version__ = version
emath = scimath
