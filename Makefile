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
	find . -name '*.pyc' -or -name '__pycache__' -delete
	rm -rf dist/*
	rm -rf .tox
	(which dh_clean && dh_clean) || true

userinstall:
	scripts/update-revno
	python setup.py install --user

lint:
	tox -e lint2,lint3

lint2:
	tox -e lint2

test:
	tox

test2:
	tox -e py2

test3:
	tox -e py3

ftest: lint
	@echo Starting fast tests...
	.tox/py2/bin/nosetests --attr '!slow' --nologcapture tests/
	.tox/py3/bin/nosetests --attr '!slow' --nologcapture tests/

docs: lint2
	.tox/py2/bin/pip install sphinx
	(cd docs; make html SPHINXBUILD=../.tox/py2/bin/sphinx-build)
.PHONY: docs

release: test docs
	$(PYTHON) setup.py sdist upload upload_sphinx
