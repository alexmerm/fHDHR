import threading
import datetime

from fHDHR.exceptions import TunerError
from fHDHR.tools import humanized_time

from .stream import Stream


class Tuner():
    """
    fHDHR Tuner Object.
    """

    def __init__(self, fhdhr, inum, epg, origin):
        self.fhdhr = fhdhr

        self.number = inum
        self.origin = origin
        self.epg = epg

        self.tuner_lock = threading.Lock()
        self.set_off_status()

        self.chanscan_url = "/api/channels?method=scan"
        self.close_url = "/api/tuners?method=close&tuner=%s&origin=%s" % (self.number, self.origin)
        self.start_url = "/api/tuners?method=start&tuner=%s&origin=%s" % (self.number, self.origin)

    def channel_scan(self, origin, grabbed=False):
        """
        Use tuner to scan channels.
        """

        if self.tuner_lock.locked() and not grabbed:
            self.fhdhr.logger.error("%s Tuner #%s is not available." % (self.origin, self.number))
            raise TunerError("804 - Tuner In Use")

        if self.status["status"] == "Scanning":
            self.fhdhr.logger.info("Channel Scan Already In Progress!")

        else:

            if not grabbed:
                self.tuner_lock.acquire()

            self.status["status"] = "Scanning"
            self.status["origin"] = origin
            self.status["time_start"] = datetime.datetime.utcnow()
            self.fhdhr.logger.info("Tuner #%s Performing Channel Scan for %s origin." % (self.number, origin))

            chanscan = threading.Thread(target=self.runscan, args=(origin,))
            chanscan.start()

    def runscan(self, origin):
        """
        Use a threaded API call to scan channels.
        """

        self.fhdhr.api.get("%s&origin=%s" % (self.chanscan_url, origin))
        self.fhdhr.logger.info("Requested Channel Scan for %s origin Complete." % origin)
        self.close()
        self.fhdhr.api.threadget(self.close_url)

    def add_downloaded_size(self, bytes_count, chunks_count):
        """
        Append size of total downloaded size and count.
        """

        if "downloaded_size" in list(self.status.keys()):
            self.status["downloaded_size"] += bytes_count
        else:
            self.status["downloaded_size"] = bytes_count

        self.status["downloaded_chunks"] = chunks_count

    def add_served_size(self, bytes_count, chunks_count):
        """
        Append Served size and count.
        """

        if "served_size" in list(self.status.keys()):
            self.status["served_size"] += bytes_count
        else:
            self.status["served_size"] = bytes_count

        self.status["served_chunks"] = chunks_count

    def grab(self, origin, channel_number):
        """
        Grab Tuner.
        """

        if self.tuner_lock.locked():
            self.fhdhr.logger.error("Tuner #%s is not available." % self.number)
            raise TunerError("804 - Tuner In Use")

        self.tuner_lock.acquire()
        self.status["status"] = "Acquired"
        self.status["origin"] = origin
        self.status["channel"] = channel_number
        self.status["time_start"] = datetime.datetime.utcnow()
        self.fhdhr.logger.info("Tuner #%s Acquired." % str(self.number))

    def close(self):
        """
        Close Tuner.
        """

        self.set_off_status()

        if self.tuner_lock.locked():
            self.tuner_lock.release()
            self.fhdhr.logger.info("Tuner #%s Released." % self.number)

    def get_status(self):
        """
        Get Tuner Status.
        """

        current_status = self.status.copy()
        current_status["epg"] = {}

        if current_status["status"] in ["Acquired", "Active", "Scanning"]:
            current_status["running_time"] = str(
                humanized_time(
                    int((datetime.datetime.utcnow() - current_status["time_start"]).total_seconds())))
            current_status["time_start"] = str(current_status["time_start"])

        if current_status["status"] in ["Active"]:

            if current_status["origin"] in self.epg.epg_methods:
                current_status["epg"] = self.epg.whats_on_now(current_status["channel"], method=current_status["origin"])

        return current_status

    def set_off_status(self):
        """
        Set Off Status.
        """

        self.stream = None
        self.status = {"status": "Inactive"}

    def setup_stream(self, stream_args, tuner):
        """Setup Stream."""

        self.stream = Stream(self.fhdhr, stream_args, tuner)

    def set_status(self, stream_args):
        """
        Set Tuner Status.
        """

        if self.status["status"] != "Active":
            self.status = {
                            "status": "Active",
                            "clients": [],
                            "clients_id": [],
                            "method": stream_args["method"],
                            "accessed": [stream_args["accessed"]],
                            "origin": stream_args["origin"],
                            "channel": stream_args["channel"],
                            "proxied_url": stream_args["stream_info"]["url"],
                            "time_start": datetime.datetime.utcnow(),
                            "downloaded_size": 0,
                            "downloaded_chunks": 0,
                            "served_size": 0,
                            "served_chunks": 0
                            }

        if stream_args["client"] not in self.status["clients"]:
            self.status["clients"].append(stream_args["client"])

        if stream_args["client_id"] not in self.status["clients_id"]:
            self.status["clients_id"].append(stream_args["client_id"])
