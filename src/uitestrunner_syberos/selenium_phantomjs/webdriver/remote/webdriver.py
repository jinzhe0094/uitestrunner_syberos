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

"""The WebDriver implementation."""

import copy

from .command import Command
from .remote_connection import RemoteConnection

try:
    str = basestring
except NameError:
    pass


_W3C_CAPABILITY_NAMES = frozenset([
    'acceptInsecureCerts',
    'browserName',
    'browserVersion',
    'platformName',
    'pageLoadStrategy',
    'proxy',
    'setWindowRect',
    'timeouts',
    'unhandledPromptBehavior',
])

_OSS_W3C_CONVERSION = {
    'acceptSslCerts': 'acceptInsecureCerts',
    'version': 'browserVersion',
    'platform': 'platformName'
}


def _make_w3c_caps(caps):
    """Makes a W3C alwaysMatch capabilities object.

    Filters out capability names that are not in the W3C spec. Spec-compliant
    drivers will reject requests containing unknown capability names.

    Moves the Firefox profile, if present, from the old location to the new Firefox
    options object.

    :Args:
     - caps - A dictionary of capabilities requested by the caller.
    """
    caps = copy.deepcopy(caps)
    profile = caps.get('firefox_profile')
    always_match = {}
    if caps.get('proxy') and caps['proxy'].get('proxyType'):
        caps['proxy']['proxyType'] = caps['proxy']['proxyType'].lower()
    for k, v in caps.items():
        if v and k in _OSS_W3C_CONVERSION:
            always_match[_OSS_W3C_CONVERSION[k]] = v.lower() if k == 'platform' else v
        if k in _W3C_CAPABILITY_NAMES or ':' in k:
            always_match[k] = v
    if profile:
        moz_opts = always_match.get('moz:firefoxOptions', {})
        # If it's already present, assume the caller did that intentionally.
        if 'profile' not in moz_opts:
            # Don't mutate the original capabilities.
            new_opts = copy.deepcopy(moz_opts)
            new_opts['profile'] = profile
            always_match['moz:firefoxOptions'] = new_opts
    return {"firstMatch": [{}], "alwaysMatch": always_match}


class WebDriver(object):
    """
    Controls a browser by sending commands to a remote server.
    This server is expected to be running the WebDriver wire protocol
    as defined at
    https://github.com/SeleniumHQ/selenium/wiki/JsonWireProtocol

    :Attributes:
     - session_id - String ID of the browser session started and controlled by this WebDriver.
     - capabilities - Dictionaty of effective capabilities of this browser session as returned
         by the remote server. See https://github.com/SeleniumHQ/selenium/wiki/DesiredCapabilities
     - command_executor - remote_connection.RemoteConnection object used to execute commands.
    """

    def __init__(self, command_executor='http://127.0.0.1:4444/wd/hub',
                 desired_capabilities=None, browser_profile=None,
                 keep_alive=False, options=None):
        """
        Create a new driver that will issue commands using the wire protocol.

        :Args:
         - command_executor - Either a string representing URL of the remote server or a custom
             remote_connection.RemoteConnection object. Defaults to 'http://127.0.0.1:4444/wd/hub'.
         - desired_capabilities - A dictionary of capabilities to request when
             starting the browser session. Required parameter.
         - browser_profile - A selenium.webdriver.firefox.firefox_profile.FirefoxProfile object.
             Only used if Firefox is requested. Optional.
         - keep_alive - Whether to configure remote_connection.RemoteConnection to use
             HTTP keep-alive. Defaults to False.
         - options - instance of a driver options.Options class
        """
        capabilities = {}
        if options is not None:
            capabilities = options.to_capabilities()
        if desired_capabilities is not None:
            capabilities.update(desired_capabilities)
        self.command_executor = command_executor
        if type(self.command_executor) is bytes or isinstance(self.command_executor, str):
            self.command_executor = RemoteConnection(command_executor, keep_alive=keep_alive)
        self._is_remote = True
        self.session_id = None
        self.capabilities = {}
        self.start_client()
        self.start_session(capabilities, browser_profile)

    def __repr__(self):
        return '<{0.__module__}.{0.__name__} (session="{1}")>'.format(
            type(self), self.session_id)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.quit()

    def start_client(self):
        """
        Called before starting a new session. This method may be overridden
        to define custom startup behavior.
        """
        pass

    def start_session(self, capabilities, browser_profile=None):
        """
        Creates a new session with the desired capabilities.

        :Args:
         - browser_name - The name of the browser to request.
         - version - Which browser version to request.
         - platform - Which platform to request the browser on.
         - javascript_enabled - Whether the new session should support JavaScript.
         - browser_profile - A selenium.webdriver.firefox.firefox_profile.FirefoxProfile object. Only used if Firefox is requested.
        """
        if browser_profile:
            if "moz:firefoxOptions" in capabilities:
                capabilities["moz:firefoxOptions"]["profile"] = browser_profile.encoded
            else:
                capabilities.update({'firefox_profile': browser_profile.encoded})
        w3c_caps = _make_w3c_caps(capabilities)
        parameters = {"capabilities": w3c_caps,
                      "desiredCapabilities": capabilities}
        response = self.execute(Command.NEW_SESSION, parameters)
        if 'sessionId' not in response:
            response = response['value']
        self.session_id = response['sessionId']
        self.capabilities = response.get('value')

        # if capabilities is none we are probably speaking to
        # a W3C endpoint
        if self.capabilities is None:
            self.capabilities = response.get('capabilities')

        # Double check to see if we have a W3C Compliant browser
        self.w3c = response.get('status') is None
        self.command_executor.w3c = self.w3c

    def execute(self, driver_command, params=None):
        """
        Sends a command to be executed by a command.CommandExecutor.

        :Args:
         - driver_command: The name of the command to execute as a string.
         - params: A dictionary of named parameters to send with the command.

        :Returns:
          The command's JSON response loaded into a dictionary object.
        """
        if self.session_id is not None:
            if not params:
                params = {'sessionId': self.session_id}
            elif 'sessionId' not in params:
                params['sessionId'] = self.session_id

        response = self.command_executor.execute(driver_command, params)
        if response:
            return response
        # If the server doesn't send a response, assume the command was
        # a success
        return {'success': 0, 'value': None, 'sessionId': self.session_id}

    def get(self, url):
        """
        Loads a web page in the current browser session.
        """
        self.execute(Command.GET, {'url': url})
        self.execute(Command.REFRESH)

    @property
    def page_source(self):
        """
        Gets the source of the current page.

        :Usage:
            driver.page_source
        """
        return self.execute(Command.GET_PAGE_SOURCE)['value']

    @property
    def desired_capabilities(self):
        """
        returns the drivers current desired capabilities being used
        """
        return self.capabilities

    def get_screenshot_as_base64(self):
        """
        Gets the screenshot of the current window as a base64 encoded string
           which is useful in embedded images in HTML.

        :Usage:
            driver.get_screenshot_as_base64()
        """
        return self.execute(Command.SCREENSHOT)['value']
