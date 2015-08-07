PROJECT=charms
PYTHON := /usr/bin/env python
SUITE=unstable
TESTS=tests/

all:
	@echo "make test - Run tests"
	@echo "make release - Build and upload package and docs to PyPI"
	@echo "make source - Create source package"
	@echo "make userinstall - Install locally"
	@echo "make docs - Build html documentation"
	@echo "make clean"

source: setup.py
	scripts/update-revno
	python setup.py sdist

docclean:
	rm -rf docs/_build

clean: docclean
	-python setup.py clean
	rm -rf build/ MANIFEST
	rm -rf .tox
	rm -rf dist/*
	find . -name '*.pyc' -or -name '__pycache__' | xargs rm -rf
	(which dh_clean && dh_clean) || true

userinstall:
	scripts/update-revno
	python setup.py install --user

lint:
	tox -e lint2,lint3

lint2:
	tox -e lint2

lint3:
	tox -e lint3

test:
	tox

test2:
	tox -e py2

test3:
	tox -e py3

ftest2: lint2
	@echo Starting fast Python 2 tests...
	.tox/py2/bin/nosetests --attr '!slow' --nologcapture tests/

ftest3: lint3
	@echo Starting fast Python 3 tests...
	.tox/py3/bin/nosetests --attr '!slow' --nologcapture tests/

ftest: ftest2 ftest3;

docs: lint2
	.tox/py2/bin/pip install sphinx
	(cd docs; make html SPHINXBUILD=../.tox/py2/bin/sphinx-build)
.PHONY: docs

release: test docs
	$(PYTHON) setup.py sdist register upload upload_sphinx

docrelease: ftest docs
	$(PYTHON) setup.py sdist register upload_sphinx
