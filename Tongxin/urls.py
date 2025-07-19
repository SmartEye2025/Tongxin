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
    path("get_studentList/", views.get_studenList),
    path('edit_studentInfo/', views.edit_studentInfo),
    path('add_student/', views.add_student),
    path('delete_student/', views.delete_student),
    path('send_mqtt/', views.send_mqtt),
    path('uploadH/', views.uploadH),
    path('getH/', views.getH),
    path('get_frame/', views.get_frame),
    path('get_calibration/',views.get_calibration),
    path('upload_calibration/',views.upload_calibration),
]
