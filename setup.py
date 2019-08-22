from setuptools import setup
import os


version_file = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            'VERSION'))
with open(version_file) as v:
    VERSION = v.read().strip()


SETUP = {
    'name': "charms.reactive",
    'version': VERSION,
    'author': "Charm Reactive Framework Maintainers",
    'author_email': "juju@lists.ubuntu.com",
    'url': "https://github.com/juju-solutions/charms.reactive",
    'packages': [
        "charms",
        "charms.reactive",
        "charms.reactive.patterns",
    ],
    'install_requires': [
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

try:
    from sphinx_pypi_upload import UploadDoc
    SETUP['cmdclass'] = {'upload_sphinx': UploadDoc}
except ImportError:
    pass

if __name__ == '__main__':
    setup(**SETUP)
