# Hacking on charms.reactive

## Run testsuite

    # Run the linter check
    make lint
    # Run the tests
    make test

Run `make` without arguments for more options.

## Test it in a charm

Use following instructions to build a charm that uses your own development branch of
charms.reactive.

Step 1: Make sure your version of charms.reactive is recognised as the latest version by
by appending `dev0` to the version number in the `VERSION` file.

Step 2: Create an override file `override-wheelhouse.txt` that points to your own
charms.reactive branch. *The format of this file is the same as pip's
[`requirements.txt`](https://pip.pypa.io/en/stable/reference/pip_install/#requirements-file-format)
file.*

    # Override charms.reactive by the version found in folder
    -e git+file:///path/to/charms.reactive#egg=charms.reactive
    # Or point it to a github repo with
    -e git+https://github.com/<myuser>/charms.reactive#egg=charms.reactive

Step 3: Build the charm specifying the override file. *You might need to install the
candidate channel of the charm snap*

    charm build <mycharm> -w wheelhouse-overrides.txt

Now when you deploy your charm, it will use your own branch of charms.reactive.

*Note: If you want to verify this or change the charms.reactive code on a built
charm, get the path of the installed charms.reactive by running following command.*

    python3 -c "import charms.reactive; print(charms.reactive.__file__)"

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
xdg-open docs/_build/html/index.html
```


# PyPI Package and Docs

The published package and docs currently live at:

    https://pypi.python.org/pypi/charms.reactive
    https://charmsreactive.readthedocs.io/en/latest/
