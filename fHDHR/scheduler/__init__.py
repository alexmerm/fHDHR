import functools
import threading
import schedule
import time

from fHDHR.tools import humanized_time


class Scheduler():
    """
    fHDHR Scheduling events system.
    """

    def __init__(self, settings, logger, db):
        self.config = settings
        self.logger = logger
        self.db = db

        self.schedule = schedule

    def fhdhr_self_add(self, fhdhr):
        self.fhdhr = fhdhr

    # This decorator can be applied to any job function
    def job_wrapper(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):

            job_name = func.__name__
            start_timestamp = time.time()

            self.logger.debug('Running job: %s' % job_name)

            result = func(*args, **kwargs)

            total_time = humanized_time(time.time() - start_timestamp)
            self.logger.debug('Job %s completed in %s' % (job_name, total_time))

            return result

        return wrapper

    def remove(self, remtag):
        joblist = self.jobs
        for job_item in joblist:
            if len(list(job_item.tags)):
                if remtag in list(job_item.tags):
                    self.schedule.cancel_job(job_item)

    def list_tags(self):
        tagslist = []
        joblist = self.jobs
        for job_item in joblist:
            if len(list(job_item.tags)):
                tagslist.extend(list(job_item.tags))
        return tagslist

    def list_jobs(self):
        jobsdicts = []
        joblist = self.jobs
        for job_item in joblist:
            if len(list(job_item.tags)):
                jobsdicts.append({
                    "name": list(job_item.tags)[0],
                    "last_run": job_item.last_run,
                    "next_run": job_item.next_run
                    })
        return jobsdicts

    def run_from_tag(self, runtag):
        joblist = self.jobs
        for job_item in joblist:
            if len(list(job_item.tags)):
                if runtag in list(job_item.tags):
                    self.logger.debug("Job %s was triggered to run." % list(job_item.tags)[0])
                    job_item.run()

    def run(self):
        """
        Run all scheduled tasks.
        """

        # Start a thread to run the events
        t = threading.Thread(target=self.thread_worker, args=())
        t.start()

    def thread_worker(self):
        while True:
            self.schedule.run_pending()
            time.sleep(1)

    def startup_tasks(self):
        self.fhdhr.logger.noob("Running Startup Tasks.")

        tags_list = self.list_tags()

        self.startup_versions_update(tags_list)

        self.startup_channel_scan(tags_list)

        self.startup_epg_update(tags_list)

        self.startup_ssdp_alive(tags_list)

        self.fhdhr.logger.noob("Startup Tasks Complete.")

        return "Success"

    def startup_epg_update(self, tags_list):

        for epg_method in self.fhdhr.device.epg.epg_methods:
            haseverpulled = self.db.get_fhdhr_value("epg", "update_time", epg_method)
            updateepg = False

            if hasattr(self.fhdhr.device.epg.epg_handling[epg_method]["class"], "epg_update_on_start"):
                updateepg = self.fhdhr.device.epg.epg_handling[epg_method]["class"].epg_update_on_start

            elif epg_method in list(self.config.dict.keys()):
                if "epg_update_on_start" in list(self.config.dict[epg_method].keys()):
                    updateepg = self.config.dict[epg_method]["epg_update_on_start"]
                else:
                    updateepg = self.config.dict["fhdhr"]["epg_update_on_start"]

            elif self.config.dict["epg"]["epg_update_on_start"]:
                updateepg = self.config.dict["epg"]["epg_update_on_start"]

            elif haseverpulled:
                updateepg = False

            if updateepg:
                if ("%s EPG Update" % epg_method) in tags_list:
                    self.fhdhr.scheduler.run_from_tag("%s EPG Update" % epg_method)

    def startup_channel_scan(self, tags_list):
        for origin in list(self.fhdhr.origins.origins_dict.keys()):

            haseverscanned = self.db.get_fhdhr_value("channels", "scanned_time", origin)
            updatechannels = False

            if hasattr(self.fhdhr.origins.origins_dict[origin], "chanscan_on_start"):
                updatechannels = self.fhdhr.origins.origins_dict[origin].chanscan_on_start

            elif origin in list(self.config.dict.keys()):
                if "chanscan_on_start" in list(self.config.dict[origin].keys()):
                    updatechannels = self.config.dict[origin]["chanscan_on_start"]
                else:
                    updatechannels = self.config.dict["fhdhr"]["chanscan_on_start"]

            elif self.config.dict["fhdhr"]["chanscan_on_start"]:
                updatechannels = self.config.dict["fhdhr"]["chanscan_on_start"]

            elif haseverscanned:
                updatechannels = False

            if updatechannels:
                if ("%s Channel Scan" % origin) in tags_list:
                    self.fhdhr.scheduler.run_from_tag("%s Channel Scan" % origin)

    def startup_versions_update(self, tags_list):
        if "Versions Update" in tags_list:
            self.fhdhr.scheduler.run_from_tag("Versions Update")

    def startup_ssdp_alive(self, tags_list):
        if "SSDP Alive" in tags_list:
            self.fhdhr.scheduler.run_from_tag("SSDP Alive")

    def __getattr__(self, name):
        """
        Quick and dirty shortcuts. Will only get called for undefined attributes.
        """

        if hasattr(self.schedule, name):
            return eval("self.schedule.%s" % name)
