
import logging

_apis = {}
_local = {}


class UrlFactory(object):
    def __init__(self):
        self._functions = {}

    def __getattr__(self, attr):
        if attr == '_functions':
            return self.__getattribute__(attr)
        return self._functions.get(attr)

    def __iadd__(self, other):
        if not callable(other):
            raise TypeError("Value be a url-making function")
        logging.debug("Adding Url function %s.", other.__name__)
        self._functions[other.__name__] = other
        return self


class UrlCollection(object):
    def __init__(self):
        self._apis = {}

    def __getattr__(self, attr):
        if attr == '_apis':
            return self.__getattribute__(attr)
        try:
            url_factory = self._apis[attr]
            logging.debug("Got existing UrlFactory %s %s %s.", attr, str(url_factory), id(url_factory))
            return url_factory
        except KeyError:
            url_factory = UrlFactory()
            logging.debug("Adding UrlFactory %s %s %s.", attr , str(url_factory), id(url_factory))
            self._apis[attr] = url_factory
            return url_factory


_local['url'] = UrlCollection()
logging.debug("Creatied UrlCollection.")


def url():
    return _local['url']


def register(mount_point, app):
    if _local.get('locked') is True:
        raise Exception("API regitration is locked")
    if mount_point in _apis.keys():
        raise NameError("API already mounted on '%s'" % mount_point)

    _apis[mount_point] = app


def mount_all(root_app):
    _local['locked'] = True
    for mount_point, app in _apis.items():
        logging.info("Mounting app on '%s'", mount_point)
        root_app.mount(mount_point, app)
