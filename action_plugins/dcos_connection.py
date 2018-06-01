"""
Action plugin to configure a DC/OS cluster.
Uses the Ansible host to connect directly to DC/OS.
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import base64
import json
import time

from six.moves.urllib.parse import urlparse

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail

try:
    import dcos.auth
    import dcos.config
    import dcos.cluster
except ImportError:
    raise AnsibleActionFail("Missing package: try 'pip install dcos-python'")

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


def check_cluster(name=None, url=None):
    """Check whether cluster is already setup.

    :param url: url of the cluster
    :return: boolean whether cluster is already setup
    """

    if url is not None:
        fqdn = urlparse(url).netloc
    else:
        fqdn = None

    display.vvv('Checking cluster @ {}'.format(fqdn))

    attached_cluster = None
    wanted_cluster = None

    for c in dcos.cluster.get_clusters():
        if fqdn == urlparse(c.get_url()).netloc:
            wanted_cluster = c
        elif c.get_name() == name:
            wanted_cluster = c
        if c.is_attached():
            attached_cluster = c

    display.vvv('wanted:\n{}\nattached:\n{}\n'.format(wanted_cluster,
                                                      attached_cluster))

    if wanted_cluster is None:
        return False
    elif wanted_cluster == attached_cluster:
        return True
    else:
        dcos.cluster.set_attached(wanted_cluster.get_cluster_path())
        return True


def ensure_auth(url, username, password, time_buffer=60 * 60):
    """Ensure that the auth token is valid.

    Returns boolean whether auth was refreshed"""

    token = dcos.config.get_config_val('core.dcos_acs_token')
    parts = token.split('.')
    info = json.loads(base64.b64decode(parts[1]))
    exp = int(info['exp'])
    limit = int(time.time()) + time_buffer
    if exp < limit:
        dcos.auth.dcos_uid_password_auth(url, username, password)
        return True
    return False


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):

        result = super(ActionModule, self).run(tmp, task_vars)
        result['changed'] = False

        if self._play_context.check_mode:
            # in --check mode, always skip this module execution
            result['skipped'] = True
            result['msg'] = 'dcos_connection does not support check mode'
            return result

        args = self._task.args

        url = args.get('url')
        if url is None:
            url = dcos.config.get_config_val('core.dcos_url')

        name = args.get('name')
        username = args.get('username')
        password = args.get('password')
        password_file = args.get('password_file')

        if not password and password_file is not None:
            with open(password_file, 'r') as f:
                password = f.read().strip()

        if not check_cluster(name, url):
            if url is None:
                raise AnsibleActionFail(
                    'Not connected: you need to specify the cluster url')
            dcos.cluster.setup_cluster(url, username, password)

            result['changed'] = True
            result['msg'] = 'Cluster connection updated to {}'.format(url)

        if ensure_auth(url, username, password):
            result['changed'] = True
            result['msg'] = '\n'.join(result['msg'], 'refreshed auth token')
        return result
