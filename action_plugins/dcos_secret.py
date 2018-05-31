"""
Action plugin to manipulate secrets on a DC/OS enterprise cluster.
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import time

from ansible.errors import AnsibleActionFail
from ansible.module_utils.parsing.convert_bool import boolean
from ansible.plugins.action import ActionBase

try:
    import dcos.security.secrets as secrets
    from dcos.errors import DCOSException
except ImportError:
    raise AnsibleActionFail("Missing package: try 'pip install dcos-python'")

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


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

        path = args.get('path')
        if path is None:
            raise AnsibleActionFail('path cannot be empty for dcos_secret')

        store = args.get('store', 'default')
        value = args.get('value')

        current_val = secrets.get(path, store=store)
        
        current_state = 'present' if current_val is not None else 'absent'

        if current_state == wanted_state:
            display.vvv("Secret {} already {}".format(path, wanted_state))
            if wanted_state == 'present' and current_val != value:
                display.vvv("Updating secret {} with new value".format(path))
                secrets.update(path, value, store=store)
                result['changed'] = True

        else:
            display.vvv("Secret {} not {}".format(path, wanted_state))
            if wanted_state == 'present':
                secrets.create(path, value, store=store)
            elif wanted_state == 'absent':
                secrets.delete(path, store=store)

            result['changed'] = True

        return result
