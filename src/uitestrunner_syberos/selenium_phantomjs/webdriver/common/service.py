# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import os
import platform
import subprocess
from subprocess import PIPE
import time
from . import utils

try:
    from subprocess import DEVNULL
    _HAS_NATIVE_DEVNULL = True
except ImportError:
    DEVNULL = -3
    _HAS_NATIVE_DEVNULL = False


class Service(object):

    def __init__(self, executable, port=0, log_file=DEVNULL, env=None, start_error_message=""):
        self.path = executable

        self.port = port
        if self.port == 0:
            self.port = utils.free_port()

        if not _HAS_NATIVE_DEVNULL and log_file == DEVNULL:
            log_file = open(os.devnull, 'wb')

        self.start_error_message = start_error_message
        self.log_file = log_file
        self.env = env or os.environ

    @property
    def service_url(self):
        """
        Gets the url of the Service
        """
        return "http://%s" % utils.join_host_port('localhost', self.port)

    def command_line_args(self):
        raise NotImplemented("This method needs to be implemented in a sub class")

    def start(self):
        """
        Starts the Service.

        :Exceptions:
         - WebDriverException : Raised either when it can't start the service
           or when it can't connect to the service
        """
        cmd = [self.path]
        cmd.extend(self.command_line_args())
        subprocess.Popen(cmd, env=self.env,
                         close_fds=platform.system() != 'Windows',
                         stdout=self.log_file,
                         stderr=self.log_file,
                         stdin=PIPE)
        while True:
            self.assert_process_still_running()
            if self.is_connectable():
                break
            time.sleep(1)
