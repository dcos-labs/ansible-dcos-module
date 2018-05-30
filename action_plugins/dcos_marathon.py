"""
Action plugin to manipulate Marathon jobs on a DC/OS cluster.
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import time

from ansible.errors import AnsibleActionFail
from ansible.module_utils.parsing.convert_bool import boolean
from ansible.plugins.action import ActionBase

try:
    import dcos.marathon
    from dcos.errors import DCOSException
except ImportError:
    raise AnsibleActionFail("Missing package: try 'pip install dcos-python'")

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


def get_app_state(marathon, app_id):
    try:
        r = marathon.get_app(app_id)
        if r.get('tasksRunning', 0) > 0:
            return 'present'
        else:
            return 'absent'
    except DCOSException:
        return 'absent'


def wait_for_app_state(marathon,
                       app_id,
                       wanted_state='present',
                       retries=6):
    """Wait for a Marathon app to be in a desired state."""

    # exponential backoff
    delay = 1
    for i in range(retries):
        if get_app_state(marathon, app_id) == wanted_state:
            return True
        time.sleep(delay)
        delay *= 2
    return False


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        if self._play_context.check_mode:
            # in --check mode, always skip this module execution
            result['skipped'] = True
            result['msg'] = 'The dcos task does not support check mode'
            return result

        result['changed'] = False

        args = self._task.args
        wanted_state = args.get('state', 'present')

        # ensure app_id has a single leading forward slash
        app_id = '/' + args.get('app_id', '').strip('/')
        resource = args.get('resource')

        if resource.get('id') is None:
            resource['id'] = app_id

        marathon = dcos.marathon.create_client()

        current_state = get_app_state(marathon, app_id)

        if current_state == wanted_state:
            display.vvv("Marathon app {} already {}".format(
                app_id, wanted_state))
        else:
            display.vvv("Marathon {} not {}".format(app_id, wanted_state))
            if wanted_state == 'present':
                marathon.add_app(resource)
                if not wait_for_app_state(marathon, app_id, wanted_state):
                    raise AnsibleActionFail(
                        'Marathon app does not appear to be running')
            else:
                marathon.remove_app(app_id)
                if not wait_for_app_state(marathon, app_id, wanted_state):
                    raise AnsibleActionFail(
                        'Marathon app still appears to be running')

            result['changed'] = True

        return result
