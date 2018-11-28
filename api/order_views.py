import re
import logging
import json
import time
import math
import hashlib
import random
from api import models
from ihome_django import settings
from django.shortcuts import HttpResponse
from api import models
from django.db.models import Q
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework.views import APIView
from api.response_code import RET
from api.utils.qiniu_storage import storage
from api.utils import auth, permission, throttle, md5
from api.utils.captcha.captcha import captcha


class OrderView(APIView):
    """订单"""
    def post(self, request, *args, **kwargs):
        """提交订单"""
        user_id = request.user
        house_id = request.data