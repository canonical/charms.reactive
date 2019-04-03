PROJECT=charms
BIN_DIR := .tox/py3/bin
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
	rm -rf .tox .coverage
	rm -rf dist/*
	rm .unit-state.db
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
	.tox/lint/bin/pip install -r docs/requirements.txt
	(cd docs; make html SPHINXBUILD=../.tox/lint/bin/sphinx-build)
	cd docs/_build/html && zip -r ../docs.zip *
.PHONY: docs

release: test
	$(BIN_DIR)/pip install twine
	git remote | xargs -L1 git fetch --tags
	rm -f dist/*
	$(PYTHON) setup.py sdist
	$(BIN_DIR)/twine upload dist/*
	git tag ${VERSION}
	git remote | xargs -L1 git push --tags
