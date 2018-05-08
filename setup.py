import os
from setuptools import setup

import codenerix_pos_client

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-codenerix-pos-client',
    version=codenerix_pos_client.__version__,
    scripts=['codenerix_pos_client/posclient.py'],
    include_package_data=True,
    zip_safe=False,
    license='Apache License Version 2.0',
    description='Codenerix POS Client enables the system to work with codenerix_pos_client command line tool so it can connecto to CODENERIX POS server.',
    long_description=README,
    url='https://github.com/codenerix/django-codenerix-pos-client',
    author=", ".join(codenerix_pos_client.__authors__),
    keywords=['django', 'codenerix', 'management', 'erp', 'pos', 'client'],
    platforms=['OS Independent'],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    install_requires=[
        'ws4py',
        'pyscard',
        'python-escpos',
        'pyserial',
        'pyusb',
        'django-channels',
        'tornado',
        'pycryptodomex',
        'colorama',
    ]
)
