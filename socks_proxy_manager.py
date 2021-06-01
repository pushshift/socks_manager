import time
import requests
import random
import math
import threading
import logging

class ProxyManagerError(Exception):
    pass

class ProxyAlreadyAdded(ProxyManagerError):
    pass

class ProxyListExhausted(ProxyManagerError):
    pass


class Proxy:

    def __init__(self, **kwargs):
        self.host = kwargs['host']
        self.port = kwargs['port']
        self.user = kwargs['user']
        self.pw = kwargs['pw']
        self.reserved = False
        self.wait_until = 0
        self.use_count = 0

    def __hash__(self):
        return hash((self.host, self.port))

    def __eq__(self, other):
        return (self.host, self.port) == (other.host, other.port)

    def __str__(self):
        return str(self.host)

    def asdict(self):
        return {"http":f"socks5://{self.user}:{self.pw}@{self.host}:{self.port}", "https":f"socks5://{self.user}:{self.pw}@{self.host}:{self.port}"}

    def __getitem__(self, key):
        if key == "http":
            return {"http":f"socks5://{self.user}:{self.pw}@{self.host}:{self.port}"}
        elif key == "https":
            return {"https":f"socks5://{self.user}:{self.pw}@{self.host}:{self.port}"}
        elif key == "all":
            return {"http":f"socks5://{self.user}:{self.pw}@{self.host}:{self.port}", "https":f"socks5://{self.user}:{self.pw}@{self.host}:{self.port}"}

    @property
    def http(self):
        return {"http":f"socks5://{self.user}:{self.pw}@{self.host}:{self.port}"}

    @property
    def https(self):
        return {"https":f"socks5://{self.user}:{self.pw}@{self.host}:{self.port}"}

    @property
    def proxy(self):
        return {"http":f"socks5://{self.user}:{self.pw}@{self.host}:{self.port}", "https":f"socks5://{self.user}:{self.pw}@{self.host}:{self.port}"}


    #def __repr__(self):
    #    return {"http":f"socks5://{self.user}:{self.pw}@{self.host}:{self.port}", "https":f"socks5://{self.user}:{self.pw}@{self.host}:{self.port}"}


class SocksProxyManager:

    def __init__(self):
        self.proxies = {}
        self.proxy_pool = []
        self.round_robin_pos = 0
        self.num_proxy_entries = len(self.proxy_pool)
        self.lock = threading.RLock()
        self.current_proxy = None

    def get_proxy(self, strategy="round_robin"):
        min_wait = math.inf
        while True:
            with self.lock:
                for proxy in self.proxies.keys():
                    if self.proxies[proxy].wait_until > time.time():
                        min_wait = min(min_wait, self.proxies[proxy].wait_until - time.time())
                        continue
                    released_proxy = self.proxies.pop(proxy)
                    return released_proxy
                logging.info(f"Must wait {min_wait} seconds before next proxy is available")

    def proxy(self, wait_until=None, reserved=False):
        #if self.current_proxy is None:
        #    self.current_proxy = self.get_proxy()
        #    logging.debug(f"NEW PROXY: {self.current_proxy}")
        ct = time.time()
        if self.current_proxy['wait_until'] and self.current_proxy['wait_until'] < ct:
            logging.warning(f"This proxy needs to wait {self.proxy['wait_until'] - ct} seconds.")
            time.sleep(self.proxy['wait_until'] - ct)
            self.proxy['wait_until'] = None
        return {"http":f"socks5://{self.current_proxy['proxy']}", "https":f"socks5://{self.current_proxy['proxy']}"}

    def release(self, proxy, wait_until=None):
        '''Release a proxy back into pool

        '''
        with self.lock:
            if wait_until is not None:
                proxy.wait_until = wait_until
            self.proxies[proxy] = proxy

    def add(self, user: str, pw: str, host: str, port: int):
        '''Add a new proxy to proxy pool

            Format: user:password@xxx.xxx.xxx.xxx:port

        '''
        with self.lock:
            new_proxy = Proxy(user=user, pw=pw, host=host, port=port)
            if new_proxy in self.proxies:
                raise ProxyAlreadyAdded("Proxy was previously added.")
            self.proxies[new_proxy] = new_proxy


    def remove(self, proxy):
        '''Remove a proxy from the proxy pool

            Format user:password@xxx.xxx.xxx.xxx:port

        '''
        with self.lock:
            del self.proxies[proxy]
#            index_pos = next((i for i, obj in enumerate(self.proxy_pool) if obj['proxy'] == proxy), None)
#            if index_pos:
#                del self.proxy_pool[index_pos]
#                self.num_proxy_entries = len(self.proxy_pool)
#                if index_pos != 0 and index_pos < self.round_robin_pos:
#                    self.round_robin_pos -= 1


    @property
    def count(self):
        return len(self.proxies)
