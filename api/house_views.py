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


class HouseInfoView(APIView):
    """房屋信息"""
    def post(self, request, *args, **kwargs):
        """保存"""
        user_id = request.user
        title = request.data.get("title")
        price = request.data.get("price")
        area_id = request.data.get("area_id")
        address = request.data.get("address")
        room_count = request.data.get("room_count")
        acreage = request.data.get("acreage")
        unit = request.data.get("unit")
        capacity = request.data.get("capacity")
        beds = request.data.get("beds")
        deposit = request.data.get("deposit")
        min_days = request.data.get("min_days")
        max_days = request.data.get("max_days")
        facility = request.data.get("facility")

        if not all([title, price, area_id, address, room_count,
                    acreage, unit, capacity, beds, deposit,
                    min_days, max_days, facility]):
            return JsonResponse({"errcode": RET.PARAMERR, "errmsg": "缺少参数"})

        try:
            price = int(price) * 100
            deposit = int(deposit) * 100
        except Exception as e:
            return JsonResponse({"errcode": RET.DATAERR, "errmsg": "参数错误"})

        try:
            house_id = models.ih_house_info.objects.create(
                hi_user_id=user_id,
                hi_title=title,
                hi_price=price,
                hi_area_id=area_id,
                hi_address=address,
                hi_room_count=room_count,
                hi_acreage=acreage,
                hi_house_unit=unit,
                hi_capacity=capacity,
                hi_beds=beds,
                hi_deposit=deposit,
                hi_min_days=min_days,
                hi_max_days=max_days,
            )
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})

        try:
            for i in range(len(facility)):
                models.ih_house_facility.objects.create(hf_house_id=house_id,
                                                        hf_facility_id=facility[i])
        except Exception as e:
            logging.error(e)
            try:
                models.ih_house_info.objects.delete(hi_house_id=house_id)
            except Exception as e:
                logging.error(e)
                return JsonResponse({"errcode": RET.DBERR, "errmsg": "删除失败"})
            else:
                return JsonResponse({"errcode": RET.DBERR, "errmsg": "没有数据保持"})
        return JsonResponse({"errcode": RET.OK, "errmsg": "OK", "house_id": house_id})
