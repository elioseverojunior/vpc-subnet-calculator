#!/usr/bin/env python3

import argparse
import logging
import os
import sys
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from ipaddress import IPv4Network

from ruamel.yaml import YAML
from ruamel.yaml.representer import RoundTripRepresenter

__version__ = '1.0.0'
__Company__ = 'Elio Severo Junior'

LOGGING_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warn': logging.WARN,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
}


class ValidateOutPutDir(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        os.makedirs(values, exist_ok=True)
        setattr(namespace, self.dest, values)


class ExplicitDefaultsHelpFormatter(ArgumentDefaultsHelpFormatter):
    def _get_help_string(self, action):
        if action.default in (None, False):
            return action.help
        return super()._get_help_string(action)


PARSER = ArgumentParser(
    usage='''%(prog)s\n''',
    description='Python AWS VPC CIDR Blocks',
    add_help=True,
    formatter_class=ExplicitDefaultsHelpFormatter)

PARSER.add_argument('-c', '--vpc-configuration',
                    dest='vpc_configuration',
                    required=False,
                    default=os.path.join(os.getcwd(), 'vpc_configuration.yaml'),
                    type=str,
                    help='AWS VPC Configurations')

PARSER.add_argument('-l', '--log-level',
                    dest='log_level',
                    choices=list(LOGGING_LEVELS.keys()),
                    default='info',
                    help='Log Levels')

PARSER.add_argument('-o', '--output',
                    action=ValidateOutPutDir,
                    dest='output',
                    default=os.path.join(os.getcwd(), 'vpc_configuration_cidr_blocks.yaml'),
                    help='Output Location')

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)


class MigratorRoundTripRepresenter(RoundTripRepresenter):
    def represent_mapping(self, tag, mapping, flow_style=None) -> RoundTripRepresenter:
        if 'name' in mapping:
            mapping.yaml_set_anchor(mapping['name'])
        return RoundTripRepresenter.represent_mapping(self, tag, mapping, flow_style=flow_style)


def represent_merger(self, data):
    return self.represent_scalar(u'tag:yaml.org,2002:merge', u'<<')


def represent_none(self, data):
    return self.represent_scalar(u'tag:yaml.org,2002:null', u'null')


def ignore_aliases(self, data) -> bool:
    return False


yml = YAML()
yml.Representer = MigratorRoundTripRepresenter
yml.preserve_quotes = True
yml.allow_duplicate_keys = True
yml.sort_base_mapping_type_on_output = True
yml.representer.add_representer(type(None), represent_none)
yml.representer.add_representer(u'tag:yaml.org,2002:merge', u'<<')
yml.indent(mapping=2, sequence=4, offset=2)


def get_cidr_blocks(cidr: str, main_cidr_block_mask: int, subnet_mask: int) -> list[str]:
    __cidr_blocks_list = []
    __vpc_cidr = IPv4Network(cidr)
    for it in __vpc_cidr.subnets(new_prefix=main_cidr_block_mask):
        net_range = IPv4Network(it.with_prefixlen)
        for its in net_range.subnets(new_prefix=subnet_mask):
            __cidr_blocks_list.append(its.with_prefixlen)
    return __cidr_blocks_list


def generate_cidr_blocks(cidr: str, total_subnets_needed: int) -> list[str]:
    cidr_blocks_list = []
    main_cidr_block_mask = subnet_mask = int(cidr.split('/')[-1])
    while len(cidr_blocks_list) < total_subnets_needed:
        subnet_mask += 1
        cidr_blocks_list = get_cidr_blocks(cidr, main_cidr_block_mask, subnet_mask)
    return cidr_blocks_list


def write_to_yaml(file_name, data):
    with open(file_name, 'w') as stream:
        yml.indent(mapping=2, sequence=4, offset=2)
        yml.allow_duplicate_keys = False
        yml.explicit_start = True
        yml.dump(data, stream)


def main(args, vpc_configuration):
    subnets_maps = {}
    subnets_maps_normalized = {}
    try:
        for account, vpc_config in vpc_configuration.items():
            subnets_maps.update({
                account: {
                    'cidr': vpc_configuration[account]['cidr'],
                    'region': vpc_configuration[account]['region'],
                    'azs': ["{}{}".format(vpc_configuration[account]['region'], az) for az in vpc_configuration[account]['azs']],
                    'subnets': [],
                    'azs_region_length': len(vpc_configuration[account]['azs']),
                    'total_subnets': sum([value for key, value in vpc_config['subnets'].items()]),
                }
            })

            for subnet_id, zones in vpc_configuration[account]['subnets'].items():
                for zone in ['{}_{}_{}{}'.format(str(idx).rjust(2, '0'),
                                                 subnet_id, vpc_configuration[account]['region'], az)
                             for idx, az in enumerate(vpc_configuration[account]['azs'][:zones])]:
                    subnets_maps[account]['subnets'].append({zone: None})

        for account, vpc_config in subnets_maps.items():
            cidr_blocks = generate_cidr_blocks(cidr=vpc_config['cidr'],
                                               total_subnets_needed=vpc_config['total_subnets'])
            for idx, subnet in enumerate(vpc_config['subnets']):
                subnets_maps[account]['subnets'][idx][list(subnet.keys())[0]] = cidr_blocks[idx]

        for account, vpc_config in subnets_maps.items():
            subnets_maps_normalized.update({
                account: {
                    'cidr': vpc_config['cidr'],
                    'region': vpc_config['region'],
                    'azs': vpc_config['azs'],
                    'subnets': {},
                    'azs_region_length': vpc_config['azs_region_length'],
                    'total_subnets': vpc_config['total_subnets'],
                }
            })
            for subnet in vpc_config['subnets']:
                for k, v in subnet.items():
                    idx, subnet_id, az_region = k.split('_')
                    if not subnets_maps_normalized[account]['subnets'].get(subnet_id):
                        subnets_maps_normalized[account]['subnets'].update({subnet_id: {az_region: None}})
                    subnets_maps_normalized[account]['subnets'][subnet_id][az_region] = v
        print('VPC CIDR Configuration Blocks\n')
        yml.dump(subnets_maps_normalized, sys.stdout)
        write_to_yaml(args.output, subnets_maps_normalized)
        print('\n\n')
    except Exception as ex:
        logger.error(ex)


if __name__ == '__main__':
    args_parser = PARSER.parse_args(args=None if sys.argv[1:] else ['--help'])
    logger.debug(args_parser)

    logger.setLevel(LOGGING_LEVELS[args_parser.log_level])
    logger.debug(logger)

    with open(args_parser.vpc_configuration, 'r') as f:
        config = yml.load(f)
        logger.debug(config)
    main(args_parser, config)
