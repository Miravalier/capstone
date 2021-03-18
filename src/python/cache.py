import time


TIMEOUT_NS = 8*60*60*1e+9 # 8 Hours


class Cache:
    def __init__(self):
        self.cache = {}
        self.timeout = time.monotonic_ns() + TIMEOUT_NS

    def check_timeout(self):
        current_time = time.monotonic_ns()
        if current_time > self.timeout:
            self.cache = {}
            self.timeout = current_time + TIMEOUT_NS
    
    def __getitem__(self, key):
        self.check_timeout()
        return self.cache.get(key, None)
    
    def __setitem__(self, key, value):
        self.check_timeout()
        self.cache[key] = value