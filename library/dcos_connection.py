#!/usr/bin/env python

ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'nobody'
}

DOCUMENTATION = '''
---
module: dcos_connection
short_description: Connects and authenticates to a DC/OS cluster
description:
    - "This module handles connection to DC/OS"

options:
    url:
        description:
            - The full url to the DC/OS cluster, including http/https
    insecure:
        description:
            - Whether or not to verify the TLS connection certificate
    no_check:
        description:
            - Whether or not to verify the downloaded CA certificate
    ca_certs:
        description:
            - Path to root CA to verify requests
    username:
        description:
            - The username to connect with DC/OS
    password:
        description:
            - The password of the user
    password_file:
        description:
            - Path to a file containing the password
    provider:
        description:
            - Name of the identity provider
    private_key:
        description:
            - Path to file with private key

author:
    - Dirk Jonker (@dirkjonker)
'''

EXAMPLES = '''
# connect to a cluster
- name: Connect to DC/OS
  dcos_connection:
    dcos_url: https://dcos-cluster.example.com
    username: superuser
    password: "{{ dcos_superuser_password }}"

- name: Connect to DC/OS over ssh tunnel
  dcos_connection:
    dcos_url: https://localhost:8443
    insecure: true
    username: superuser
    password: "{{ dcos_superuser_password }}"
'''

RETURN = '''
nothing special
'''

import os.path
from urllib.parse import urlparse

from ansible.module_utils.basic import AnsibleModule
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


def check_cluster(url):
    """Check whether cluster is already setup.

    :param url: url of the cluster
    :return: boolean whether cluster is already setup
    """
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


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            url=dict(type='str'),
            insecure=dict(type='bool'),
            no_check=dict(type='bool'),
            ca_cert=dict(type='path'),
            username=dict(type='str'),
            password=dict(type='str', no_log=True),
            password_file=dict(type='path'),
            provider=dict(type='str'),
            key_path=dict(type='path'),
        ),
        mutually_exclusive=[['password', 'password_file', 'key_path']],
        supports_check_mode=True,
    )

    _ensure_dcos(module)

    result = dict(changed=False)

    if module.check_mode:
        return result

    try:
        if not check_cluster(module.params['url']):
            print('not setup, setting up')
            dcoscli.cluster.main.setup(
                dcos_url=module.params['url'],
                insecure=module.params['insecure'],
                no_check=module.params['no_check'],
                ca_certs=module.params['ca_cert'],
                username=module.params['username'],
                password_str=module.params['password'],
                password_file=module.params['password_file'],
                provider=module.params['provider'],
                key_path=module.params['key_path'],
            )
            result['changed'] = True
    except DCOSException as e:
        module.fail_json("Failed to connect to DC/OS cluster: {}".format(e))

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
