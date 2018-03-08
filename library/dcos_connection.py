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
