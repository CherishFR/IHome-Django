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
from api.utils.qiniu_storage import storage
from api.utils import auth, permission, throttle, md5
from api.utils.captcha.captcha import captcha


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
    def get(self, request, *args, **kwargs):
        """获取房屋信息"""
        user_id = request.user
        house_id = request.query_params.get("house_id")
        if not house_id:
            return JsonResponse({"errcode": RET.PARAMERR, "errmsg": "缺少参数"})

        # 先尝试从缓存中获取参数
        try:
            ret = cache.get("house_info_%s" % house_id)
        except Exception as e:
            logging.error(e)
            ret = None
        if ret:
            return JsonResponse({"errcode": RET.OK, "errmsg": "OK", "data": ret, "user_id": user_id})

        # 查询数据库
        try:
            house_obj = models.ih_house_info.objects.filter(hi_house_id=house_id).values(
                'hi_title',
                'hi_price',
                'hi_address',
                'hi_room_count',
                'hi_acreage',
                'hi_house_unit',
                'hi_capacity',
                'hi_beds',
                'hi_deposit',
                'hi_min_days',
                'hi_max_days',
                'hi_user_id__up_name',
                'hi_user_id__up_avatar',
                'hi_user_id'
            ).first()
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DATAERR, "errmsg": "参数错误"})
        if not house_obj:
            return JsonResponse({"errcode": RET.NODATA, "errmsg": "查无此房"})
        data = {
            "hid": house_id,
            "user_id": house_obj["hi_user_id"],
            "title": house_obj["hi_title"],
            "price": house_obj["hi_price"],
            "address": house_obj["hi_address"],
            "room_count": house_obj["hi_room_count"],
            "acreage": house_obj["hi_acreage"],
            "unit": house_obj["hi_house_unit"],
            "capacity": house_obj["hi_capacity"],
            "beds": house_obj["hi_beds"],
            "deposit": house_obj["hi_deposit"],
            "min_days": house_obj["hi_min_days"],
            "max_days": house_obj["hi_max_days"],
            "user_name": house_obj["hi_user_id__up_name"],
            "user_avatar": settings.QINIU_URL_PREFIX + house_obj["up_avatar"]
            if house_obj.get("hi_user_id__up_avatar") else ""
        }

        # 查询图片信息
        try:
            img_obj = models.ih_house_image.objects.filter(hi_house_id=house_id).values("hi_url")
        except Exception as e:
            logging.error(e)
            img_obj = None
        images = []
        if img_obj:
            for image in img_obj:
                images.append(settings.QINIU_URL_PREFIX + image["hi_url"])
        data["images"] = images

        # 查看房屋基础设施
        try:
            facility_obj = models.ih_house_facility.objects.filter(hf_house_id=house_id).values("hf_facility_id")
        except Exception as e:
            logging.error(e)
            facility_obj = None
        facilities =[]
        if facility_obj:
            for facility in facility_obj:
                facilities.append(facility["hf_facility_id"])
        data["facilities"] = facilities

        # 查看评论信息
        try:
            comment_obj = models.ih_order_info.objects.filter(
                oi_house_id=house_obj,
                oi_status=4,
                oi_comment__isnull=False
            ).values(
                "oi_comment",
                "oi_user_id__up_name",
                "oi_utime",
                "oi_user_id__up_mobile"
            )
        except Exception as e:
            logging.error(e)
            comment_obj = None
        comments = []
        if comment_obj:
            for comment in comment_obj:
                comments.append({
                    "user_name": comment["oi_user_id__up_name"]
                    if comment["oi_user_id__up_name"] != comment["oi_user_id__up_mobile"] else "匿名用户",
                    "content": comment["oi_comment"],
                    "ctime": comment["oi_utime"].strftime("%Y-%m-%d %H:%M:%S")
                })
        data["comments"] = comments

        # 存入到redis中
        json_data = json.dumps(data)
        try:
            cache.set("house_info_%s" % house_id, json_data, settings.REDIS_HOUSE_INFO_EXPIRES_SECONDES)
        except Exception as e:
            logging.error(e)

        return JsonResponse({"errcode": RET.OK, "errmsg": "OK", "data": json_data, "user_id": user_id})

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


class HouseImageView(APIView):
    def post(self, request, *args, **kwargs):
        house_id = request.query_params.get("house_id")
        house_image = request.FILES.get("house_image")[0]["body"]
        # 调用七牛云的storage方法上传图片
        img_name = storage(house_image)
        if not img_name:
            return JsonResponse({"errcode": RET.UNKOWNERR, "errmsg": "qiniu error"})
        try:
            models.ih_house_image.objects.create(hi_house_id=house_id, hi_url=img_name)
            models.ih_house_info.objects.filter(
                hi_house_id=house_id,
                hi_index_image_url__isnull=False
            ).update(hi_index_image_url=house_image)
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})
        img_url = settings.QINIU_URL_PREFIX + img_name
        return JsonResponse({"errcode": RET.OK, "errmsg": "OK", "url": img_url})


class MyHousesView(APIView):
    def get(self, request, *args, **kwargs):
        user_id = request.user
        try:
            obj = models.ih_house_info.objects.filter(hi_user_id=user_id).values(
                "hi_house_id",
                "hi_title",
                "hi_price",
                "hi_ctime",
                "hi_area_id__ai_name",
                "hi_index_image_url"
            )
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})
        houses = []
        if obj:
            for i in obj:
                house = {
                    "house_id": i["hi_house_id"],
                    "title": i["hi_title"],
                    "price": i["hi_price"],
                    "ctime": i["hi_ctime"].strftime("%Y-%m-%d"),
                    "area_name": i["hi_area_id__ai_name"],
                    "img_url": settings.QINIU_URL_PREFIX + i["hi_index_image_url"] if i["hi_index_image_url"] else ""
                }
                houses.append(house)
        return JsonResponse({"errcode": RET.OK, "errmsg": "OK", "houses": houses})


class IndexView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            ret = cache.get("home_page_data")
        except Exception as e:
            logging.error(e)
            ret = None
        if ret:
            json_houses = ret
        else:
            try:
                house_obj = models.ih_house_info.objects.values(
                    "hi_house_id",
                    "hi_title",
                    "hi_order_count",
                    "hi_index_image_url"
                ).order_by("-hi_order_count")[:settings.HOME_PAGE_MAX_HOUSES]
            except Exception as e:
                logging.error(e)
                return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})
            if not house_obj:
                return JsonResponse({"errcode": RET.NODATA, "errmsg": "没有数据"})
            houses = []
            for i in house_obj:
                if not i["hi_index_image_url"]:
                    continue
                house = {
                    "house_id": i["hi_house_id"],
                    "title": i["hi_title"],
                    "img_url": settings.QINIU_URL_PREFIX + i["hi_index_image_url"]
                }
                houses.append(house)
            json_houses = json.dumps(houses)
            try:
                cache.set("home_page_data", json_houses, settings.HOME_PAGE_DATA_REDIS_EXPIRE_SECOND)
            except Exception as e:
                logging.error(e)

        try:
            ret = cache.get("area_info")
        except Exception as e:
            logging.error(e)
            ret = None
        if ret:
            json_areas = ret
        else:
            try:
                area_obj = models.ih_area_info.objects.values("ai_area_id", "ai_name")
            except Exception as e:
                logging.error(e)
                return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})
            areas = []
            if area_obj:
                for area in area_obj:
                    areas.append({"area_id": area["ai_area_id"], "name": area["ai_name"]})
            json_areas = json.dumps(areas)
            try:
                cache.set("rea_info", json_areas, settings.REDIS_AREA_INFO_EXPIRES_SECONDES)
            except Exception as e:
                logging.error(e)
        return JsonResponse({"errcode": RET.OK, "errmsg": "OK", "houses": json_houses, "areas": json_areas})
