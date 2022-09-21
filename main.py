# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    main.py                                            :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: elio.severo <elio.severo@nutrien.com>      +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2022/09/19 18:56:10 by elio.severo       #+#    #+#              #
#    Updated: 2022/09/19 19:20:29 by elio.severo      ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

#!/usr/bin/env python3

import argparse
import logging
import os
import sys
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from ipaddress import IPv4Network

from ruamel.yaml import YAML
from ruamel.yaml.representer import RoundTripRepresenter
from enum import Enum
from dataclasses import dataclass
from typing import Any, List, Optional, TypeVar, Callable, Type, cast

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

# To use this code, make sure you
#
#     import json
#
# and then, to convert JSON from a string, do
#
#     result = cidr_block_configurations_from_dict(json.loads(json_string))


T = TypeVar("T")
EnumT = TypeVar("EnumT", bound=Enum)


def from_int(x: Any) -> int:
    assert isinstance(x, int) and not isinstance(x, bool)
    return x


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


def from_none(x: Any) -> Any:
    assert x is None
    return x


def from_union(fs, x):
    for f in fs:
        try:
            return f(x)
        except Exception as ex:
            logger.error(ex)
            pass
    assert False


def to_enum(c: Type[EnumT], x: Any) -> EnumT:
    assert isinstance(x, c)
    return x.value


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


class Az(Enum):
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    E = "e"
    F = "f"


@dataclass
class Subnets:
    private: int
    subnets_lambda: int
    database: int

    @staticmethod
    def from_dict(obj: Any) -> 'Subnets':
        assert isinstance(obj, dict)
        private = from_int(obj.get("private"))
        subnets_lambda = from_int(obj.get("lambda"))
        database = from_int(obj.get("database"))
        return Subnets(private, subnets_lambda, database)

    def to_dict(self) -> dict:
        result: dict = {"private": from_int(self.private), "lambda": from_int(self.subnets_lambda),
                        "database": from_int(self.database)}
        return result


@dataclass
class CIDRBlockConfiguration:
    environment: str
    cidr: str
    region: str
    azs: List[Az]
    subnets: Subnets
    subnet_bits: Optional[int] = None

    @staticmethod
    def from_dict(obj: Any) -> 'CIDRBlockConfiguration':
        assert isinstance(obj, dict)
        environment = from_str(obj.get("environment"))
        cidr = from_str(obj.get("cidr"))
        region = from_str(obj.get("region"))
        azs = from_list(Az, obj.get("azs"))
        subnets = Subnets.from_dict(obj.get("subnets"))
        subnet_bits = from_union([from_int, from_none], obj.get("subnet_bits"))
        return CIDRBlockConfiguration(environment, cidr, region, azs, subnets, subnet_bits)

    def to_dict(self) -> dict:
        result: dict = {"environment": from_str(self.environment), "cidr": from_str(self.cidr),
                        "region": from_str(self.region), "azs": from_list(lambda x: to_enum(Az, x), self.azs),
                        "subnets": to_class(Subnets, self.subnets),
                        "subnet_bits": from_union([from_int, from_none], self.subnet_bits)}
        return result


def cidr_block_configurations_from_dict(s: Any) -> List[CIDRBlockConfiguration]:
    return from_list(CIDRBlockConfiguration.from_dict, s)


def cidr_block_configurations_to_dict(x: List[CIDRBlockConfiguration]) -> Any:
    return from_list(lambda x: to_class(CIDRBlockConfiguration, x), x)


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

PARSER.add_argument('--vpc-configuration-array',
                    dest='array_vpc_configuration',
                    required=False,
                    default=os.path.join(os.getcwd(), 'array_vpc_configuration.yaml'),
                    type=str,
                    help='AWS VPC Configurations')

PARSER.add_argument('-l', '--log-level',
                    dest='log_level',
                    required=False,
                    choices=list(LOGGING_LEVELS.keys()),
                    default='info',
                    help='Log Levels')

PARSER.add_argument('-o', '--output',
                    action=ValidateOutPutDir,
                    required=False,
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
            logger.error(account)
            logger.error(vpc_config)
            subnet_bits = vpc_configuration[account]['subnet_bits'] if vpc_configuration[account]['subnet_bits'] is not None else vpc_configuration[account]['cidr'].split('/')[-1]
            subnets_maps.update({
                account: {
                    'cidr': vpc_configuration[account]['cidr'],
                    'subnet_bits': vpc_configuration[account]['subnet_bits'] if vpc_configuration[account]['subnet_bits'] is not None else vpc_configuration[account]['cidr'].split('/')[:-1],
                    'region': vpc_configuration[account]['region'],
                    'azs': ["{}{}".format(vpc_configuration[account]['region'], az) for az in
                            vpc_configuration[account]['azs']],
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
                                               total_subnets_needed=vpc_config['total_subnets']) #, subnet_bits=subnet_bits)
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

    with open(args_parser.array_vpc_configuration, 'r') as f:
        array_config = yml.load(f)
        logger.debug(array_config)

    # result = cidr_block_configurations_from_dict(array_config)

    main(args_parser, config)
