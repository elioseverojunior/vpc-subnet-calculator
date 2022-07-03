#!/usr/bin/env python3

import sys
from ipaddress import IPv4Network

from ruamel.yaml import YAML
from ruamel.yaml.representer import RoundTripRepresenter


class MigratorRoundTripRepresenter(RoundTripRepresenter):
    def represent_mapping(self, tag, mapping, flow_style=None):
        if 'name' in mapping:
            mapping.yaml_set_anchor(mapping['name'])
        return RoundTripRepresenter.represent_mapping(self, tag, mapping, flow_style=flow_style)


def represent_merger(self, data):
    return self.represent_scalar(u'tag:yaml.org,2002:merge', u'<<')


def represent_none(self, data):
    return self.represent_scalar(u'tag:yaml.org,2002:null', u'null')


def ignore_aliases(self, data):
    return False


yml = YAML()
yml.Representer = MigratorRoundTripRepresenter
yml.preserve_quotes = True
yml.allow_duplicate_keys = True
yml.sort_base_mapping_type_on_output = True
yml.representer.add_representer(type(None), represent_none)
yml.representer.add_representer(u'tag:yaml.org,2002:merge', u'<<')
yml.indent(mapping=2, sequence=4, offset=2)


def generate_cidr_blocks(cidr, total_subnets_needed, environment_name=None):
    cidr_blocks_list = []
    main_cidr_block_mask = subnet_mask = int(cidr.split('/')[-1])
    while len(cidr_blocks_list) < total_subnets_needed:
        cidr_blocks_list = []
        subnet_mask += 1
        vpc_cidr = IPv4Network(cidr)
        for it in vpc_cidr.subnets(new_prefix=main_cidr_block_mask):
            if environment_name:
                print('\n{} {}'.format(environment_name, it.with_prefixlen))
            net_range = IPv4Network(it.with_prefixlen)
            for its in net_range.subnets(new_prefix=subnet_mask):
                cidr_blocks_list.append(its.with_prefixlen)
    return cidr_blocks_list


if __name__ == '__main__':
    vpc_configuration = {
        'devops': {
            'cidr': '172.10.0.0/16',
            'region': 'sa-east-1',
            'subnets': {
                'public': ['a', 'b'],
                'private': ['a', 'b'],
                'lambda': ['a', 'b'],
            },
        },
        'sharedtools': {
            'cidr': '100.100.0.0/16',
            'region': 'us-east-1',
            'subnets': {
                'public': ['a', 'b', 'c'],
                'private': ['a', 'b', 'c'],
                'lambda': ['a', 'b', 'c'],
                'database': ['a', 'b'],
                'elasticache': ['a', 'b'],
            },
        },
        'nickel': {
            'cidr': '100.101.0.0/16',
            'region': 'us-east-1',
            'subnets': {
                'public': ['a', 'b'],
                'private': ['a', 'b'],
                'lambda': ['a', 'b'],
                'database': ['a', 'b'],
                'elasticache': ['a', 'b'],
            },
        },
        'snd': {
            'cidr': '100.102.0.0/16',
            'region': 'us-east-1',
            'subnets': {
                'public': ['a', 'b', 'c'],
                'private': ['a', 'b', 'c'],
                'lambda': ['a', 'b'],
                'database': ['a', 'b'],
                'elasticache': ['a', 'b'],
            },
        },
        'dev': {
            'cidr': '100.103.0.0/16',
            'region': 'us-east-1',
            'subnets': {
                'public': ['a', 'b', 'c'],
                'private': ['a', 'b', 'c'],
                'lambda': ['a', 'b', 'c'],
                'database': ['a', 'b'],
                'elasticache': ['a', 'b'],
            },
        },
        'sit': {
            'cidr': '100.104.0.0/16',
            'region': 'us-east-1',
            'subnets': {
                'public': ['a', 'b', 'c'],
                'private': ['a', 'b', 'c'],
                'lambda': ['a', 'b', 'c'],
                'database': ['a', 'b'],
                'elasticache': ['a', 'b'],
            },
        },
        'perf': {
            'cidr': '100.105.0.0/16',
            'region': 'us-east-1',
            'subnets': {
                'public': ['a', 'b', 'c'],
                'private': ['a', 'b', 'c'],
                'lambda': ['a', 'b', 'c'],
                'database': ['a', 'b'],
                'elasticache': ['a', 'b'],
            },
        },
        'pre': {
            'cidr': '100.106.0.0/16',
            'region': 'us-east-1',
            'subnets': {
                'public': ['a', 'b', 'c'],
                'private': ['a', 'b', 'c'],
                'lambda': ['a', 'b', 'c'],
                'database': ['a', 'b'],
                'elasticache': ['a', 'b'],
            },
        },
        'prod': {
            'cidr': '100.107.0.0/16',
            'region': 'us-east-1',
            'subnets': {
                'public': ['a', 'b', 'c'],
                'private': ['a', 'b', 'c'],
                'lambda': ['a', 'b', 'c'],
                'database': ['a', 'b'],
                'elasticache': ['a', 'b'],
            },
        },
    }
    subnets_maps = {}

    for account, vpc_config in vpc_configuration.items():
        subnets_maps.update({
            account: {
                'cidr': vpc_configuration[account]['cidr'],
                'region': vpc_configuration[account]['region'],
                'biggest_azs_region': max([len(value) for key, value in vpc_config['subnets'].items()]),
                'total_subnets': sum([len(value) for key, value in vpc_config['subnets'].items()]),
                'subnets': []
            }
        })

        for subnet_id, zones in vpc_configuration[account]['subnets'].items():
            for zone in zones:
                subnets_maps[account]['subnets'].append({'{}_{}{}'.format(subnet_id, vpc_configuration[account]['region'], zone): ''})
            print()

    for account, vpc_config in subnets_maps.items():
        cidr_blocks = generate_cidr_blocks(cidr=vpc_config['cidr'], total_subnets_needed=vpc_config['total_subnets'], environment_name=account)
        for idx, network in enumerate(vpc_config['subnets']):
            subnets_maps[account]['subnets'][idx][list(network.keys())[0]] = cidr_blocks[idx]
            print('{}\t\t\t=> {}'.format(list(network.keys())[0], cidr_blocks[idx]))

    subnets_maps_normalized = {}

    for account, vpc_config in subnets_maps.items():
        subnets_maps_normalized.update({
            account: {
                'cidr': vpc_config['cidr'],
                'region': vpc_config['region'],
                'biggest_azs_region': vpc_config['biggest_azs_region'],
                'total_subnets': vpc_config['total_subnets'],
                'subnets': {}
            }
        })
        for subnet in vpc_config['subnets']:
            for k, v in subnet.items():
                subnet_id, az_region = k.split('_')
                if not subnets_maps_normalized[account]['subnets'].get(subnet_id):
                    subnets_maps_normalized[account]['subnets'].update({subnet_id: {vpc_config['region']: {az_region: None}}})
                subnets_maps_normalized[account]['subnets'][subnet_id][vpc_config['region']][az_region] = v
                print('%s => { %s => %s }' % (subnet, k, v))

    print('\n\n')
    yml.dump(subnets_maps_normalized, sys.stdout)
    with open('./vpc_config.yaml', 'w') as stream:
        yml.indent(mapping=2, sequence=4, offset=2)
        yml.allow_duplicate_keys = False
        yml.explicit_start = True
        yml.dump(subnets_maps_normalized, stream)
    print('\n\n')
