########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.


from nose.tools import nottest

from test_cli_package import TestCliPackage
from test_offline_cli_package import TestOfflineCliPackage
from centos_base import Centos65Base


class Centos65Bootstrap(Centos65Base, TestCliPackage):

    def test_centos6_5_cli_package(self):
        self._add_dns()
        self._test_cli_package()


class Centos65OfflineBootstrap(Centos65Base, TestOfflineCliPackage):

    @nottest
    def test_offline_centos6_5_cli_package(self):
        self._test_cli_package()
