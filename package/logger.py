import logging, re, threading
from logging.handlers import TimedRotatingFileHandler


class MyLogger(logging.Logger):

    def __init__(self, name, level = logging.NOTSET):
        self._wcount = 0
        self._ecount = 0
        self._wcountLock = threading.Lock()   
        self._ecountLock = threading.Lock()       

        return super(MyLogger, self).__init__(name, level)        

    @property
    def warningCount(self):
        return self._wcount
    @property
    def errorCount(self):
        return self._ecount

    def warning(self, msg, *args, **kwargs):
        self._wcountLock.acquire()
        self._wcount += 1
        self._wcountLock.release()

        return super(MyLogger, self).warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._ecountLock.acquire()
        self._ecount += 1
        self._ecountLock.release()

        return super(MyLogger, self).warning(msg, *args, **kwargs)


def getLogger(name="cl_evaluator", file_name='cl_log'):
    # create logger with 'cl_evaluator'
    logging.setLoggerClass(MyLogger)
    logging.basicConfig()
    logger = logging.getLogger(name)
    handler = TimedRotatingFileHandler(file_name, when="midnight", interval=1)
    handler.setLevel(logging.DEBUG)
    handler.suffix = "%Y%m%d.log"
    formatter = logging.Formatter('[%(asctime)s]: %(levelname)-8s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

mylog = getLogger()
def cmLog(msg):
    splitted = re.compile('\[([DIWECO])\] ?').split(msg)
    try:
        level = splitted[1]
        msg = splitted[2]
        if level == 'D':
            mylog.debug(msg)
        elif level == 'I':
            mylog.info(msg)
        elif level == 'W':
            mylog.warning(msg)
        elif level == 'E':
            mylog.error(msg)
        elif level == 'C':
            mylog.critical(msg)
        else:
            print('[O] unhandlered message:', msg)
    except:
        print('[O] unhandlered message:', msg)
