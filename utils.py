from subprocess import Popen, PIPE

"""
Several utilities
"""

def parse_config(config):
        """
        Parse the config from a config file. Parse to a list
        in case of comma-separated values.
        """
        c = dict()
        for k,v in config.items():
            c[k] = v.split(',')
        return c

def parse_fw_config(config):
    c = {'rules':list()}
    for k,v, in config.items():
        if k.split('_')[0] == 'rule':
            rule = dict()
            rule_opts = v.split(',')
            for opt in rule_opts:
                value_option = opt.split(':')
                rule[value_option[0]] = value_option[1]
            c['rules'].append(rule)
        else:
            c[k] = v
    return c

def call_sub(args, response=False):
	p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
	out,err = p.communicate()
	code = p.returncode
	if response:
		if code == 0:
			return out
		else:
			raise SubprocessError('call failed: {}'.format(err))
	else:
		if code == 0:
			return
		else:
			raise SubprocessError('call failed')

class SubprocessError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

