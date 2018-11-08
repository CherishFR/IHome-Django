import time
from ihome_django import settings
from rest_framework.throttling import BaseThrottle
from django.core.cache import cache


class VisitThrottle(BaseThrottle):

    def __init__(self):
        self.history = None

    def allow_request(self, request, view):
        """60s内只能访问3次"""
        remote_addr = self.get_ident(request)  # 获取IP地址
        ctime = time.time()  # 获取当前时间
        # 如果访问记录中没有请求者的IP，则创建对应的键值对，并允许访问
        if not cache.get(remote_addr):
            cache.set(remote_addr, [ctime, ])
            return True  # 表示可以访问
        # 如果有对应的访问记录就取出来
        self.history = cache.get(remote_addr)
        # 处理相关的记录，只保留60s以内的记录
        while self.history and self.history[-1] < ctime - 60:
            self.history.pop()
        # 查看处理后的记录数量，如果小于3次则允许访问
        if len(self.history) < 3:
            self.history.insert(0, ctime)
            cache.set(remote_addr, self.history)
            return True
        return False  # 返回False表示访问频率太高，被限制

    def wait(self):
        """需要等多少秒才能访问"""
        ctime = time.time()
        return 60 - (ctime - self.history[-1])