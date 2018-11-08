from django.urls import path, re_path
from api import views

urlpatterns = [
    re_path('^(?P<version>[v1|v2]+)/login/$', views.LoginView.as_view()),
    re_path('^(?P<version>[v1|v2]+)/register/$', views.RegisterView.as_view()),
]
