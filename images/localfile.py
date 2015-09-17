"""Helper classes for dealing with local file operations."""


import os, errno, logging


################################################################################
# Standard File Copyer Class


class FileCopy(object):
    """
    File Copier for local file operations. Handles copying, linking and overwrite protection.

    Args:
        source (.location.LocationDescriptor): The `Location` to copy from.
            May be `None` if `source_path` is absolute.
        source_path (str): The relative path to copy from.
        destination (.location.LocationDescriptor): The `Location` to copy to. Required.
        destination_filename (str): The wanted filename to use on the destionation.
        link (Optional[boo]): Try hard-linking before copying. Defaults to `False`.
        keep_original (Optional[bool]): Keep source file, as opposed to deleting it when done.
            Defaults to whatever the source `Location.metadata.keep_original` is.
        dest_folder (str): Relative destination folder. 
            If not given, let destionation `Location` decide.

    Attributes:
        destination_rel_path (str): After run, contains the relative path of the destination
            (from destination `Location` root).
        destination_full_path (str): After run, contains the full path of the destination.
        link (bool): Will be set to False if linking failed due to cross-device error.
    """
    def __init__(self, source, source_path, destination, dest_filename, link=False, keep_original=None, dest_folder=None):
        self.source = source
        if source and source.metadata and keep_original is None:
            self.keep_original = source.metadata.keep_original
        elif keep_original is None:
            self.keep_original = True
        else:
            self.keep_original = keep_original
        self.source_path = source_path
        self.destination = destination
        self.link = link
        self.dest_filename = dest_filename
        self.dest_folder = dest_folder
        self.destination_rel_path = None
        self.destination_full_path = None

    def run(self):
        if self.source:
            src = os.path.join(self.source.get_root(), self.source_path)
        else:
            src = self.source_path
        dst_folder = self.dest_folder or self.destination.suggest_folder()
        dst = os.path.join(dst_folder, self.dest_filename)
        try:
            os.makedirs(dst_folder)
        except FileExistsError as e:
            pass
        c = 0
        while True:
            try:
                if c:
                    postfix = '%i_' % c
                    dst_path, dst_ext = os.path.splitext(dst)
                    fixed_dst = ''.join([dst_path, '_%i' % c, dst_ext])
                else:
                    fixed_dst = dst
                if self.link:
                    logging.debug("Linking %s -> %s", src, fixed_dst)
                    os.link(src, fixed_dst)
                    self.destination_rel_path = os.path.relpath(fixed_dst, self.destination.get_root())
                    self.destination_full_path = fixed_dst
                else:
                    import shutil
                    logging.debug("Copying %s -> %s", src, fixed_dst)
                    shutil.copyfile(src, fixed_dst)
                    self.destination_rel_path = os.path.relpath(fixed_dst, self.destination.get_root())
                    self.destination_full_path = fixed_dst
                break
            except FileExistsError:
                c += 1
            except OSError as e:
                if e.errno == errno.EXDEV:
                    logging.debug("Cross-device link %s -> %s", src, fixed_dst)
                    self.link = False
                else:
                    logging.debug("OSError %i %s -> %s (%s)", e.errno, src, fixed_dst, str(e))
                    raise e
                    

        if not self.keep_original:
            logging.debug("Removing original %s", src)
            os.remove(src)
