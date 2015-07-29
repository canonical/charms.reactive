import re
import argparse
import sphinx.ext.autodoc


def is_cli(obj):
    return hasattr(obj, '_subcommand_args') or hasattr(obj, '_subcommand_argsets')


class CLIDoc(sphinx.ext.autodoc.FunctionDocumenter):
    """
    Automatically generate documentation for CLI entry-points.
    """

    def _get_usage(self):
        """
        Build usage string from argparser args.
        """
        parser = argparse.ArgumentParser()
        parser.prog = 'juju-resources {}'.format(self.object_name)
        for set_name, set_args in getattr(self.object, '_subcommand_argsets', {}).items():
            for ap_args, ap_kwargs in set_args:
                parser.add_argument(*ap_args, **ap_kwargs)
        for ap_args, ap_kwargs in getattr(self.object, '_subcommand_args', []):
            parser.add_argument(*ap_args, **ap_kwargs)
        usage = parser.format_usage()
        usage = re.sub(r'\n *', ' ', usage)
        return usage.strip()

    def add_content(self, more_content, no_docstring=False):
        if is_cli(self.object):
            # add usage
            self.add_line('**%s**' % self._get_usage(), '<clidoc>')
            self.add_line('', '<clidoc>')

        # add description
        super(CLIDoc, self).add_content(more_content, no_docstring)

        if is_cli(self.object):
            # add parameter docs
            sourcename = u'args of %s' % self.fullname
            lines = []
            for set_name, set_args in getattr(self.object, '_subcommand_argsets', {}).items():
                for ap_args, ap_kwargs in set_args:
                    lines.append(':param {}: {}'.format(' '.join(ap_args), ap_kwargs.get['help']))
            for ap_args, ap_kwargs in getattr(self.object, '_subcommand_args', []):
                lines.append(':param {}: {}'.format(' '.join(ap_args), ap_kwargs['help']))
            for i, line in enumerate(lines):
                self.add_line(line, sourcename, i)


def filter_cli(app, what, name, obj, skip, options):
    if type(obj).__name__ == 'function' and obj.__module__ == 'jujuresources.cli':
        return not is_cli(obj)
    return skip


def setup(app):
    app.add_autodocumenter(CLIDoc)
    app.connect('autodoc-skip-member', filter_cli)
