#!/usr/bin/env python3

import argparse
import logging
import os
import sys
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from ipaddress import IPv4Network

from ruamel.yaml import YAML
from ruamel.yaml.representer import RoundTripRepresenter

# Constants
__version__ = '1.0.0'
__Company__ = 'Elio Severo Junior'
DEFAULT_VPC_CONFIG_PATH = os.path.join(os.getcwd(), 'vpc_configuration.yaml')
DEFAULT_OUTPUT_PATH = os.path.join(os.getcwd(), 'vpc_configuration_cidr_blocks.yaml')

LOGGING_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warn': logging.WARN,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
}

# Logging setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format='%(asctime)s %(message)s')


# Custom Argument Parser Action
class ValidateOutputDir(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        os.makedirs(values, exist_ok=True)
        setattr(namespace, self.dest, values)


# Formatter Class with Explicit Defaults
class ExplicitDefaultsHelpFormatter(ArgumentDefaultsHelpFormatter):
    def _get_help_string(self, action):
        if action.default in (None, False):
            return action.help
        return super()._get_help_string(action)


# YAML Configuration
class YamlConfigurator:
    def __init__(self):
        self.yaml = YAML()
        self.yaml.Representer = self.MigratorRoundTripRepresenter
        self.yaml.preserve_quotes = True
        self.yaml.allow_duplicate_keys = True
        self.yaml.sort_base_mapping_type_on_output = True
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self.yaml.representer.add_representer(type(None), self.represent_none)

    class MigratorRoundTripRepresenter(RoundTripRepresenter):
        def represent_mapping(self, tag, mapping, flow_style=None) -> RoundTripRepresenter:
            if 'name' in mapping:
                mapping.yaml_set_anchor(mapping['name'])
            return RoundTripRepresenter.represent_mapping(self, tag, mapping, flow_style=flow_style)

    @staticmethod
    def represent_none(self, data):
        return self.represent_scalar(u'tag:yaml.org,2002:null', u'null')

    def dump_to_file(self, file_name, data):
        with open(file_name, 'w') as stream:
            self.yaml.explicit_start = True
            self.yaml.dump(data, stream)


# Functions
def get_cidr_blocks(cidr: str, main_cidr_block_mask: int, subnet_mask: int) -> list[str]:
    cidr_blocks = []
    vpc_cidr = IPv4Network(cidr)
    for subnet in vpc_cidr.subnets(new_prefix=main_cidr_block_mask):
        net_range = IPv4Network(subnet.with_prefixlen)
        for smaller_subnet in net_range.subnets(new_prefix=subnet_mask):
            cidr_blocks.append(smaller_subnet.with_prefixlen)
    return cidr_blocks


def generate_cidr_blocks(cidr: str, total_subnets_needed: int) -> list[str]:
    cidr_blocks_list = []
    main_cidr_block_mask = subnet_mask = int(cidr.split('/')[-1])
    while len(cidr_blocks_list) < total_subnets_needed:
        subnet_mask += 1
        cidr_blocks_list = get_cidr_blocks(cidr, main_cidr_block_mask, subnet_mask)
    return cidr_blocks_list


class VpcConfiguration:
    cidr: str
    region: str
    azs: list[str]
    subnets: list[dict[str, int]]
    azs_region_length: int
    total_subnets: int

    def __init__(self, vpc_config: dict):
        region = vpc_config['region'].split('-')
        self.cidr = vpc_config['cidr']
        self.region = '-'.join(vpc_config['region'].split('-')[:-1] if len(region) > 2 else region)
        self.azs = [f"{self.region}{az}" for az in vpc_config['azs']]
        self.subnets = self.__set_subnets(vpc_config)
        self.azs_region_length: len(vpc_config['azs'])
        self.total_subnets: sum(vpc_config['subnets'].values())

    def __set_subnets(self, vpc_config: dict) -> list[dict[str, int]]:
        subnets: list[dict[str, int]] = []
        for subnet_id, subnet_count in vpc_config['subnets'].items():
            for idx, az in enumerate(vpc_config['azs'][:subnet_count]):
                subnets.append({f"{str(idx).rjust(2, '0')}_{subnet_id}_{self.region}{az}": None})
        return subnets


class VpcAccountConfiguration:
    account: str
    vpc_configuration: VpcConfiguration

    def __init__(self, account, vpc_configuration: dict):
        self.account = account
        self.vpc_configuration = VpcConfiguration(vpc_configuration)


def parse_vpc_configuration(vpc_configuration: dict) -> dict:
    subnets_maps = {}
    for account, vpc_config in vpc_configuration.items():
        subnets_maps[account] = {
            'cidr': vpc_config['cidr'],
            'region': vpc_config['region'],
            'azs': [f"{vpc_config['region']}{az}" for az in vpc_config['azs']],
            'subnets': [],
            'azs_region_length': len(vpc_config['azs']),
            'total_subnets': sum(vpc_config['subnets'].values()),
        }
        for subnet_id, subnet_count in vpc_config['subnets'].items():
            subnets_maps[account]['subnets'].extend(
                {f"{str(idx).rjust(2, '0')}_{subnet_id}_{vpc_config['region']}{az}": None} for idx, az in
                enumerate(vpc_config['azs'][:subnet_count])
            )
    return subnets_maps


def normalize_subnets(subnets: dict) -> dict:
    normalized_subnets = {}
    for account, config in subnets.items():
        normalized_subnets[account] = {
            'cidr': config['cidr'],
            'region': config['region'],
            'azs': config['azs'],
            'subnets': {},
            'azs_region_length': config['azs_region_length'],
            'total_subnets': config['total_subnets'],
        }
        for subnet in config['subnets']:
            for key, value in subnet.items():
                idx, subnet_id, az_region = key.split('_')
                if not normalized_subnets[account]['subnets'].get(subnet_id):
                    normalized_subnets[account]['subnets'][subnet_id] = {}
                normalized_subnets[account]['subnets'][subnet_id][az_region] = value
    return normalized_subnets


def main(args, vpc_configuration):
    subnets_maps = parse_vpc_configuration(vpc_configuration)
    for account, vpc_config in subnets_maps.items():
        cidr_blocks = generate_cidr_blocks(vpc_config['cidr'], vpc_config['total_subnets'])
        for idx, subnet in enumerate(vpc_config['subnets']):
            subnet_key = list(subnet.keys())[0]
            subnets_maps[account]['subnets'][idx][subnet_key] = cidr_blocks[idx]

    subnets_maps_normalized = normalize_subnets(subnets_maps)
    yml_config.dump_to_file(args.output, subnets_maps_normalized)
    yml_config.yaml.dump(subnets_maps_normalized, sys.stdout)


# Argument parser setup
PARSER = ArgumentParser(
    usage='''%(prog)s\n''',
    description='Python AWS VPC CIDR Blocks',
    add_help=True,
    formatter_class=ExplicitDefaultsHelpFormatter
)
PARSER.add_argument('-c', '--vpc-configuration',
                    dest='vpc_configuration',
                    required=False,
                    default=DEFAULT_VPC_CONFIG_PATH,
                    type=str,
                    help='AWS VPC Configurations')
PARSER.add_argument('-l', '--log-level',
                    dest='log_level',
                    required=False,
                    choices=LOGGING_LEVELS.keys(),
                    default='info',
                    help='Log Levels')
PARSER.add_argument('-o', '--output',
                    action=ValidateOutputDir,
                    required=False,
                    dest='output',
                    default=DEFAULT_OUTPUT_PATH,
                    help='Output Location')


def list_required_arguments(parser: ArgumentParser):
    # Iterate through all arguments
    required_args = []
    for action in parser._actions:
        # Check if the argument is required
        if action.required:
            required_args.append(action.dest)
    return required_args


def argument_parser_has_required(parser: ArgumentParser):
    return bool(list_required_arguments(parser))


if __name__ == '__main__':
    if argument_parser_has_required(PARSER):
        args_parser = PARSER.parse_args(args=None if sys.argv[1:] else ['--help'])
    else:
        args_parser = PARSER.parse_args()
    logger.setLevel(LOGGING_LEVELS[args_parser.log_level])
    yml_config = YamlConfigurator()

    try:
        with open(args_parser.vpc_configuration, 'r') as f:
            config = yml_config.yaml.load(f)
        main(args_parser, config)
    except Exception as ex:
        logger.error(ex)
