import re
import argparse
import sphinx.ext.autodoc
from charmhelpers.cli import describe_arguments


class CLIDoc(sphinx.ext.autodoc.FunctionDocumenter):
    """
    Automatically generate documentation for CLI entry-points.
    """

    def generate(self, more_content=None, real_modname=None,
                 check_module=False, all_members=False):
        if not self.parse_name():
            # need a module to import
            self.directive.warn(
                'don\'t know which module to import for autodocumenting '
                '%r (try placing a "module" or "currentmodule" directive '
                'in the document, or giving an explicit module name)'
                % self.name)
            return

        # now, import the module and get object to document
        if not self.import_object():
            return

        if not (type(self.object).__name__ == 'function' and
                self.object.__module__ == 'charms.reactive.cli'):
            return super(CLIDoc, self).generate(more_content, real_modname, check_module, all_members)

        parser = argparse.ArgumentParser()
        parser.prog = 'charms.reactive {}'.format(self.object_name)
        for args, kwargs in describe_arguments(self.object):
            parser.add_argument(*args, **kwargs)

        usage = parser.format_usage()
        usage = re.sub('usage: (\S+) (\S+) (.*)', r'\1 **\2** `\3`', usage)
        self.add_line(usage, '<clidoc>')
        self.add_line('', '<clidoc>')
        self.indent += '    '
        self.add_content(more_content)


def setup(app):
    app.add_autodocumenter(CLIDoc)
