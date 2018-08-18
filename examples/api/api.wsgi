## Uncomment this for virtual environments / Travis CI
# activate_this = '/path/to/bin/activate_this.py'
# with open(activate_this) as fname:
#    exec(fname.read(), dict(__file__=activate_this))
import sys
sys.path.insert(0, '/path/to/vctools')
from api_main import vctools_api as application
