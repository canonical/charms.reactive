# Hacking on Docs

Install dependencies:

```bash
sudo apt install python3-sphinx
```

To build the html documentation:

```bash
make docs
```

To browse the html documentation locally:

```bash
make docs
cd docs/_build/html
python -m SimpleHTTPServer 8765
# point web browser to http://localhost:8765
```


# PyPI Package and Docs

The published package and docs currently live at:

    https://pypi.python.org/pypi/charms.reactive
    https://charmsreactive.readthedocs.io/en/latest/
