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


class AvatarView(APIView):
    """上传头像"""
    def post(self, request, *args, **kwargs):
        files = request.Files.get("avatar")
        if not files:
            return JsonResponse({"errcode": RET.NODATA, "errmsg": "未上传图片"})
        avatar = files[0]["body"]

        try:
            file_name = storage(avatar)
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.UNKOWNERR, "errmsg": "上传失败"})

        user_id = request.user

        try:
            models.ih_user_profile.objects.filter(up_user_id=user_id).update_or_create(up_avatar=file_name)
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "保存失败"})
        return JsonResponse({"errcode": RET.OK, "errmsg": "OK", "data": settings.QINIU_URL_PREFIX+file_name})


class ProfileView(APIView):
    """个人信息"""
    def get(self, request, *args, **kwargs):
        user_id = request.user
        try:
            obj = models.ih_user_profile.objects.filter(up_user_id=user_id).values(
                "up_name",
                "up_mobile",
                "up_avatar"
            ).first()
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})
        if obj["up_avatar"]:
            img_url = settings.QINIU_URL_PREFIX + obj["up_avatar"]
        else:
            img_url = None
        data = {
            "user_id": user_id,
            "name": obj["up_name"],
            "mobile": obj["up_mobile"],
            "avatar": img_url
        }
        return JsonResponse({"errcode": RET.OK, "errmsg": "OK", "data": data})


class NameView(APIView):
    """用户名"""
    def post(self, request, *args, **kwargs):
        user_id = request.user
        name = request.query_params.get("name")

        if name in (None, ""):
            return JsonResponse({"errcode": RET.PARAMERR, "errmsg": "数据错误"})

        try:
            models.ih_user_profile.objects.filter(up_user_id=user_id).update(up_name=name)
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "用户名已存在"})

        request.session["name"] = name
        return JsonResponse({"errcode": RET.OK, "errmsg": "OK"})


class AuthView(APIView):
    """实名认证"""
    def get(self, request, *args, **kwargs):
        user_id = request.user

        try:
            obj = models.ih_user_profile.objects.filter(up_user_id=user_id).values(
                "up_real_name",
                "up_id_card"
            ).first()
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})
        if not obj:
            return JsonResponse({"errcode": RET.NODATA, "errmsg": "没有进行认证"})
        data = {
            "real_name": obj.get("up_real_name", ""),
            "id_card": obj.get("up_id_card", ""),
        }
        return JsonResponse({"errcode": RET.OK, "errmsg": "OK", "data": data})

    def post(self, request, *args, **kwargs):
        user_id = request.user
        real_name = request.query_params.get("real_name")
        id_card = request.query_params.get("id_card")

        if real_name in (None, "") or id_card in (None, ""):
            return JsonResponse({"errcode": RET.PARAMERR, "errmsg": "无数据"})

        try:
            models.ih_user_profile.objects.filter(up_user_id=user_id).update_or_create(
                up_real_name=real_name,
                up_id_card=id_card
            )
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})
        return JsonResponse({"errcode": RET.OK, "errmsg": "OK"})
