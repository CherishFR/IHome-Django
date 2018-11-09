import hashlib
import time


def md5(mobile):
    ctime = str(time.time())
    m = hashlib.md5(bytes(mobile, encoding="tuf-8"))
    m.update(bytes(mobile, encoding="tuf-8"))
    return m.hexdigest()
