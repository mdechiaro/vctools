# Examples for setting up vctools with Apache + WSGI

# Ubuntu

apache2

# Python 3.4, 3.5

libapache2-mod-wsgi

# Python 3.6+

apache2-dev

Install mod_wsgi via pip3 or pipenv and run the following commands:

mod_wsgi-express module-config >> examples/api/api.conf
sed -i "/WSGIDaemonProcess/ s,$, python-home=$VIRTUAL_ENV," examples/api/api.conf
