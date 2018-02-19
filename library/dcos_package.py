#!/usr/bin/env python

ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'nobody'
}

DOCUMENTATION = '''
---
module: dcos_package
short_description: Manages DC/OS package state
description:
    - "This module handles package state on DC/OS"

options:
    name:
        description:
            - This is the package name
        required: true
    state:
        description:
            - Whether to install (`present` or `latest`), or remove (`absent`) a package.
    version:
        description:
            - The version of the package
        required: false
    app_id:
        description:
            - The name of the application in DC/OS
        required: false
    options:
        description:
            - An object containing the application specific options
        required: false

author:
    - Dirk Jonker (@dirkjonker)
'''

EXAMPLES = '''
# Install a specific version of a package
- name: Install Spark
  dcos_package:
    name: spark
    state: present
    version: 2.0.1-2.2.0-1

# Ensure absense of a package
- name: Make sure Spark is not installed
  dcos_package:
    name: spark
    state: absent
'''

RETURN = '''
nothing special
'''

from ansible.module_utils.basic import AnsibleModule

try:
    import dcos
    import dcos.package
    from dcos.errors import DCOSException
    HAS_DCOS = True
except ImportError:
    HAS_DCOS = False

from ansible.module_utils.six import PY2


def _version(v):
    return tuple(map(int, v.split('.')))


def _ensure_dcos(module):
    """Check whether the dcos[cli] package is installed."""
    if PY2:
        module.fail_json(msg="Python 3 is required for DC/OS")

    if not HAS_DCOS:
        module.fail_json(msg="`dcoscli` is not installed, but it is required "
                             "for the Ansible dcos_package module")
    else:
        v = _version(dcos.version)
        if v < (0, 5, 0):
            module.fail_json(msg="dcos 0.5.x is required, found {}"
                                 .format(dcos.version))
        if v >= (0, 6, 0):
            module.warn("dcos cli version > 0.5.x detected, may not work")


def get_current_version(pm, package, app_id):
    packages = {p['name']: p['version'] for p in pm.installed_apps(None, None)}
    return packages.get(package)


def get_wanted_version(version, state):
    if state == 'absent':
        return None
    return version


def install_package(pm, package, app_id, version, options=None):
    print('DC/OS: installing package {} version {}'
          .format(package, version))
    pkg = pm.get_package_version(package, version)
    return pm.install_app(pkg, options)


def uninstall_package(pm, package, app_id):
    print("DC/OS: uninstalling package {}".format(package))
    return pm.uninstall_app(package, remove_all=True, app_id=app_id)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', required=True),
            version=dict(type='str', default=None),
            state=dict(type='str', choices=['absent', 'present'], default='present'),
            app_id=dict(type='str', default=None),
            options=dict(type='dict', default=None)
        ),
        supports_check_mode=True
    )

    _ensure_dcos(module)

    result = dict(changed=False)

    if module.check_mode:
        return result

    pm = dcos.package.get_package_manager()

    package_name = module.params['name']
    app_id = '/' + (module.params['app_id'] or package_name)
    options = module.params['options'] or dict(name='app_id')
    package_version = module.params['version']

    current_version = get_current_version(pm, package_name, app_id)
    wanted_version = get_wanted_version(package_version, module.params['state'])

    if current_version != wanted_version:
        try:
            if wanted_version is not None:
                install_package(pm, package_name, app_id, version, options)
                if wanted_version != get_current_version(pm, package_name, app_id):
                    module.fail_json('failed to install')
            else:
                uninstall_package(pm, package_name, app_id)
                if wanted_version != get_current_version(pm, package_name, app_id):
                    module.fail_json('failed to uninstall')
        except DCOSException as e:
            module.fail_json(str(e), **result)

        result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()
