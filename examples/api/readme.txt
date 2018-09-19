# Examples for setting up vctools with Apache + WSGI

# Ubuntu / RedHat

apache2 / httpd

# Python 3.4, 3.5 (Ubuntu / RedHat)

libapache2-mod-wsgi / mod_wsgi

# Python 3.6+ (Ubuntu / RedHat)

apache2-dev / httpd-devel

Install mod_wsgi via pip3 or pipenv and run the following commands:

run: pipenv shell 'mod_wsgi-express module-config; exit'

copy output to examples/api/api.conf
sed -i "/WSGIDaemonProcess/ s,$, python-home=$VIRTUAL_ENV," examples/api/api.conf
systemctl restart (apache2|httpd)
