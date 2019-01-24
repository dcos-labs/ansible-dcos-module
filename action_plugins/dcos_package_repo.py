"""
Action plugin to configure a DC/OS cluster.
Uses the Ansible host to connect directly to DC/OS.
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import subprocess
import tempfile
import time
import os
import sys

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail

# to prevent duplicating code, make sure we can import common stuff
sys.path.append(os.getcwd())
sys.path.append(os.getcwd() + '/resources/ansible-dcos-module')
from action_plugins.common import ensure_dcos, run_command, _dcos_path

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()

def get_repo_state(name):
    """Get the current state of a repo"""

    r = subprocess.check_output([
        'dcos',
        'package',
        'repo',
        'list',
        '--json'
        ],
        env=_dcos_path()
    )
    repos = json.loads(r)['repositories']

    display.vvv('looking for repo {}'.format(name))

    state = 'absent'
    for n in repos:
        try:
            if n['name'] == name:
                state = 'present'
                display.vvv('found repo name: {}'.format(n['name']))
        except KeyError:
            continue

    return state

def repo_add(name, url, index):
    """Create a repo"""
    display.vvv("DC/OS: create repo {}".format(name))

    quotes = '\"'

    cmd = [
        'dcos',
        'package',
        'repo',
        'add',
        '--index',
        str(index),
        name,
        url,
    ]
    run_command(cmd, 'add repo', stop_on_error=True)

def repo_update(name, url, index):
    """Update a repo"""
    display.vvv("DC/OS: updating repo {}".format(
        name))

    repo_remove(name)
    while get_repo_state(name) != 'absent':
        time.sleep(1)

    repo_add(name, url, index)

def repo_remove(name):
    """Delete a repo"""
    display.vvv("DC/OS: remove repo {}".format(name))

    cmd = [
        'dcos',
        'package',
        'repo',
        'remove',
        name,
    ]
    run_command(cmd, 'remove repo', stop_on_error=True)

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        if self._play_context.check_mode:
            # in --check mode, always skip this module execution
            result['skipped'] = True
            result['msg'] = 'The dcos task does not support check mode'
            return result

        args = self._task.args
        name = args.get('name', None)
        url = args.get('url', None)
        index = args.get('index', 0)
        wanted_state = args.get('state', 'present')

        if name is None:
            raise AnsibleActionFail('name cannot be empty for dcos_package_repo')

        if url is None:
            raise AnsibleActionFail('url cannot be empty for dcos_package_repo')

        ensure_dcos()

        current_state = get_repo_state(name)

        if current_state == wanted_state:

            display.vvv(
                "DC/OS: Repo {} already in desired state".format(name))
            
            if wanted_state == "present":
                repo_update(name, url, index)

            result['changed'] = False
        else:

            display.vvv("DC/OS: Repo {} not in desired state".format(name))

            if wanted_state != 'absent':
                repo_add(name, url, index)
            else:
                repo_remove(name)

            result['changed'] = True

        return result
