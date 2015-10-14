########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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

import time

import fabric.contrib.files
import fabric.context_managers

from cloudify.workflows import local
from cloudify_cli import constants as cli_constants
# from system_tests import resources
# from cosmo_tester.framework.testenv import TestCase
# from cosmo_tester.test_suites.test_blueprints.hello_world_bash_test \
#     import AbstractHelloWorldTest
from hello_world_singlehost_test import HelloWorldSingleHostTest
# from cosmo_tester.framework.util import create_rest_client
from cloudify_rest_client.exceptions import CloudifyClientError


CLOUDIFY_AUTOMATION_TOKEN = 'CLOUDIFY_AUTOMATION_TOKEN'


class ExternalComponentsTests(HelloWorldSingleHostTest):

    def setUp(self):
        super(ExternalComponentsTests, self).setUp()
        blueprint_path = self.copy_blueprint('openstack-start-vm')
        self.blueprint_yaml = blueprint_path / 'blueprint.yaml'
        self.prefix = 'simple-host-{0}'.format(self.test_id)
        self.manager_blueprint_overrides = {}

        self.inputs = {
            'prefix': self.prefix,
            'external_network': self.env.external_network_name,
            'os_username': self.env.keystone_username,
            'os_password': self.env.keystone_password,
            'os_tenant_name': self.env.keystone_tenant_name,
            'os_region': self.env.region,
            'os_auth_url': self.env.keystone_url,
            'image_id': self.env.centos_7_image_name,
            'flavor': self.env.medium_flavor_id,
            'key_pair_path': '{0}/{1}-keypair.pem'.format(self.workdir,
                                                          self.prefix)
        }

        self.logger.info('initialize local env for running the '
                         'blueprint that starts a vm')
        self.local_env = local.init_env(
            self.blueprint_yaml,
            inputs=self.inputs,
            name=self._testMethodName,
            ignored_modules=cli_constants.IGNORED_LOCAL_WORKFLOW_MODULES)

        self.logger.info('starting vm to serve as the management vm')
        self.local_env.execute('install',
                               task_retries=10,
                               task_retry_interval=30)
        self.public_ip_address = \
            self.local_env.outputs()['simple_vm_public_ip_address']
        self.private_ip_address = \
            self.local_env.outputs()['simple_vm_private_ip_address']

        self.addCleanup(self.cleanup)

    def test_external_components(self):
        self.logger.info('Bootstrapping a manager')
        remote_manager_key_path = '/home/{0}/manager_key.pem'.format(
            self.env.centos_7_image_user)
        self.bootstrap_simple_manager_blueprint(remote_manager_key_path)

        # self.client = create_rest_client(self.cfy.get_management_ip())

        # self.logger.info('Copying manager private keypair into the manager '
        #                  'host')
        # with self.manager_env_fabric() as fabric_api:
        #     fabric_api.put(self.env.management_key_path,
        #                    '~/manager-kp.pem')

        # self.logger.info('Launching the watchdog')
        # self._launch_external_components_host()

        # self.logger.info('Testing the watchdog operation')
        # self._test_watchdog_operation()

        # self.logger.debug('Sleeping 15 seconds to allow elasticsearch'
        #                   'to fully start up before uninstalling...')
        # time.sleep(15)

        # self.logger.info('Uninstalling watchdog deployment')
        # self.execute_uninstall()

    def _launch_external_components_host(self):
        blueprint_path = self.copy_blueprint('external-components-vm')
        self.blueprint_yaml = \
            blueprint_path / 'external-components-blueprint.yaml'

        inputs = dict(
            image=self.env.centos_7_image_name,
            flavor=self.env.medium_flavor_id,
            agent_user='centos',
            manager_ip=self.cfy.get_management_ip(),
            manager_private_key_path='/tmp/home/manager-kp.pem')

        self.upload_deploy_and_execute_install(fetch_state=False,
                                               inputs=inputs,
                                               deployment_id=self.test_id)

        self.logger.info('Waiting for the watchdog to become active')
        self._wait_for_watchdog_to_be_active()

    def _test_watchdog_operation(self):
        self.logger.info('Verifying the manager is up with a status call')
        self.client.manager.get_status()

        self.logger.info('Disabling REST service on the manager')
        self._disable_rest_service_on_manager()

        self.logger.info('Ensuring REST service is down')
        self._ensure_rest_service_is_down()

        self.logger.info('Waiting for manager to recover')
        self._wait_for_manager()
        self.logger.info('Manager has recovered successfully')

    def _wait_for_manager(self, timeout=900):
        end = time.time() + timeout

        while time.time() <= end:
            try:
                self.client.deployments.list()
                return
            except (IOError, CloudifyClientError) as e:
                self.logger.debug(
                    'Manager has yet to recover - blueprints list call '
                    'returned an error: {0}'.format(str(e)))
                time.sleep(5)

        self.fail('Manager has not recovered in time; Waited for {0} seconds'
                  .format(timeout))

    def _ensure_rest_service_is_down(self):
        # attempting multiple calls to get_status again, expecting failures.
        # (multiple calls are to ensure REST is down, rather than a
        # connection error etc.)
        for _ in xrange(3):
            try:
                self.client.manager.get_status()
            except (IOError, CloudifyClientError):
                time.sleep(1)
            else:
                self.fail(
                    'Status call to manager checked out ok, despite having '
                    'disabled the REST service on the manager')

    def _wait_for_watchdog_to_be_active(self, timeout=900):
        end = time.time() + timeout

        fip_node_instance = \
            self.client.node_instances.list(
                deployment_id=self.test_id, node_name='watchdog_floatingip')[0]
        watchdog_host_ip = \
            fip_node_instance.runtime_properties['floating_ip_address']

        with fabric.context_managers.settings(
                host_string=watchdog_host_ip,
                user=self.env.management_user_name,
                key_filename=self.env.agent_key_path):

            while time.time() <= end:
                if fabric.contrib.files.exists(
                        '/tmp/test-workdir/.cloudify/bootstrap'):
                    return

                self.logger.info(
                    'Watchdog has yet to become active...')
                time.sleep(5)

        self.fail('Watchdog has not started in time; Waited for {0} seconds'
                  .format(timeout))

    def _disable_rest_service_on_manager(self):
        command = 'sudo docker kill cfy'
        with self.manager_env_fabric() as fabric_api:
            fabric_api.run(command)

    def _bootstrap(self, mb_path, inputs_path):
        self.cfy.bootstrap(blueprint_path=mb_path,
                           inputs_file=inputs_path,
                           task_retries=5,
                           install_plugins=self.env.install_plugins)
