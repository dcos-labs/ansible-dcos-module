# Ansible DC/OS modules

This can be used to control DC/OS.

Requirements: Python 3 and 'dcoscli' package installed, e.g.
`pip install dcoscli`

Examples:

    ---
    - name: Connect to cluster
      dcos_connection:
        url: https://dcos-cluster.example.com
        username: sysadmin
        password: "{{ sysadm_pwd }}"

    - name: Ensure Spark is installed
      dcos_package:
        name: spark
        state: present
        version: 2.0.1-2.2.0-1
