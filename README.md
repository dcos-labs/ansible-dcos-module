# Ansible DC/OS modules

This can be used to control DC/OS.

Requirements: [dcos-python](https://github.com/dirkjonker/dcos-python) package installed, e.g.
`pip install dcos-python`

Note: this has only been tested with DC/OS 1.10

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

    - name: Run a Marathon application
      dcos_marathon:
        app_id: nginx
        state: present
        resource:
          cpu: 1
          mem: 128
	  instances: 1
          container:
            type: MESOS
            docker:
              image: nginx


For more documentation about the modules please check the documentation in the modules
subdirectory.
