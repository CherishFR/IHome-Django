from django.urls import path, re_path
from api import login_views, house_views

urlpatterns = [
    re_path(r'^(?P<version>[v1|v2]+)/login/$', login_views.LoginView.as_view()),
    re_path(r'^(?P<version>[v1|v2]+)/logout/$', login_views.LogoutView.as_view()),
    re_path(r'^(?P<version>[v1|v2]+)/register/$', login_views.RegisterView.as_view()),
    re_path(r'^(?P<version>[v1|v2]+)/piccode/$', login_views.PicCodeView.as_view()),
    re_path(r'^(?P<version>[v1|v2]+)/smscode/$', login_views.SMSCodeView.as_view()),
    re_path(r'^(?P<version>[v1|v2]+)/house/area/$', house_views.AreaInfoView.as_view()),
    re_path(r'^(?P<version>[v1|v2]+)/house/info/$', house_views.HouseInfoView.as_view()),
]
