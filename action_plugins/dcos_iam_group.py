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


def update_permissions(gid, permissions):
    """Check for missing/surplus resource permissions.

    Returns a boolean that indicates whether changes were made.
    """
    wanted_resources = {p['rid'] for p in permissions}
    available = {r['rid'] for r in iam.list_resources()}
    missing = wanted_resources - available

    if missing:
        raise AnsibleActionFail(
            "Cannot grant permissions that do not exist: {}".format(
                ', '.join(missing)))

    # create (rid, action) tuples in a set for comparison
    wanted = {(p['rid'], p['action']) for p in permissions}

    current = set()
    for permission in iam.list_group_permissions(gid):
        rid = permission['rid']
        for action in permission['actions']:
            pair = (rid, action['name'])
            current.add(pair)

    to_add = wanted - current
    to_remove = current - wanted

    for p in to_add:
        display.vvv("Granting {} permission on {} to group {}".format(
            p[1], p[0], gid))
        iam.grant_permission_to_group(gid, p[0], p[1])

    for p in to_remove:
        display.vvv("Revoking {} permission on {} from group {}".format(
            p[1], p[0], gid))
        iam.revoke_permission_from_group(gid, p[0], p[1])

    return len(to_add | to_remove) > 0


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):

        result = super(ActionModule, self).run(tmp, task_vars)
        result['changed'] = False

        args = self._task.args
        gid = args.get('gid')
        description = args.get('description', 'created by Ansible')
        permissions = args.get('permissions', [])
        wanted_state = args.get('state', 'present')

        if gid is None:
            raise AnsibleActionFail('gid cannot be empty for dcos_user')

        group = iam.get_group(gid)
        current_state = 'present' if group is not None else 'absent'

        if self._play_context.check_mode:
            if current_state != wanted_state:
                result['changed'] = True
                result['msg'] = 'would change group {} to be {}'.format(
                    gid, wanted_state)
            return result

        if current_state == wanted_state:
            display.vvv("User {} already {}".format(gid, wanted_state))
            if wanted_state == 'present':
                result['changed'] = update_permissions(gid, permissions)
        else:
            display.vvv("User {} not {}".format(gid, wanted_state))
            try:
                if wanted_state == 'present':
                    iam.create_group(gid, description)
                    update_permissions(gid, permissions)
                    result['msg'] = 'Group {} was created'.format(gid)
                elif wanted_state == 'absent':
                    iam.delete_group(gid)
                    result['msg'] = 'Group {} was deleted'.format(gid)
            except DCOSException as e:
                raise AnsibleActionFail(e)

            result['changed'] = True

        return result
