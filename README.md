# Ansible DC/OS modules

This can be used to control DC/OS.

There are probably lots of bugs. Please report them on github, or create a pull request!

## Examples

Connecting to a cluster, note this will automatically refresh the auth token if it will expire in the next 60 minutes or so.

    - name: Connect to cluster
      dcos_connection:
        url: https://dcos-cluster.example.com
        username: sysadmin
        password: "{{ sysadm_pwd }}"

Installing packages form universe:

    - name: Ensure Spark is installed
      dcos_package:
        name: spark
        app_id: namespace/spark
        state: present
        version: 2.3.1-2.2.1-2
        options:
          service:
            docker-image: "mesosphere/spark:2.3.1-2.2.1-2-hadoop-2.7"
            UCR_containerizer: true
            user: root

Running Marathon applications:

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

Managing IAM users, groups, permissions:

    - name: Ensure a permission resource exists
      dcos_iam_resource:
        rid: dcos:mesos:master:framework:role:*
        state: present

    - name: Create a group
      dcos_iam_group:
        gid: test_group
        description: test group created by Ansible
        state: present
        permissions:
          - rid: dcos:mesos:master:framework:role:*
            action: read

    - name: Create a user
      dcos_iam_user:
        uid: test_user
        description: test user created by Ansible
        password: "{{ lookup('password', '/dev/null') }}"
        groups:
          - test_group

Managing secrets:

    - name: create a secret
      dcos_secret:
        path: foo/password
        value: "{{ lookup('password', '/dev/null') }}"

For more documentation about the modules please check the documentation in the modules
subdirectory.

## Known limitations

- Packages and Marathon apps can not be updated in-place
- Users cannot be assigned permissions individually.
- Error handling is very minimal, some Python experience is required.

All of the above is fixable in either the action plugin or the dcos-python package. Please open issues or pull requests if you find more problems.

## Acknowledgements

Current maintainers:
* [Dirk Jonker][github-dirkjonker]
* [Jan Repnak][github-jrx]

## License
[DC/OS][github-dcos], along with this project, are both open source software released under the
[Apache Software License, Version 2.0](LICENSE).

[github-dcos]: https://github.com/dcos/dcos
[github-jrx]: https://github.com/jrx
[github-dirkjonker]: https://github.com/dirkjonker