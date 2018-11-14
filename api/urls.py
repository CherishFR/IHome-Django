from django.urls import path, re_path
from api import views

urlpatterns = [
    re_path(r'^(?P<version>[v1|v2]+)/login/$', views.LoginView.as_view()),
    re_path(r'^(?P<version>[v1|v2]+)/logout/$', views.LogoutView.as_view()),
    re_path(r'^(?P<version>[v1|v2]+)/register/$', views.RegisterView.as_view()),
    re_path(r'^(?P<version>[v1|v2]+)/piccode/$', views.PicCodeView.as_view()),
]
