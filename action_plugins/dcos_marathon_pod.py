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

def get_pod_state(pod_id):
    """Get the current state of an pod."""
    r = subprocess.check_output(['dcos', 'marathon', 'pod', 'list', '--json' ], env=_dcos_path())
    pods = json.loads(r)

    display.vvv('looking for pod_id {}'.format(pod_id))

    state = 'absent'
    for a in pods:
        try:
            if pod_id in a['id']:
                state = 'present'
                display.vvv('found pod: {}'.format(pod_id))

        except KeyError:
         continue
    return state

def pod_create(pod_id, options):
    """Deploy an pod via Marathon"""
    display.vvv("DC/OS: Marathon create pod {}".format(pod_id))

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
            'pod',
            'add',
            f.name
        ]
        run_command(cmd, 'add pod', stop_on_error=True)


def pod_update(pod_id, options):
    """Update an pod via Marathon"""
    display.vvv("DC/OS: Marathon update pod {}".format(pod_id))

    # create a temporary file for the options json file
    with tempfile.NamedTemporaryFile('w+') as f:
        json.dump(options, f)

        # force write the file to disk to make sure subcommand can read it
        f.flush()
        os.fsync(f)

        cmd = [
            'dcos',
            'marathon',
            'pod',
            'update',
            '--force',
            pod_id
        ]

        from subprocess import Popen, PIPE

        p = Popen(cmd, env=_dcos_path(), stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate(json.dumps(options))

        display.vvv("stdout {}".format(stdout))
        display.vvv("stderr {}".format(stderr))

def pod_remove(pod_id):
    """Remove an pod via Marathon"""
    display.vvv("DC/OS: Marathon remove pod {}".format(pod_id))

    cmd = [
        'dcos',
        'marathon',
        'pod',
        'remove',
        '/' + pod_id,
    ]
    run_command(cmd, 'remove pod', stop_on_error=True)

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

        # ensure pod_id has a single leading forward slash
        pod_id = '/' + args.get('pod_id', '').strip('/')

        options = args.get('options') or {}
        options['id']= pod_id

        ensure_dcos()

        current_state = get_pod_state(pod_id)
        wanted_state = state

        if current_state == wanted_state:
            
            display.vvv(
                "Marathon pod {} already in desired state {}".format(pod_id, wanted_state))

            if wanted_state == "present":
                pod_update(pod_id, options)

            result['changed'] = False
        else:
            display.vvv("Marathon pod {} not in desired state {}".format(pod_id, wanted_state))

            if wanted_state != 'absent':
                pod_create(pod_id, options)
            else:
                pod_remove(pod_id)

            result['changed'] = True

        return result
