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

class TransformationMatrix(models.Model):
    matrix = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Matrix at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']  # 按时间降序排列