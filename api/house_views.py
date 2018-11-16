import re
import logging
import json
import hashlib
import random
from api import models
from ihome_django import settings
from django.shortcuts import HttpResponse
from api import models
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework.views import APIView
from api.response_code import RET
from api.utils import auth, permission, throttle, md5
from api.utils.captcha.captcha import captcha
from api.libs.yuntongxun.SendTemplateSMS import ccp


class AreaInfoView(APIView):
    """提供城区信息"""
    def get(self, request, *args, **kwargs):
        # 先看redis中有没有数据
        try:
            ret = cache.get("area_info")
        except Exception as e:
            logging.error(e)
            ret = None
        if ret:
            logging.info("hit redis: area_info")
            return JsonResponse({"errcode": RET.OK, "errmsg": "OK", "data": ret})

        # redis中没有则去数据库中取
        try:
            obj = models.ih_area_info.objects.all().values("ai_area_id", "ai_name")
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})
        if not obj:
            return JsonResponse({"errcode": RET.NODATA, "errmsg": "没有数据"})

        # 数据处理
        data = []
        for row in obj:
            msg = {
                "area_id": row.get("ai_area_id", ""),
                "name": row.get("ai_name", "")
            }
            data.append(msg)

        # 将数据存入redis
        json_data = json.loads(data)
        try:
            cache.setex("area_info", json_data, settings.REDIS_AREA_INFO_EXPIRES_SECONDES)
        except Exception as e:
            logging.error(e)

        return JsonResponse({"errcode": RET.OK, "errmsg": "OK", "data": data})