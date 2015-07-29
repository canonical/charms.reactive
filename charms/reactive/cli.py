# Copyright 2014-2015 Canonical Limited.
#
# This file is part of charm-helpers.
#
# charm-helpers is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3 as
# published by the Free Software Foundation.
#
# charm-helpers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with charm-helpers.  If not, see <http://www.gnu.org/licenses/>.

from charmhelpers.cli import cmdline
from charms.reactive import helpers


@cmdline.subcommand()
@cmdline.test_command
def hook(*hook_patterns):
    """
    Check if the current hook matches one of the patterns.
    """
    return helpers._hook(hook_patterns)


@cmdline.subcommand()
@cmdline.test_command
def when(handler_id, *desired_states):
    """
    Check if all of the desired_states are active and have changed.
    """
    return helpers._when(handler_id, desired_states, False)


@cmdline.subcommand()
@cmdline.test_command
def when_not(handler_id, *desired_states):
    """
    Check if not all of the desired_states are active and have changed.
    """
    return helpers._when(handler_id, desired_states, True)


@cmdline.subcommand()
@cmdline.test_command
def when_file_changed(*filenames):
    """
    Check if files have changed since the last time they were checked.
    """
    return helpers.any_file_changed(filenames)


@cmdline.subcommand()
@cmdline.test_command
def only_once(handler_id):
    """
    Check if handler has already been run in the past.
    """
    return not helpers.was_invoked(handler_id)


@cmdline.subcommand()
@cmdline.no_output
def mark_invoked(handler_id):
    """
    Record that the handler has been invoked, for use with only_once.
    """
    helpers.mark_invoked(handler_id)
