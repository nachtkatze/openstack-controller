# openstack-controller
OpenStack controller for booting networking topologies

# Topologies

## FwLbaaS
First, run a `source openrc.sh` in order to work with the right tenant.

To run the topology (default FwLb topo):
```
python run.py boot
```

To shutdown all the elements in the tenant:
```
python run.py shutdown --topo all
```
