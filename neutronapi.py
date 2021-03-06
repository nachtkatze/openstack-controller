import json

from utils import call_sub

class NeutronIF():
    """
    Interface to the neutron api using command line orders.
    The methods names are the same as the commands from neutron. Ex:
    router-delete is called by router_delete
    """

    def __init__(self, encoding='utf-8'):
        self.encoding = encoding

    def _select_name_id(self, id_=None, name=None):
        if not id_ is None:
            param = id_
        else:
            param = name
        return param

    def _decode(self, value):
        return str(value.decode('utf-8'))

    def router_list(self):
        resp = call_sub(['neutron', 'router-list', '-f', 'json'], response=True)
        resp = self._decode(resp)
        return json.loads(resp)

    def router_port_list(self, router_id=None, router_name=None):
        router = self._select_name_id(id_=router_id, name=router_name)
        resp = call_sub(['neutron', 'router-port-list', router, '-f', 'json'],
                 response=True)
        resp = self._decode(resp)
        return json.loads(resp)

    def router_gateway_clear(self, router_id=None, router_name=None):
        router = self._select_name_id(id_=router_id, name=router_name)
        call_sub(['neutron', 'router-gateway-clear', router])

    def router_interface_delete(self, router_id=None, router_name=None,
            subnet_id=None, subnet_name=None, port_id=None, port_name=None):
        subnet = self._select_name_id(id_=subnet_id, name=subnet_name)
        port = self._select_name_id(id_=port_id, name=port_name)
        router = self._select_name_id(id_=router_id, name=router_name)
        subnet_port = ''
        if subnet is None:
            subnet_port = 'port={}'.format(port)
        else:
            subnet_port = subnet
        call_sub(['neutron', 'router-interface-delete', router, subnet_port])

    def router_delete(self, router_id=None, router_name=None):
        router = self._select_name_id(id_=router_id, name=router_name)
        call_sub(['neutron', 'router-delete', router])

    def firewall_rule_create(self, rule_opts=None):
        opts = ''
        for opt, value in rule_opts.items():
            option = '--{} {} '.format(str(opt), str(value))
            opts += option
        command = ['neutron', 'firewall-rule-create']
        command.extend(opts.split())
        call_sub(command)

    def firewall_policy_create(self, name=None, fw_rules=None):
       call_sub(['neutron', 'firewall-policy-create', name, '--firewall-rules',
                fw_rules])

    def firewall_create(self, name=None, fw_policy=None, router=None):
        call_sub(['neutron', 'firewall-create', fw_policy, '--name', name,
                 '--router', router])

    def firewall_list(self):
        resp = call_sub(['neutron', 'firewall-list', '-f', 'json'], 
                        response=True)
        resp = self._decode(resp)
        return json.loads(resp)

    def firewall_delete(self, name=None, id_=None):
        fw = self._select_name_id(id_=id_, name=name)
        call_sub(['neutron', 'firewall-delete', fw])

    def firewall_policy_list(self):
        resp = call_sub(['neutron', 'firewall-policy-list', '-f', 'json'],
                       response=True)
        resp = self._decode(resp)
        return json.loads(resp)

    def firewall_policy_delete(self, name=None, id_=None):
        policy = self._select_name_id(id_=id_, name=name)
        call_sub(['neutron', 'firewall-policy-delete', policy])

    def firewall_rule_list(self):
        resp = call_sub(['neutron', 'firewall-rule-list', '-f', 'json'],
                       response=True)
        resp = self._decode(resp)
        return json.loads(resp)

    def firewall_rule_delete(self, id_=None, name=None):
        rule = self._select_name_id(id_=id_, name=name)
        call_sub(['neutron', 'firewall-rule-delete', rule])
