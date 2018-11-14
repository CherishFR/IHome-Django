import re
import logging
import hashlib
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


# Create your views here.

class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        mobile = request.data.get("mobile")
        sms_code = request.data.get("phonecode")
        password = request.data.get("password")

        if not all([mobile, sms_code, password]):
            return JsonResponse({"errcode": RET.PARAMERR, "errmsg": "参数不完整"})

        if not re.match(r"^1\d{10}$", mobile):
            return JsonResponse({"errcode": RET.DATAERR, "errmsg": "手机号码格式错误"})

        if len(password) < 6:
            return JsonResponse({"errcode": RET.DATAERR, "errmsg": "密码长度过短"})

        try:
            real_sms_code = cache.get("sms_code_%s" % mobile)
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库查询出错"})

        if not real_sms_code:
            return JsonResponse({"errcode": RET.NODATA, "errmsg": "验证码过期"})

        if real_sms_code != sms_code:
            return JsonResponse({"errcode": RET.DATAERR, "errmsg": "验证码错误"})

        try:
            cache.delete("sms_code_%s" % mobile)
        except Exception as e:
            logging.error(e)

        password = hashlib.sha256(password + settings.SECRET_KEY).hexdigest()
        try:
            models.ih_user_profile.objects.create(up_name=mobile, up_mobile=mobile, up_passwd=password)
        except Exception as e:
            logging.error(e)
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库查询出错"})

        return JsonResponse({"errcode": RET.OK, "errmsg": "OK"})


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [throttle.VisitThrottle, ]

    def post(self, request, *args, **kwargs):
        mobile = request.data.get("mobile")
        password = request.data.get("password")

        if not all([mobile, password]):
            return JsonResponse({"errcode": RET.PARAMERR, "errmsg": "参数不完整"})

        if not re.match(r"^1\d{10}$", mobile):
            return JsonResponse({"errcode": RET.DATAERR, "errmsg": "手机号码格式错误"})

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
    permission_classes = []

    def delete(self, request, *args, **kwargs):
        token = request.COOKIES.get("token")
        try:
            models.ih_user_token.objects.filter(token=token).delete()
        except Exception as e:
            return JsonResponse({"errcode": RET.DBERR, "errmsg": "数据库操作出错"})
        return JsonResponse({"errcode": RET.OK, "errmsg": "OK"})


class PicCodeView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        pre_code_id = request.query_params.get("pre", "")
        cur_code_id = request.query_params.get("cur")
        # 生成图片验证码
        name, text, pic = captcha.generate_captcha()
        try:
            if pre_code_id:
                cache.delete("pic_code_%s" % pre_code_id)
            cache.set("pic_code_%s" % cur_code_id, text)
        except Exception as e:
            logging.error(e)
            return HttpResponse("查询出错")
        else:
            return HttpResponse(pic, content_type='image/png')
