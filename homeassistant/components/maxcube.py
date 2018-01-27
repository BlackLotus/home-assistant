"""
Platform for the MAX! Cube LAN Gateway.

For more details about this component, please refer to the documentation
https://home-assistant.io/components/maxcube/
"""
import logging
import time
from socket import timeout
from threading import Lock

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import load_platform
from homeassistant.const import CONF_HOST, CONF_PORT

REQUIREMENTS = ['maxcube-api==0.1.0']

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 62910
CONF_DISCOVERY = 'discovery'
DEFAULT_DISCOVERY = False
DOMAIN = 'maxcube'

MAXCUBE_HANDLE = 'maxcube'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_DISCOVERY, default=DEFAULT_DISCOVERY): cv.boolean,
    }),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Establish connection to MAX! Cube."""
    from maxcube.connection import MaxCubeConnection
    from maxcube.cube import MaxCube
    from maxcube.discovery import discover_cube

    discovery = config.get(DOMAIN).get('discovery', DEFAULT_DISCOVERY)
    if discovery:
        discoverd_host = discover_cube()
    host = config.get(DOMAIN).get(CONF_HOST)
    port = config.get(DOMAIN).get(CONF_PORT)

    try:
        cube = MaxCube(MaxCubeConnection(discovered_host, port))
    except timeout:
        try:
            cube = MaxCube(MaxCubeConnection(host, port))
        except timeout:
            _LOGGER.error("Connection to Max!Cube could not be established")
            cube = None
            return False

    hass.data[MAXCUBE_HANDLE] = MaxCubeHandle(cube)

    load_platform(hass, 'climate', DOMAIN)
    load_platform(hass, 'binary_sensor', DOMAIN)

    return True


class MaxCubeHandle(object):
    """Keep the cube instance in one place and centralize the update."""

    def __init__(self, cube):
        """Initialize the Cube Handle."""
        self.cube = cube
        self.mutex = Lock()
        self._updatets = time.time()

    def update(self):
        """Pull the latest data from the MAX! Cube."""
        # Acquire mutex to prevent simultaneous update from multiple threads
        with self.mutex:
            # Only update every 60s
            if (time.time() - self._updatets) >= 60:
                _LOGGER.debug("Updating")

                try:
                    self.cube.update()
                except timeout:
                    _LOGGER.error("Max!Cube connection failed")
                    return False

                self._updatets = time.time()
            else:
                _LOGGER.debug("Skipping update")
