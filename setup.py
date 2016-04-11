from setuptools import setup
from sphinx_pypi_upload import UploadDoc
import os


version_file = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            'VERSION'))
with open(version_file) as v:
    VERSION = v.read().strip()


SETUP = {
    'name': "charms.reactive",
    'version': VERSION,
    'author': "Ubuntu Developers",
    'author_email': "ubuntu-devel-discuss@lists.ubuntu.com",
    'url': "https://github.com/juju-solutions/charms.reactive",
    'cmdclass': {
        'upload_sphinx': UploadDoc,
    },
    'packages': [
        "charms",
        "charms.reactive",
    ],
    'install_requires': [
        'six',
        'pyaml',
        'charmhelpers>=0.5.0',
    ],
    'scripts': [
        "bin/charms.reactive",
        "bin/charms.reactive.sh",
    ],
    'license': "Apache License 2.0",
    'long_description': open('README.rst').read(),
    'description': 'Framework for writing reactive-style Juju Charms',
}


if __name__ == '__main__':
    setup(**SETUP)
