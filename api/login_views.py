import re
import logging
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


# Create your views here.

class RegisterView(APIView):
    """校验验证码并注册账户"""
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        mobile = request.data.get("mobile")
        sms_code = request.data.get("phonecode")
        password = request.data.get("password")

        # 校验参数
        if not all([mobile, sms_code, password]):
            return JsonResponse({"errcode": RET.PARAMERR, "errmsg": "参数不完整"})

        if not re.match(r"^1\d{10}$", mobile):
            return JsonResponse({"errcode": RET.DATAERR, "errmsg": "手机号码格式错误"})

        if len(password) < 6:
            return JsonResponse({"errcode": RET.DATAERR, "errmsg": "密码长度过短"})

        # 获取短信验证码
        try:
            real_sms_code = cache.get("sms_code_%s" % mobile)
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库查询出错"})

        # 比对短信验证码
        if not real_sms_code:
            return JsonResponse({"errcode": RET.NODATA, "errmsg": "验证码过期"})
        if real_sms_code != sms_code:
            return JsonResponse({"errcode": RET.DATAERR, "errmsg": "验证码错误"})

        # 删除短信验证码
        try:
            cache.delete("sms_code_%s" % mobile)
        except Exception as e:
            logging.error(e)

        # 注册账户
        password = hashlib.sha256(password + settings.SECRET_KEY).hexdigest()
        try:
            models.ih_user_profile.objects.create(up_name=mobile, up_mobile=mobile, up_passwd=password)
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库查询出错"})

        return JsonResponse({"errcode": RET.OK, "errmsg": "OK"})


class LoginView(APIView):
    """登陆系统"""
    authentication_classes = []
    permission_classes = []
    throttle_classes = [throttle.VisitThrottle, ]

    def post(self, request, *args, **kwargs):
        mobile = request.data.get("mobile")
        password = request.data.get("password")

        # 校验参数
        if not all([mobile, password]):
            return JsonResponse({"errcode": RET.PARAMERR, "errmsg": "参数不完整"})

        if not re.match(r"^1\d{10}$", mobile):
            return JsonResponse({"errcode": RET.DATAERR, "errmsg": "手机号码格式错误"})

        # 查找数据库中是否存在对应的账户，并生成token
        password = hashlib.sha256(password + settings.SECRET_KEY).hexdigest()
        try:
            obj = models.ih_user_profile.objects.filter(up_mobile=models, up_passwd=password).first()
            if not obj:
                return JsonResponse({"errcode": RET.DATAERR, "errmsg": "用户名密码错误"})
            user_token = md5.md5(mobile)
            models.ih_user_token.objects.update_or_create(up_user=obj, defaults={'up_token': user_token})
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})
        response = JsonResponse({"errcode": RET.OK, "errmsg": "OK"})
        response.set_cookie("token", user_token)
        return response


class LogoutView(APIView):
    """退出登录"""
    permission_classes = []

    def delete(self, request, *args, **kwargs):
        token = request.COOKIES.get("token")
        # 清除账户对应的token
        try:
            models.ih_user_token.objects.filter(token=token).delete()
        except Exception as e:
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})
        return JsonResponse({"errcode": RET.OK, "errmsg": "OK"})


class PicCodeView(APIView):
    """生成图形验证码"""
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        pre_code_id = request.query_params.get("pre", "")
        cur_code_id = request.query_params.get("cur")
        # 生成图片验证码
        name, text, pic = captcha.generate_captcha()

        # 将验证码数据存入redis
        try:
            if pre_code_id:
                cache.delete("pic_code_%s" % pre_code_id)
            cache.set("pic_code_%s" % cur_code_id, text)
        except Exception as e:
            logging.error(e)
            return HttpResponse("查询出错")
        else:
            return HttpResponse(pic, content_type='image/png')


class SMSCodeView(APIView):
    """生成短信验证码"""
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        mobile = request.data.get("mobile")
        piccode = request.data.get("piccode")
        piccode_id = request.data.get("piccode_id")

        # 校验参数
        if not all([mobile,piccode,piccode_id]):
            return JsonResponse({"errcode": RET.PARAMERR, "errmsg": "参数不完整"})
        if not re.match(r"^1\d{10}$", mobile):
            return JsonResponse({"errcode": RET.DATAERR, "errmsg": "手机号码格式错误"})

        # 获取图片验证码
        try:
            real_piccode = cache.get("pic_code_%s" % piccode_id)
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})
        if not real_piccode:
            return JsonResponse({"errcode": RET.NODATA, "errmsg": "验证码已过期"})

        # 删除图片验证码
        try:
            cache.delete("pic_code_%s" % piccode_id)
        except Exception as e:
            logging.error(e)

        if real_piccode.lower() != piccode.lower():
            return JsonResponse({"errcode": RET.DATAERR, "errmsg": "验证码错误"})

        # 检查手机号是否已注册
        try:
            obj = models.ih_user_profile.objects.filter(up_mobile=mobile).first()
        except Exception as e:
            logging.error(e)
        else:
            if obj:
                return JsonResponse({"errcode": RET.DATAEXIST, "errmsg": "该手机号已被注册"})

        # 生成短信验证码
        sms_code = "%06d" % random.randint(1, 1000000)
        try:
            cache.set("sms_code_%s" % mobile, sms_code)
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})

        # 发送短信
        try:
            result = ccp.sendTemplateSMS(mobile, [sms_code, settings.SMS_CODE_EXPIRES_SECONDS / 60], 1)
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})
        if result:
            return JsonResponse({"errcode": RET.OK, "errmsg": "OK"})
        else:
            return JsonResponse({"errcode": RET.UNKOWNERR, "errmsg": "发送失败"})