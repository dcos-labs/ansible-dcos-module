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
        version: 2.3.0-2.2.1-2
        state: present
        options:
          service:
            UCR_containerizer: true
            user: root

Running Marathon applications:

    - name: Run a Marathon application
      dcos_marathon:
        app_id: nginx
        state: present
        options:
          cpus: 0.1
          mem: 128
          instances: 1
          container:
            type: MESOS
            docker:
              image: nginx
            portMappings:
              - containerPort: 80
                hostPort: 0
                protocol: tcp
                name: default
          networks:
            - mode: container/bridge

Managing IAM users, groups, permissions:

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

## Playbooks

Below are some playbooks that make use of the different actions:

* [Install Kubernetes on DC/OS Enterprise](plays/kubernetes.yml)
* [Expose Kubectl Proxy via Edge-LB](plays/kubectl-edgelb.yml)
* [Expose Kubectl Proxy via Marathon-LB](plays/kubectl-mlb.yml)
* [Install Confluent-Kafka](plays/confluent-kafka.yml)
* [Expose Confluent-Kafka via Edge-LB](plays/confluent-kafka-edgelb.yml)
* [Install DC/OS Monitoring](plays/monitoring.yml)
* [Install DC/OS Package Registry](plays/package-registry.yml)

## Known limitations

* Package and Marathon app updates are triggered with every Ansible run.
* Users and service-accounts cannot be assigned permissions individually.
* Revoking of permissions is not possible.
* Error handling is very minimal, some Python experience is required.

All of the above is fixable in either the action plugin or the DC/OS CLI. Please open issues or pull requests if you find more problems.

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
