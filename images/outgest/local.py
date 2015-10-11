"""Take care of local exports, to and from the main server"""

import logging, os, errno, mimetypes

from ..localfile import FileCopy
from ..export_job import GenericExportModule, register_export_module
from ..entry import FileDescriptor
from ..location import get_location_by_id
from ..types import first


class LocalExportModule(GenericExportModule):
    def run(self):
        self.verify_job()
        self.select_source()
        self.select_filename()

        if self.job_descriptor.metadata.longest_side is None:
            self.copy_source()
        else:
            raise NotImplemented("Conversion not implemented.")

    def verify_job(self):
        jd = self.job_descriptor
        assert jd is not None, "JobDescriptor not set"
        assert jd.entry is not None, "EntryDescriptor not set"
        assert jd.location is not None, "LocationDescriptor not set"
        assert jd.metadata is not None, "ExportJobMetadata not set"

    def select_source(self):
        jd = self.job_descriptor

        wants = first(jd.metadata.wants, jd.location.metadata.wants, FileDescriptor.Purpose.primary)
        if isinstance(wants, list):
            if 'primary' in wants:
                wants = FileDescriptor.Purpose.primary
            elif 'proxy' in wants:
                wants = FileDescriptor.Purpose.proxy
            elif 'thumb' in wants:
                wants = FileDescriptor.Purpose.thumb
            else:
                wants = FileDescriptor.Purpose.primary
        if isinstance(wants, str):
            wants = getattr(FileDescriptor.Purpose, wants)
        logging.info("Wants %s", FileDescriptor.Purpose(wants))

        candidates = [fd for fd in jd.entry.files if fd.purpose == wants]

        assert len(candidates) > 0, "No candidates of type %s found" % wants.name

        self.source = candidates.pop(0)
        self.source_location = get_location_by_id(self.source.location_id)
        logging.info("Exporting %i:%s", self.source.location_id, self.source.path)

    def select_filename(self):
        jd = self.job_descriptor

        filename = jd.metadata.path or jd.entry.export_filename or jd.entry.original_filename
        assert filename, "Could not determine a target filename"

        logging.info("Target filename may be %s", filename)

        (base, ext) = os.path.splitext(filename)
        if not ext:
            ext = mimetypes.guess_extension(self.source.mime)
            if ext:
                logging.info("Suggested extension is %s", ext)
                filename = base + ext

        self.filename = filename
        jd.metadata.path = filename
        logging.info("Target filename will be %s", filename)

    def copy_source(self):
        filecopy = FileCopy(self.source_location, self.source.path,
                            self.job_descriptor.location, self.filename,
                            keep_original=True, link=True)
        filecopy.run()
        filename = filecopy.destination_rel_path
        self.filename = filename
        self.job_descriptor.metadata.path = filename



register_export_module(None, LocalExportModule)
