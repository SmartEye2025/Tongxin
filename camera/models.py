from django.db import models
from django.db.models import Manager


class Student(models.Model):
    object = Manager
    name = models.CharField(max_length=20, verbose_name="姓名")
    student_id = models.CharField(max_length=20,verbose_name="学生ID")
    uwb_id = models.CharField(max_length=20, verbose_name="UWB定位标签id")
    age = models.IntegerField(verbose_name="年龄",default=0)
    speciality = models.CharField(max_length=100,default="无",verbose_name="特殊需求")
    seat_x = models.FloatField(default=0.,verbose_name="座位横坐标")
    seat_y = models.FloatField(default=0., verbose_name="座位纵坐标")

    def __str__(self):
        return self.student_id


# 行为统计表
class Behavior(models.Model):
    object = Manager
    date = models.DateTimeField(auto_now_add=True)
    walk = models.IntegerField(verbose_name="走动",default=0)
    run = models.IntegerField(verbose_name="跑动",default=0)
    lookAround = models.IntegerField(verbose_name="东张西望", default=0)
    offSeat = models.IntegerField(verbose_name="离座", default=0)
    sleeping = models.IntegerField(verbose_name="瞌睡", default=0)
    handup = models.IntegerField(verbose_name="举手", default=0)
    standup = models.IntegerField(verbose_name="起立", default=0)


    def __str__(self):
        return self.date

# 教室
class Classroom(models.Model):
    object = Manager
    class_id = models.CharField(max_length=100,default='')
    matrix = models.JSONField(verbose_name="单应性矩阵",default=None,null=True)
    baseA_x = models.FloatField(verbose_name='A基站x坐标',default=0)
    baseA_y = models.FloatField(verbose_name='A基站y坐标',default=0)
    baseB_x = models.FloatField(verbose_name='B基站x坐标',default=0)
    baseB_y = models.FloatField(verbose_name='B基站y坐标',default=0)
    baseC_x = models.FloatField(verbose_name='C基站x坐标',default=0)
    baseC_y = models.FloatField(verbose_name='C基站y坐标',default=0)
    base_z = models.FloatField(verbose_name='基站共同z坐标',default=0)
    ptz_x = models.FloatField(verbose_name='云台x坐标',default=0)
    ptz_y = models.FloatField(verbose_name='云台y坐标',default=0)
    ptz_z = models.FloatField(verbose_name='云台z坐标', default=0)
