```
Ubuntu 22.04.3 LTS
Python 3.12.3
pip3 install tabulate
```
```
usage: main.py [-h] {run,init,commit,ps,logs,exec,stop,rm,network} ...

A simple docker implementation based on python3

positional arguments:
  {run,init,commit,ps,logs,exec,stop,rm,network}
    run                 Create a container with namespace and cgroups limit
    init                Init container process run user's process in container. Do not call it outside
    commit              commit container to image
    ps                  list all the containers
    logs                print logs of a container
    exec                exec a command into container
    stop                stop a container
    rm                  remove unused containers
    network             container network commands

options:
  -h, --help            show this help message and exit
```