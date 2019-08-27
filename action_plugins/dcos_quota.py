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
from action_plugins.common import (
    ensure_dcos,
    run_command,
    _dcos_path
)

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()

def get_quota_state(gid):
    """Get the current state of a quota."""

    r = subprocess.check_output([
        'dcos',
        'quota',
        'list',
        '--json'
        ],
        env=_dcos_path()
    )
    quotas = json.loads(r)

    display.vvv('looking for gid {}'.format(gid))

    state = 'absent'
    for q in quotas:
        try:
            if gid == q['role']:
                state = 'present'
                display.vvv('found pool: {}'.format(gid))

        except KeyError:
            continue
    return state

def quota_create(gid, cpu, mem, disk, gpu):
    """Create a quota"""
    display.vvv("DC/OS: create quota {}".format(gid))

    cmd = [
        'dcos',
        'quota',
        'create',
        gid,
    ]

    if cpu is not None:
        cmd.extend([ '--cpu', str(cpu)])
    if mem is not None:
        cmd.extend([ '--mem', str(mem)])
    if disk is not None:
        cmd.extend([ '--disk', str(disk)])
    if gpu is not None:
        cmd.extend([ '--gpu', str(gpu)])

    run_command(cmd, 'create quota', stop_on_error=True)

def quota_update(gid, cpu, mem, disk, gpu):
    """Update quota permissions"""
    display.vvv("DC/OS: update quota {}".format(gid))

    cmd = [
        'dcos',
        'quota',
        'update',
        gid,
    ]

    if cpu is not None:
        cmd.extend([ '--cpu', str(cpu)])
    if mem is not None:
        cmd.extend([ '--mem', str(mem)])
    if disk is not None:
        cmd.extend([ '--disk', str(disk)])
    if gpu is not None:
        cmd.extend([ '--gpu', str(gpu)])

    run_command(cmd, 'update quota', stop_on_error=True)

def quota_delete(gid):
    """Delete a quota"""
    display.vvv("DC/OS: delete quota {}".format(gid))

    cmd = [
        'dcos',
        'quota',
        'delete',
        gid,
    ]
    run_command(cmd, 'delete quota', stop_on_error=True)

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
        gid = args.get('group_id')
        cpu = args.get('cpu', None)
        mem = args.get('mem', None)
        disk = args.get('disk', None)
        gpu = args.get('gpu', None)

        wanted_state = args.get('state', 'present')

        if gid is None:
            raise AnsibleActionFail('gid cannot be empty for dcos_iam_quota')

        ensure_dcos()

        current_state = get_quota_state(gid)

        if current_state == wanted_state:
            
            display.vvv(
                "DC/OS quota {} already in desired state {}".format(gid, wanted_state))

            if wanted_state == "present":
                quota_update(gid, cpu, mem, disk, gpu)

            result['changed'] = False
        else:
            display.vvv("DC/OS: quota {} not in desired state {}".format(gid, wanted_state))

            if wanted_state != 'absent':
                quota_create(gid, cpu, mem, disk, gpu)

            else:
                quota_delete(gid)

            result['changed'] = True

        return result
