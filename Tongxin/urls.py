"""
URL configuration for Tongxin project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from camera import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("get_studentList/", views.get_student_list),
    path('edit_studentInfo/', views.edit_student_info),
    path('add_student/', views.add_student),
    path('delete_student/', views.delete_student),
    path('send_mqtt/', views.send_mqtt),
    path('uploadH/', views.uploadH),
    path('getH/', views.getH),
    path('get_frame/', views.get_frame),
    path('get_calibration/',views.get_calibration),
    path('upload_calibration/',views.upload_calibration),
    path('', views.index),
    path('index/', views.index),
    path('login/', views.user_login),
    path('logout/', views.user_logout),
    path('update-profile/', views.update_profile),
    path('update_avatar/', views.update_avatar),
    path('update_nickname/', views.update_nickname),
    path('get_user_info/', views.get_user_info),
    path('bind_student/', views.bind_student),
    path('unbind_student/', views.unbind_student),
    path('get_binding_info/', views.get_binding_info),
    path('get_student_info/', views.get_student_info),
    path('logout/', views.user_logout),
    path('statistics/', views.statistics),
    path('weekly_data/', views.weekly_data),
    path('distraction_types/', views.distraction),
    # 新增
    path('notices/', views.list_notices),
    path('evaluations/', views.list_evaluations),
    path('messages/', views.list_messages),
    path('leave_requests/', views.create_leave_request),
    path('get_rank/', views.get_rank),
]
