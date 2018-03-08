import os.path
from urllib.parse import urlparse

from ansible.errors import AnsibleActionFail
from ansible.parsing.yaml.objects import AnsibleUnicode
from ansible.plugins.action import ActionBase
from ansible.module_utils.six import PY2

try:
    import dcos
    import dcos.config
    import dcos.cluster
    import dcoscli.cluster.main
    from dcos.errors import DCOSException
    HAS_DCOS = True
except ImportError:
    HAS_DCOS = False

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


def _version(v):
    return tuple(map(int, v.split('.')))


def _ensure_dcos():
    """Check whether the dcos[cli] package is installed."""
    if PY2:
        raise AnsibleActionFail("Python 3 is required for DC/OS")

    if not HAS_DCOS:
        raise AnsibleActionFail("`dcoscli` library not installed, "
                                "try `pip install dcoscli`")
    else:
        v = _version(dcos.version)
        if v < (0, 5, 0):
            raise AnsibleActionFail("dcos 0.5.x is required, found {}"
                                    .format(dcos.version))
        if v >= (0, 6, 0):
            display.v("dcos cli version > 0.5.x detected, may not work")


def check_cluster(name=None, url=None):
    """Check whether cluster is already setup.

    :param url: url of the cluster
    :return: boolean whether cluster is already setup
    """
    wanted_host = None
    if url:
        wanted_host = urlparse(url).netloc

    cluster = None

    for c in dcos.cluster.get_clusters():
        host = urlparse(c.get_url()).netloc
        if host == wanted_host:
            cluster = c
            break

    if cluster is not None:
        display.vvv("found cluster: {}".format(cluster))
        attached = dcos.config.get_attached_cluster_path()
        cfg_path = os.path.dirname(cluster.get_config_path())
        if attached != cfg_path:
            dcos.cluster.set_attached(cfg_path)
        return True

    display.vvv('no cluster found')

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

        args = {}
        for k, v in self._task.args.items():
            if isinstance(v, AnsibleUnicode):
                args[k] = str(v)
            else:
                args[k] = v

        _ensure_dcos()

        try:
            if not check_cluster(args.get('name'), args.get('url')):
                display.vvv('DC/OS cluster not setup, setting up')

                dcoscli.cluster.main.setup(
                    dcos_url=args.get('url'),
                    insecure=args.get('insecure'),
                    no_check=args.get('no_check'),
                    ca_certs=args.get('ca_certs'),
                    username=args.get('username'),
                    password_str=args.get('password'),
                    password_env=args.get('password_env'),
                    password_file=args.get('password_file'),
                    provider=args.get('provider'),
                    key_path=args.get('private_key'))

                result['changed'] = True
        except DCOSException as e:
            raise
            #raise AnsibleActionFail("Failed to connect to DC/OS cluster: {}".format(e))

        return result
