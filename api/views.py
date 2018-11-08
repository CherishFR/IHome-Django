import re
from django.shortcuts import render, HttpResponse
from api import models
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.versioning import URLPathVersioning
from api.response_code import RET
from api.utils import auth, permission, throttle


# Create your views here.

class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [throttle.VisitThrottle, ]

    def post(self, request, *args, **kwargs):
        mobile = request.data.get("mobile")
        sms_code = request.data.get("phonecode")
        password = request.data.get("password")

        if not all([mobile, sms_code, password]):
            return JsonResponse({"errcode": RET.PARAMERR, "errmsg": "参数不完整"})

        if not re.match(r"^1\d{10}$", mobile):
            return JsonResponse({"errcode": RET.DATAERR, "errmsg": "手机号码格式错误"})


class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        pass