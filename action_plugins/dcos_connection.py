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


def setup_cluster(url, username, password):
    """Setup a connection to a DC/OS cluster."""

    with dcos.cluster.setup_directory() as tempdir:
        dcos.cluster.set_attached(tempdir)

        # in python 2 this url NEEDS to be a str
        # otherwise for some reason toml messes up
        dcos.config.set_val("core.dcos_url", str(url))

        with open('/Users/dirkjonker/.dcos/clusters/setup/dcos.toml') as f:
            display.vvv(f.read())
        # get validated dcos_url
        dcos.config.set_val("core.ssl_verify", "false")

        login(url, username, password)
        dcos.cluster.setup_cluster_config(url, tempdir, False)


def ensure_auth(url, username, password, time_buffer=60 * 60):
    """Ensure that the auth token is valid."""

    token = dcos.config.get_config_val('core.dcos_acs_token')
    parts = token.split('.')
    info = json.loads(base64.b64decode(parts[1]))
    exp = int(info['exp'])
    limit = int(time.time()) + time_buffer
    if exp < limit:
        login(url, username, password)


def login(url, username, password):
    """Login to the current DC/OS cluster."""

    dcos.auth.dcos_uid_password_auth(url, username, password)


def connect_cluster(**kwargs):
    """Connect to a DC/OS cluster by url"""

    changed = False

    url = kwargs.get('url')
    if url is None:
        url = dcos.config.get_config_val('core.dcos_url')

    name = kwargs.get('name')
    username = kwargs.get('username')
    password = kwargs.get('password')
    password_file = kwargs.get('password_file')

    if not password and password_file is not None:
        with open(password_file, 'r') as f:
            password = f.read().strip()

    if not check_cluster(name, url):
        if url is None:
            raise AnsibleActionFail(
                'Not connected: you need to specify the cluster url')
        setup_cluster(url, username, password)

        changed = True

    ensure_auth(url, username, password)
    return changed


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

        result['changed'] = connect_cluster(**args)
        return result
