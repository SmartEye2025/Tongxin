from django.db import models
from django.db.models import Manager


class Student(models.Model):
    object = Manager
    name = models.CharField(max_length=20, verbose_name="姓名")
    student_id = models.CharField(max_length=20,verbose_name="学生ID")
    uwb_id = models.CharField(max_length=20, verbose_name="UWB定位标签id")
    seat_x = models.FloatField(default=0.,verbose_name="座位横坐标")
    seat_y = models.FloatField(default=0., verbose_name="座位纵坐标")

    def __str__(self):
        return self.student_id