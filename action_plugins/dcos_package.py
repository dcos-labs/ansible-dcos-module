"""
Action plugin to install a Universe package on a DC/OS cluster.
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import time

from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase

try:
    import dcos.package
except ImportError:
    raise AnsibleActionFail("Missing package: try 'pip install dcos-python'")

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


def get_current_version(package, app_id):
    """Get the current version of an installed package."""

    pm = dcos.package.get_package_manager()
    packages = pm.installed_apps(package, app_id)

    v = None
    for p in packages:
        if p['name'] == package and p['appId'] == '/' + app_id:
            v = p['version']

    display.vvv('{} current version: {}'.format(package, v))
    return v


def get_wanted_version(version, state):
    if state == 'absent':
        return None
    return version


def install_package(name, version, options):
    """Install a Universe package on DC/OS."""
    display.vvv("DC/OS: installing package {} version {}".format(
        name, version))

    pm = dcos.package.get_package_manager()
    package = pm.get_package_version(name, version)
    pm.install_app(package, options)


def uninstall_package(name, app_id):
    """Install a Universe package from DC/OS."""
    display.vvv("DC/OS: uninstalling package {}".format(name))

    pm = dcos.package.get_package_manager()
    dcos.package.uninstall(pm, name, False, app_id, False, True)


def wait_for_package_state(package_name,
                           app_id,
                           wanted_version,
                           retries=5,
                           delay=5):
    """Wait for a package to become in a desired state."""
    for i in range(retries):
        if wanted_version == get_current_version(package_name, app_id):
            return True
        time.sleep(delay)
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

        args = self._task.args
        package_name = args.get('name', None)
        package_version = args.get('version', None)
        state = args.get('state', 'present')

        # ensure app_id has no leading or trailing /
        app_id = args.get('app_id', package_name).strip('/')

        options = args.get('options') or {'service': {}}

        if 'name' not in options['service']:
            options['service']['name'] = app_id

        current_version = get_current_version(package_name, app_id)
        wanted_version = get_wanted_version(package_version, state)

        if current_version == wanted_version:
            display.vvv(
                "Package {} already in desired state".format(package_name))
            result['changed'] = False
        else:
            display.vvv("Package {} not in desired state".format(package_name))
            if wanted_version is not None:
                install_package(package_name, wanted_version, options)
                if not wait_for_package_state(package_name, app_id,
                                              wanted_version):
                    raise AnsibleActionFail('package not installed')
            else:
                uninstall_package(package_name, app_id)
                if not wait_for_package_state(package_name, app_id,
                                              wanted_version):
                    raise AnsibleActionFail('package still installed')

            result['changed'] = True

        return result
