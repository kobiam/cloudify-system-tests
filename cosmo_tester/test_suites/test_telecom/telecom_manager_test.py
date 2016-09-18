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
import os

from cosmo_tester.framework import util
from cosmo_tester.framework.testenv import TestCase
from path import path

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import urllib
import tarfile

import logging
import cloudify.utils

for logger_name in ('sh', 'pika', 'requests.packages.urllib3.connectionpool'):
    cloudify.utils.setup_logger(logger_name, logging.WARNING)

PHANTOMJS_FILE_NAME = 'phantomjs-2.1.1-linux-x86_64'


class TelecomManagerTests(TestCase):
    def test_bootstrap_telecom_manager(self):
        self._copy_manager_blueprint()
        self._update_manager_blueprint()
        self._bootstrap()
        self._verify_manager_edition()

    def _copy_manager_blueprint(self):
        inputs_path, mb_path = util.generate_unique_configurations(
            workdir=self.workdir,
            original_inputs_path=self.env.cloudify_config_path,
            original_manager_blueprint_path=self.env._manager_blueprint_path)
        self.test_manager_blueprint_path = path(mb_path)
        self.test_inputs_path = path(inputs_path)

    def _update_manager_blueprint(self):
        with util.YamlPatcher(self.test_inputs_path) as patch:
            patch.set_value('telecom_edition', 'true')

    def _bootstrap(self):
        self.cfy.bootstrap(self.test_manager_blueprint_path,
                           inputs=self.test_inputs_path,
                           task_retries=5,
                           install_plugins=self.env.install_plugins)
        self.addCleanup(self.cfy.teardown, force=True)

    def _verify_manager_edition(self):
        urllib.urlretrieve(
            'https://bitbucket.org/ariya/phantomjs/downloads/'
            + PHANTOMJS_FILE_NAME
            + '.tar.bz2',
            PHANTOMJS_FILE_NAME + '.tar.bz2')

        tar = tarfile.open(PHANTOMJS_FILE_NAME + '.tar.bz2', 'r:bz2')
        tar.extractall()
        tar.close()

        exec_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            PHANTOMJS_FILE_NAME + '/bin/phantomjs'))
        driver = webdriver.PhantomJS(executable_path=exec_path)
        self.logger.info('Verifying manager edition...')

        try:
            driver.get('http://' + self.get_manager_ip())
        except Exception:
            self.logger.info('Failed to get manager ip.')

        try:
            edition = driver.find_element_by_class_name(
                'ui-variation-brand').text
        except NoSuchElementException:
            self.logger.info('Telecom Edition UI element not found.')

        self.assertEqual(edition, 'Telecom Edition',
                         'The manager is not Telecom Edition')
        self.logger.info('Test passed. The manager is Telecom Edition.')
        driver.close()
