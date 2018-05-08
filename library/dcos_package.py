from __future__ import absolute_import, division, print_function
__metaclass__ = type

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
    app_id:
        description:
            - The name of the application in DC/OS
    options:
        description:
            - An object containing the application specific options

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
