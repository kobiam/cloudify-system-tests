########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

"""
Assumes Windows image with WinRM and python.
"""


from cosmo_tester.framework.testenv import TestCase
from cosmo_tester.framework.util import YamlPatcher


class WindowsAgentTest(TestCase):

    def test_windows(self):

        blueprint_path = self.copy_blueprint('windows')
        self.blueprint_yaml = blueprint_path / 'blueprint.yaml'
        with YamlPatcher(self.blueprint_yaml) as patch:
            patch.set_value('node_templates.vm.properties.server.image_name',
                            self.env.windows_image_name)

        self.blueprint_yaml = blueprint_path / 'existing-blueprint.yaml'
        self.upload_deploy_and_execute_install()
        outputs = self.client.deployments.outputs.get(self.test_id)['outputs']
        self.assertEqual('create1_value', outputs['create1_key'])
        self.assertEqual('configure1_value', outputs['configure1_key'])
        self.assertEqual('start1_value', outputs['start1_key'])
        self.assertEqual('create2_value', outputs['create2_key'])
        self.execute_uninstall()
