#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json
import time

from oslo_config import cfg

from tacker.tests import constants
from tacker.tests.functional import base
from tacker.tests.utils import read_file


CONF = cfg.CONF


class VnfTestToscaScale(base.BaseTackerTest):
    def test_vnf_tosca_scale(self):
        data = dict()
        data['tosca'] = read_file('sample-tosca-scale-all.yaml')
        vnfd_name = 'test_tosca_vnf_scale_all'
        toscal = data['tosca']
        tosca_arg = {'vnfd': {'name': vnfd_name,
                              'attributes': {'vnfd': toscal}}}

        # Create vnfd with tosca template
        vnfd_instance = self.client.create_vnfd(body=tosca_arg)
        self.assertIsNotNone(vnfd_instance)

        # Create vnf with vnfd_id
        vnfd_id = vnfd_instance['vnfd']['id']
        vnf_name = 'test_tosca_vnf_scale_all'
        vnf_arg = {'vnf': {'vnfd_id': vnfd_id, 'name': vnf_name}}
        vnf_instance = self.client.create_vnf(body=vnf_arg)

        self.validate_vnf_instance(vnfd_instance, vnf_instance)

        vnf_id = vnf_instance['vnf']['id']

        # TODO(kanagaraj-manickam) once load-balancer support is enabled,
        # update this logic to validate the scaling
        def _wait(count):
            self.wait_until_vnf_active(
                vnf_id,
                constants.VNF_CIRROS_CREATE_TIMEOUT,
                constants.ACTIVE_SLEEP_TIME)
            vnf = self.client.show_vnf(vnf_id)['vnf']

            # {"VDU1": ["10.0.0.14", "10.0.0.5"]}
            self.assertEqual(count, len(json.loads(vnf['mgmt_url'])['VDU1']))

        _wait(2)

        def _scale(type, count):
            body = {"scale": {'type': type, 'policy': 'SP1'}}
            self.client.scale_vnf(vnf_id, body)
            _wait(count)

        # scale out
        time.sleep(constants.SCALE_WINDOW_SLEEP_TIME)
        _scale('out', 3)

        # scale in
        time.sleep(constants.SCALE_WINDOW_SLEEP_TIME)
        _scale('in', 2)

        # Delete vnf_instance with vnf_id
        try:
            self.client.delete_vnf(vnf_id)
        except Exception:
            assert False, "vnf Delete failed"

        # Delete vnfd_instance
        self.addCleanup(self.client.delete_vnfd, vnfd_id)
        self.addCleanup(self.wait_until_vnf_delete, vnf_id,
            constants.VNF_CIRROS_DELETE_TIMEOUT)