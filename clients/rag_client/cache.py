import functools, time
class LRU:
    def __init__(self, cap=2048):
        self._cap = cap; self._data = {}
    def get(self, k):
        v = self._data.get(k)
        if v: v[1] = time.time(); return v[0]
    def set(self, k, v):
        self._data[k] = [v, time.time()]
        if len(self._data) > self._cap:
            old = min(self._data.items(), key=lambda x: x[1][1])[0]
            del self._data[old]
CACHE = LRU()