import re
import logging
import json
import time
import datetime
import math
import hashlib
import random
from api import models
from ihome_django import settings
from django.shortcuts import HttpResponse
from api import models
from django.db.models import Q, F
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework.views import APIView
from api.response_code import RET
from api.utils.qiniu_storage import storage
from api.utils import auth, permission, throttle, md5
from api.utils.captcha.captcha import captcha
from django.db import transaction


class OrderView(APIView):
    """订单"""
    def post(self, request, *args, **kwargs):
        """提交订单"""
        user_id = request.user
        house_id = request.data.get("house_id")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")

        # 检查参数
        if not all([house_id, start_date, end_date]):
            return JsonResponse({"errcode": RET.NODATA, "errmsg": "缺少参数"})
        # 查看房屋是否存在
        try:
            house_obj = models.ih_house_info.objects.filter(hi_house_id=house_id).values(
                "hi_price",
                "hi_user_id"
            )
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})

        if not house_obj:
            return JsonResponse({"errcode": RET.NODATA, "errmsg": "没有数据"})

        # 查看房东是否是自己：
        if user_id == house_obj["hi_user_id"]:
            return JsonResponse({"errcode": RET.ROLEERR, "errmsg": "用户为房东"})

        # 判断日期
        format_end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        format_start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        days = (format_end_date - format_start_date).days + 1
        if days <= 0:
            return JsonResponse({"errcode": RET.PARAMERR, "errmsg": "日期不正确"})

        try:
            count_obj = models.ih_order_info.objects.filter(
                oi_house_id=house_id,
                oi_begin_date__lt=end_date,
                oi_end_date__gt=start_date
            ).count()
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})

        if count_obj > 0:
            return JsonResponse({"errcode": RET.DATAERR, "errmsg": "数据错误"})
        amount = days * house_obj["hi_price"]

        try:
            with transaction.atomic():
                models.ih_order_info.objects.create(
                    oi_user_id=user_id,
                    oi_house_id=house_id,
                    oi_begin_date=start_date,
                    oi_end_date=end_date,
                    oi_days=days,
                    oi_house_price=house_obj["hi_price"],
                    oi_amount=amount
                )
                models.ih_house_info.objects.filter(hi_house_id=house_id).update(
                    hi_order_count=F('hi_order_count') + 1
                )
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})
        return JsonResponse({"errcode": RET.OK, "errmsg": "OK"})


class MyOrderView(APIView):
    """我的订单"""
    def get(self, request, *args, **kwargs):
        user_id = request.user
        role = request.query_params.get("role", "")

        try:
            if role == "landlord":
                obj = models.ih_order_info.objects.filter(oi_house_id__hi_user_id=user_id).values(
                    "oi_order_id",
                    "oi_house_id__hi_title",
                    "oi_house_id__hi_index_image_url",
                    "oi_begin_date",
                    "oi_end_date",
                    "oi_ctime",
                    "oi_days",
                    "oi_amount",
                    "oi_status",
                    "oi_comment"
                ).order_by("-oi_ctime")
            else:
                obj = models.ih_order_info.objects.filter(oi_user_id=user_id).values(
                    "oi_order_id",
                    "oi_house_id__hi_title",
                    "oi_house_id__hi_index_image_url",
                    "oi_begin_date",
                    "oi_end_date",
                    "oi_ctime",
                    "oi_days",
                    "oi_amount",
                    "oi_status",
                    "oi_comment"
                ).order_by("-oi_ctime")
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})