#!/usr/bin/env python3

import os
import tempfile
import unittest

from calculator import get_cidr_blocks, generate_cidr_blocks, parse_vpc_configuration, normalize_subnets, \
    YamlConfigurator


class TestVpcCidrBlocks(unittest.TestCase):

    def setUp(self):
        self.yaml_configurator = YamlConfigurator()
        self.cidr = '10.0.0.0/16'
        self.main_cidr_block_mask = 18
        self.subnet_mask = 24
        self.vpc_configuration = {
            'account1': {
                'cidr': '10.0.0.0/16',
                'region': 'us-east-1',
                'azs': ['a', 'b', 'c'],
                'subnets': {
                    'subnet1': 2,
                    'subnet2': 1
                }
            }
        }

    def test_get_cidr_blocks(self):
        cidr_blocks = get_cidr_blocks(self.cidr, self.main_cidr_block_mask, self.subnet_mask)
        self.assertGreater(len(cidr_blocks), 0)

    def test_generate_cidr_blocks(self):
        cidr_blocks = generate_cidr_blocks(self.cidr, 10)
        self.assertGreaterEqual(len(cidr_blocks), 10)

    def test_parse_vpc_configuration(self):
        parsed = parse_vpc_configuration(self.vpc_configuration)
        self.assertIsNotNone(parsed)
        self.assertIn('account1', parsed)
        self.assertIn('subnets', parsed['account1'])

    def test_normalize_subnets(self):
        parsed = parse_vpc_configuration(self.vpc_configuration)
        normalized = normalize_subnets(parsed)
        self.assertIsNotNone(normalized)
        self.assertIn('account1', normalized)
        self.assertIn('subnets', normalized['account1'])

    def test_yaml_dump(self):
        data = {'test': 'data'}
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            self.yaml_configurator.dump_to_file(tmp.name, data)
        with open(tmp.name, 'r') as tmp:
            read_data = tmp.read()
        os.remove(tmp.name)
        self.assertIn('test: data', read_data)


if __name__ == '__main__':
    unittest.main()