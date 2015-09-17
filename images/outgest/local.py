"""Take care of local exports, to and from the main server"""

import logging, os, errno

from ..export_job import register_export_module
from ..entry import FileDescriptor


class LocalExportModule:
    def run(self):
        jd = self.job_descriptor
        assert jd is not None, "JobDescriptor not set"

        assert jd.entry is not None, "EntryDescriptor not set"
        assert jd.target is not None, "LocationDescriptor not set"

        wants = jd.metadata.wants or jd.target.metadata.wants or FileDescriptor.Purpose.primary

        candidates = [fd for fd in jd.entry.files if fd.purpose == wants]

        assert len(candidates) > 0, "No candidates of type %s found" % wants.name

        fd = candidates.pop(0)
        logging.info("Exporting %i:%s", fd.location_id, fd.path)




register_export_module(None, LocalExportModule)
