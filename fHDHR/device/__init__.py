
import fHDHR.exceptions

from .channels import Channels
from .epg import EPG
from .tuners import Tuners
from .images import imageHandler
from .ssdp import SSDPServer


class fHDHR_Device():
    """
    The fHDHR devices.
    """

    def __init__(self, fhdhr, origins):
        self.fhdhr = fhdhr
        self.fhdhr.logger.debug("Setting Up internal \"Devices\".")

        self.channels = Channels(fhdhr, origins)

        self.epg = EPG(fhdhr, self.channels, origins)

        self.tuners = Tuners(fhdhr, self.epg, self.channels, origins)

        self.images = imageHandler(fhdhr, self.epg)

        self.ssdp = SSDPServer(fhdhr)

        self.interfaces = {}

        self.fhdhr.logger.info("Detecting and Opening any found Interface plugins.")
        for plugin_name in list(self.fhdhr.plugins.plugins.keys()):

            if self.fhdhr.plugins.plugins[plugin_name].manifest["type"] == "interface":
                method = self.fhdhr.plugins.plugins[plugin_name].name.lower()

                plugin_utils = self.fhdhr.plugins.plugins[plugin_name].plugin_utils
                plugin_utils.channels = self.channels
                plugin_utils.epg = self.epg
                plugin_utils.tuners = self.tuners
                plugin_utils.images = self.images
                plugin_utils.ssdp = self.ssdp
                plugin_utils.origins = self.fhdhr.origins

                try:

                    self.interfaces[method] = self.fhdhr.plugins.plugins[plugin_name].Plugin_OBJ(fhdhr, plugin_utils)

                except fHDHR.exceptions.INTERFACESetupError as e:
                    self.fhdhr.logger.error(e)

                except Exception as e:
                    self.fhdhr.logger.error(e)

    def run_interface_plugin_threads(self):

        self.fhdhr.logger.debug("Checking Interface Plugins for threads to run.")

        for interface_plugin in list(self.interfaces.keys()):

            if hasattr(self.interfaces[interface_plugin], 'run_thread'):
                self.fhdhr.logger.info("Starting %s interface plugin thread." % interface_plugin)
                self.interfaces[interface_plugin].run_thread()
                self.fhdhr.logger.debug("Started %s interface plugin thread." % interface_plugin)
