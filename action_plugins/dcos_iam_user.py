"""
Action plugin to manipulate users on a DC/OS enterprise cluster.
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


def update_group_memberships(uid, groups):
    """Check for missing/surplus group membership.

    Returns a boolean that indicates whether changes were made.
    """
    wanted = set(groups)
    available = {g['gid'] for g in iam.list_groups()}
    missing = wanted - available

    if missing:
        raise AnsibleActionFail(
            "Cannot add user to groups that do not exist: {}".format(
                ', '.join(missing)))

    current = {g['group']['gid'] for g in iam.get_user_groups(uid)}
    to_add = wanted - current
    to_remove = current - wanted

    for gid in to_add:
        display.vvv("Adding user {} to group {}".format(uid, gid))
        iam.add_user_to_group(uid, gid)

    for gid in to_remove:
        display.vvv("Removing user {} from group {}".format(uid, gid))
        iam.delete_user_from_group(uid, gid)

    return len(to_add | to_remove) > 0


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):

        result = super(ActionModule, self).run(tmp, task_vars)
        result['changed'] = False

        args = self._task.args
        uid = args.get('uid')
        groups = args.get('groups', [])
        wanted_state = args.get('state', 'present')

        if uid is None:
            raise AnsibleActionFail('uid cannot be empty for dcos_user')

        user = iam.get_user(uid)

        current_state = 'present' if user is not None else 'absent'

        if self._play_context.check_mode:
            if current_state != wanted_state:
                result['changed'] = True
                result['msg'] = 'would change user {} to be {}'.format(
                    uid, wanted_state)
            return result

        if current_state == wanted_state:
            display.vvv("User {} already {}".format(uid, wanted_state))
            if wanted_state == 'present':
                result['changed'] = update_group_memberships(uid, groups)
        else:
            display.vvv("User {} not {}".format(uid, wanted_state))
            try:
                if wanted_state == 'present':
                    iam.create_user(uid, **iam.check_user_args(**args))
                    update_group_memberships(uid, groups)
                    result['msg'] = "User {} was created".format(uid)
                elif wanted_state == 'absent':
                    iam.delete_user(uid)
                    result['msg'] = "User {} was deleted".format(uid)
            except DCOSException as e:
                raise AnsibleActionFail(e.text)

            result['changed'] = True

        return result
