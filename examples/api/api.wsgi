# activate_this = '/home/travis/virtualenv/python2.7.14/bin/activate_this.py'
# execfile(activate_this, dict(__file__=activate_this))
import sys
sys.path.insert(0, '/path/to/vctools')
from api_main import vctools_api as application
