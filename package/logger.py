import logging, re, threading
from logging.handlers import TimedRotatingFileHandler

debug = True
# debug = False

class CMLogger(logging.Logger):
    def __init__(self, name, level = logging.DEBUG):
        self._wcount = 0
        self._ecount = 0
        self._wcountLock = threading.Lock()   
        self._ecountLock = threading.Lock()       
        return super().__init__(name, level)        

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

        return super().warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._ecountLock.acquire()
        self._ecount += 1
        self._ecountLock.release()

        return super().error(msg, *args, **kwargs)


loggers = {}
def getLogger(name="cl_evaluator", file_name='cloudmile_log', level=logging.DEBUG):
    global loggers
    if loggers.get(name):
        return loggers.get(name)
    else:
        # create logger with 'cl_evaluator'
        logging.setLoggerClass(CMLogger)
        logger = logging.getLogger(name)
        formatter = logging.Formatter('[%(asctime)s]: %(levelname)-8s: %(message)s')
        contains_timed_file_handler = False
        contains_stream_handler = False
        for handler in logger.handlers:
            contains_timed_file_handler |= isinstance(handler, TimedRotatingFileHandler)
            contains_stream_handler |= isinstance(handler, logging.StreamHandler)
        if not contains_timed_file_handler:
            trfh = TimedRotatingFileHandler(file_name, when="midnight", interval=1)
            trfh.setLevel(level)
            trfh.suffix = "%Y%m%d.log"
            trfh.setFormatter(formatter)
            logger.addHandler(trfh)
        if not contains_stream_handler:
            sh = logging.StreamHandler()
            sh.setLevel(logging.ERROR)
            sh.setFormatter(formatter)
            logger.addHandler(sh)
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
            mylog.warn(msg)
        elif level == 'E':
            print('[E] ', msg)
            mylog.error(msg)
        elif level == 'C':
            print('[C] ', msg)
            mylog.critical(msg)
        else:
            print('[O] unhandlered message:', msg)
    except Exception as e:
        print('[O] unhandlered message: {} with exception {}'.format(msg, str(e)))
