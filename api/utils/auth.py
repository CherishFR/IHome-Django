from django.core.cache import cache
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication


class Authentication(BaseAuthentication):
    def authenticate(self, request):
        token = request._request.GET.get("token")
        try:
            token_obj = cache.get(token)
        except Exception as e:
            raise exceptions.AuthenticationFailed("数据库查询出错")
        if not token_obj:
            raise exceptions.AuthenticationFailed("用户认证失败")
        return token_obj.user, token_obj

    def authenticate_header(self, request):
        pass
