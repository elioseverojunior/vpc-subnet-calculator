#!/usr/bin/env python3

import argparse
import logging
import os
import sys
from ipaddress import IPv4Network

from ruamel.yaml import YAML
from ruamel.yaml.representer import RoundTripRepresenter
from argparse import ArgumentParser, Action, ArgumentDefaultsHelpFormatter

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

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)


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
    description='%s Python Terraform to Templates' % __Company__,
    usage='''%(prog)s\n''',
    add_help=True,
    formatter_class=ExplicitDefaultsHelpFormatter)

PARSER.add_argument('-p', '--project-dir',
                    dest='project_dir',
                    required=True,
                    type=str,
                    help='Project Dir')

PARSER.add_argument('-c', '--configuration-repo-dir',
                    dest='config_repo_dir',
                    required=True,
                    type=str,
                    help='Configuration Repo Dir')

PARSER.add_argument('-e', '--environments',
                    dest='environments',
                    required=False,
                    default=['dev01-us'],
                    type=list,
                    help='Environment List')

PARSER.add_argument('--repository-configs',
                    dest='repository_configs',
                    required=False,
                    default=os.path.join(os.getcwd(), 'configs', 'repositories.yaml'),
                    type=str,
                    help='Repositories Configurations')

PARSER.add_argument('--cleanup',
                    dest='cleanup',
                    action='store_true',
                    default=False,
                    help='To Cleanup not required services')

PARSER.add_argument('--no-use-defaults',
                    dest='no_use_defaults',
                    action='store_true',
                    default=False,
                    help='To Not Use defaults')

PARSER.add_argument('--skip-if-regex-match',
                    dest='skip_if_regex_match',
                    type=str,
                    required=False,
                    default=None,
                    help='Skip if Regex Match')

PARSER.add_argument('--migrate-legacy-tfvars',
                    dest='migrate_legacy_tfvars',
                    action='store_true',
                    default=False,
                    required=False,
                    help='Migrate Legacy Terraform Vars Files')

PARSER.add_argument('--migrate-only',
                    dest='migrate_only',
                    nargs='+',
                    required=False,
                    default="*",
                    type=str,
                    help='Migrate only the listed environment or if regex match.\n'
                         'This Option will work only if --migrate-legacy-tfvars is used.')

PARSER.add_argument('--log-level',
                    dest='log_level',
                    choices=list(LOGGING_LEVELS.keys()),
                    default='info',
                    help='Log Levels')

PARSER.add_argument('-o', '--output',
                    action=ValidateOutPutDir,
                    dest='output',
                    default=os.path.join(os.getcwd(), 'outputs'),
                    help='Output Location')


def main():
    try:
        vpc_configuration = {
            'sharedtools': {
                'cidr': '100.100.0.0/16',
                'region': 'us-east-1',
                'azs': ['a', 'b', 'c'],
                'subnets': {
                    'public': 3,
                    'private': 3,
                    'lambda': 3,
                    'database': 2,
                    'elasticache': 2,
                },
            },
            'nickel': {
                'cidr': '100.101.0.0/16',
                'region': 'us-east-1',
                'azs': ['a', 'b'],
                'subnets': {
                    'public': 2,
                    'private': 2,
                    'lambda': 2,
                    'database': 2,
                    'elasticache': 2,
                    'redshift': 2,
                },
            },
            'snd': {
                'cidr': '100.102.0.0/16',
                'region': 'us-east-1',
                'azs': ['a', 'b', 'c'],
                'subnets': {
                    'public': 3,
                    'private': 3,
                    'lambda': 2,
                    'database': 2,
                    'elasticache': 2,
                    'redshift': 2,
                },
            },
            'dev': {
                'cidr': '100.103.0.0/16',
                'region': 'us-east-1',
                'azs': ['a', 'b', 'c'],
                'subnets': {
                    'public': 3,
                    'private': 3,
                    'lambda': 2,
                    'database': 2,
                    'elasticache': 2,
                    'redshift': 2,
                },
            },
            'sit': {
                'cidr': '100.104.0.0/16',
                'region': 'us-east-1',
                'azs': ['a', 'b', 'c'],
                'subnets': {
                    'public': 3,
                    'private': 3,
                    'lambda': 2,
                    'database': 2,
                    'elasticache': 2,
                    'redshift': 2,
                },
            },
            'perf': {
                'cidr': '100.105.0.0/16',
                'region': 'us-east-1',
                'azs': ['a', 'b', 'c'],
                'subnets': {
                    'public': 3,
                    'private': 3,
                    'lambda': 3,
                    'database': 2,
                    'elasticache': 2,
                    'redshift': 2,
                },
            },
            'pre': {
                'cidr': '100.106.0.0/16',
                'region': 'us-east-1',
                'azs': ['a', 'b', 'c'],
                'subnets': {
                    'public': 3,
                    'private': 3,
                    'lambda': 3,
                    'database': 2,
                    'elasticache': 2,
                    'redshift': 2,
                },
            },
            'prod': {
                'cidr': '100.107.0.0/16',
                'region': 'us-east-1',
                'azs': ['a', 'b', 'c'],
                'subnets': {
                    'public': 3,
                    'private': 3,
                    'lambda': 3,
                    'database': 2,
                    'elasticache': 2,
                    'redshift': 2,
                },
            },
        }

        write_to_yaml('./vpc_configuration.yaml', vpc_configuration)
        subnets_maps = {}
        for account, vpc_config in vpc_configuration.items():
            subnets_maps.update({
                account: {
                    'cidr': vpc_configuration[account]['cidr'],
                    'region': vpc_configuration[account]['region'],
                    'azs': vpc_configuration[account]['azs'],
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

        subnets_maps_normalized = {}
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
        write_to_yaml('./vpc_configuration_cidr_blocks.yaml', subnets_maps_normalized)
        print('\n\n')
    except Exception as ex:
        logger.error(ex)


if __name__ == '__main__':
    args = PARSER.parse_args(args=None if sys.argv[1:] else ['--help'])
    main()
