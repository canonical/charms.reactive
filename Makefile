PROJECT=charms
PYTHON := .tox/py3/bin/python
SUITE=unstable
TESTS=tests/
VERSION=$(shell cat VERSION)

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
	tox -e lint

test:
	tox -e py3

ftest: lint
	@echo Starting fast Python 3 tests...
	.tox/py3/bin/nosetests --attr '!slow' --nologcapture tests/

docs: lint
	.tox/py3/bin/pip install sphinx
	(cd docs; make html SPHINXBUILD=../.tox/py3/bin/sphinx-build)
.PHONY: docs

release: test docs
	git remote | xargs -L1 git fetch --tags
	$(PYTHON) setup.py sdist register upload upload_sphinx
	git tag release-${VERSION}
	git remote | xargs -L1 git push --tags

docrelease: ftest docs
	$(PYTHON) setup.py sdist register upload_sphinx
