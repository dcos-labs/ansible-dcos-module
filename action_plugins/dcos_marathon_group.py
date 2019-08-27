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

def get_group_state(group_id):
    """Get the current state of an group."""
    r = subprocess.check_output(['dcos', 'marathon', 'group', 'list', '--json' ], env=_dcos_path())
    groups = json.loads(r)

    display.vvv('looking for group_id {}'.format(group_id))

    state = 'absent'
    for a in groups:
        try:
            if group_id == a['id']:
                state = 'present'
                display.vvv('found group: {}'.format(group_id))

        except KeyError:
         continue
    return state

def group_create(group_id, options):
    """Deploy an group via Marathon"""
    display.vvv("DC/OS: Marathon create group {}".format(group_id))

    # create a temporary file for the options json file
    with tempfile.NamedTemporaryFile('w+') as f:
        json.dump(options, f)

        # force write the file to disk to make sure subcommand can read it
        f.flush()
        os.fsync(f)

        display.vvv(subprocess.check_output(
        ['cat', f.name]).decode())

        cmd = [
            'dcos',
            'marathon',
            'group',
            'add',
            f.name
        ]
        run_command(cmd, 'add group', stop_on_error=True)


def group_update(group_id, options):
    """Update an group via Marathon"""
    display.vvv("DC/OS: Marathon update group {}".format(group_id))

    # create a temporary file for the options json file
    with tempfile.NamedTemporaryFile('w+') as f:
        json.dump(options, f)

        # force write the file to disk to make sure subcommand can read it
        f.flush()
        os.fsync(f)

        cmd = [
            'dcos',
            'marathon',
            'group',
            'update',
            '--force',
            group_id
        ]

        from subprocess import Popen, PIPE

        p = Popen(cmd, env=_dcos_path(), stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate(json.dumps(options).encode())

        display.vvv("stdout {}".format(stdout))
        display.vvv("stderr {}".format(stderr))

def group_remove(group_id):
    """Remove an group via Marathon"""
    display.vvv("DC/OS: Marathon remove group {}".format(group_id))

    cmd = [
        'dcos',
        'marathon',
        'group',
        'remove',
        '/' + group_id,
    ]
    run_command(cmd, 'remove group', stop_on_error=True)

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
        state = args.get('state', 'present')

        # ensure group_id has a single leading forward slash
        group_id = '/' + args.get('group_id', '').strip('/')

        options = args.get('options') or {}
        options['id']= group_id

        ensure_dcos()

        current_state = get_group_state(group_id)
        wanted_state = state

        if current_state == wanted_state:
            
            display.vvv(
                "Marathon group {} already in desired state {}".format(group_id, wanted_state))

            if wanted_state == "present":
                group_update(group_id, options)

            result['changed'] = False
        else:
            display.vvv("Marathon group {} not in desired state {}".format(group_id, wanted_state))

            if wanted_state != 'absent':
                group_create(group_id, options)
            else:
                group_remove(group_id)

            result['changed'] = True

        return result
