"""
Action plugin to configure a DC/OS cluster.
Uses the Ansible host to connect directly to DC/OS.
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail
from ansible.module_utils.six import PY2
#from ansible.utils.vars import merge_hash

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()

try:
    import dcos
    import dcos.config
    import dcos.cluster
    import dcos.package
    import dcoscli.cluster.main
    from dcos.errors import DCOSException
    HAS_DCOS = True
except ImportError:
    HAS_DCOS = False


def _version(v):
    return tuple(map(int, v.split('.')))


def _ensure_dcos():
    """Check whether the dcos[cli] package is installed."""
    if PY2:
        raise AnsibleActionFail("Python 3 is required for DC/OS")

    if not HAS_DCOS:
        raise AnsibleActionFail(msg="Package `dcoscli` is not installed, try `pip install dcoscli`")
    else:
        v = _version(dcos.version)
        if v < (0, 5, 0):
            raise AnsibleActionFail("dcos 0.5.x is required, found {}".format(dcos.version))
        if v >= (0, 6, 0):
            raise AnsibleActionFail("dcos cli version > 0.5.x detected, may not work")
    display.vvv("dcos: all prerequisites seem to be in order")


def check_cluster(url=None):
    """Check whether cluster is already setup.

    :param url: url of the cluster
    :return: boolean whether cluster is already setup
    """
    if url is None:
        # check if any cluster is currently attached
        return any(c.is_attached() for c in dcos.cluster.get_clusters())

    parsed = urlparse(url)

    current_cluster = None

    for c in dcos.cluster.get_clusters():
        cluster = urlparse(c.get_url())
        if cluster.netloc == parsed.netloc:
            current_cluster = c
            break

    if current_cluster is not None:
        attached = dcos.config.get_attached_cluster_path()
        cfg_path = os.path.dirname(current_cluster.get_config_path())
        if attached != cfg_path:
            dcos.config.set_attached(cfg_path)
        return True

    return False


def connect_cluster(url=None, **kwargs):
    """Connect to a DC/OS cluster by url"""

    if url is None:
        raise AnsibleActionFail('No DC/OS cluster attached, please suppply dcos_url parameter')

    try:
        if not check_cluster(url):
            print('not setup, setting up')
            dcoscli.cluster.main.setup(
                dcos_url=kwargs.get('url'),
                insecure=kwargs.get('insecure'),
                no_check=kwargs.get('no_check_ca'),
                ca_certs=kwargs.get('ca_cert'),
                username=kwargs.get('username'),
                password_str=kwargs.get('password'),
                password_file=kwargs.get('password_file'),
                provider=kwargs.get('identity_provider'),
                key_path=kwargs.get('key_path'),
            )
            result['changed'] = True
    except DCOSException as e:
        module.fail_json("Failed to connect to DC/OS cluster: {}".format(e))


def get_current_version(pm, package, app_id):
    """Get the current version of an installed package."""
    packages = {p['name']: p['version'] for p in pm.installed_apps(package, app_id)}
    display.vvv('packages: {}'.format(packages))
    v = packages.get(package)
    display.vvv('{} current version: {}'.format(package, v))
    return v


def get_wanted_version(version, state):
    if state == 'absent':
        return None
    return version


def install_package(pm, package, version, options=None):
    """Install a Universe package on DC/OS."""
    display.vvv("DC/OS: installing package {} version {}"
                .format(package, version))
    display.vvv("options: {}".format(options))
    pkg = pm.get_package_version(package, version)

    if pkg.marathon_template():
        # check options before trying to install
        pkg.options(options)

    display.vvv('pkg: {}'.format(pkg))
    return pm.install_app(pkg, options, app_id=None)


def uninstall_package(pm, package, app_id):
    display.vvv("DC/OS: uninstalling package {}".format(package))
    return pm.uninstall_app(package, remove_all=True, app_id=app_id)


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
        package_name = args.get('name', None)
        package_version = args.get('version', None)
        state = args.get('state', 'present')
        app_id = args.get('app_id', package_name)
        options = args.get('options') or {}
        options['name'] = app_id

        _ensure_dcos()

        connect_options = args.get('connect_options')
        if connect_options:
            url = args.get('cluster_url')
            if not check_cluster(url):
                connect_cluster(url, **args)
        else:
            display.vvv("Warning: no connection options found, "
                        "assuming an attached and authenticated cluster")

        pm = dcos.package.get_package_manager()

        current_version = get_current_version(pm, package_name, app_id)
        wanted_version = get_wanted_version(package_version, state)

        if current_version == wanted_version:
            display.vvv("Package {} already in desired state".format(package_name))
            result['changed'] = False
        else:
            display.vvv("Package {} not in desired state".format(package_name))
            try:
                if wanted_version is not None:
                    install_package(pm, package_name, wanted_version, options)
                    if wanted_version != get_current_version(pm, package_name, app_id):
                        raise AnsibleActionFail('failed to install')
                else:
                    uninstall_package(pm, package_name, app_id)
                    if wanted_version != get_current_version(pm, package_name, app_id):
                        raise AnsibleActionFail('failed to uninstall')

            except DCOSException as e:
                #raise AnsibleActionFail(e)
                raise

            result['changed'] = True

        return result
