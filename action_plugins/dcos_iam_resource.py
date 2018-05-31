"""
Action plugin to manipulate permission resources on a DC/OS enterprise cluster.
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase

try:
    import dcos.security.iam as iam
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
        result['changed'] = False

        args = self._task.args
        rid = args.get('rid')
        description = args.get('description', 'created by Ansible')
        wanted_state = args.get('state', 'present')

        if rid is None:
            raise AnsibleActionFail(
                'rid cannot be empty for dcos_iam_resource')

        group = iam.get_group(rid)
        current_state = 'present' if group is not None else 'absent'

        if self._play_context.check_mode:
            if current_state != wanted_state:
                result['changed'] = True
                result['msg'] = 'would change resource {} to be {}'.format(
                    rid, wanted_state)
            return result

        if current_state == wanted_state:
            display.vvv("User {} already {}".format(rid, wanted_state))
        else:
            display.vvv("User {} not {}".format(rid, wanted_state))
            if not self._play_context.check_mode:
                try:
                    if wanted_state == 'present':
                        iam.create_resource(rid, description)
                        result['msg'] = 'Resource {} was created'.format(rid)
                    elif wanted_state == 'absent':
                        iam.delete_resource(rid)
                        result['msg'] = 'Resource {} was deleted'.format(rid)
                except DCOSException as e:
                    raise AnsibleActionFail(e)

            result['changed'] = True

        return result
