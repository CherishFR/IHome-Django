from django.core.cache import cache
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from api import models


class Authentication(BaseAuthentication):
    def authenticate(self, request):
        token = request.COOKIES.get("token")
        try:
            token_obj = models.ih_user_token.objects.filter(token=token).first()
        except Exception as e:
            raise exceptions.AuthenticationFailed("数据库查询出错")
        if not token_obj:
            raise exceptions.AuthenticationFailed("用户认证失败")
        return token_obj.up_user, token_obj

    def authenticate_header(self, request):
        pass
