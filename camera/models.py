from django.contrib.auth.hashers import make_password
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.db.models import Manager
from django.contrib.auth.models import AbstractUser
import os
import uuid

# ---------------------网页端---------------------------
# 学生信息表
class Student(models.Model):
    object = Manager
    name = models.CharField(max_length=20, verbose_name="姓名")
    student_id = models.CharField(max_length=20,verbose_name="学生ID")
    uwb_id = models.CharField(max_length=20, verbose_name="UWB定位标签id")
    age = models.IntegerField(verbose_name="年龄",default=0)
    speciality = models.CharField(max_length=100,default="无",verbose_name="特殊需求")
    seat_x = models.FloatField(default=0.,verbose_name="座位横坐标")
    seat_y = models.FloatField(default=0., verbose_name="座位纵坐标")

    class Meta:
        verbose_name = _("学生")
        verbose_name_plural = _("学生管理")

    def __str__(self):
        return f"{self.name} 学号：{self.student_id}"

# 行为统计表
class Behavior(models.Model):
    object = Manager
    date = models.DateTimeField(auto_now_add=False, editable=True)
    subject = models.CharField(max_length=100, verbose_name="学科",default="语文")
    student = models.ForeignKey(Student,on_delete=models.CASCADE,verbose_name="学生",default=None)

    hand_up = models.IntegerField(verbose_name="举手", default=0)
    focus_time = models.FloatField(verbose_name="专注时长(分钟)",default=0)
    hyperactive = models.IntegerField(verbose_name="多动",default=0)
    look_around = models.IntegerField(verbose_name="东张西望", default=0)
    off_seat = models.IntegerField(verbose_name="离座", default=0)
    sleeping = models.IntegerField(verbose_name="瞌睡", default=0)
    stand_up = models.IntegerField(verbose_name="起立", default=0)

    class Meta:
        verbose_name = _("学生行为")
        verbose_name_plural = _("行为管理")

    def __str__(self):
        return f"{self.student.name}: {self.date.strftime("%Y-%m-%d %H:%M:%S")}"

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


# ------------------小程序端----------------------
def user_avatar_path(instance, filename):
    # 为上传的头像生成唯一文件名
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('avatars', filename)

# 用户模型
class User(AbstractUser):
    # 扩展用户模型
    nickname = models.CharField(max_length=50, blank=True, null=True, verbose_name='昵称')
    username = models.CharField(max_length=150,unique=True,default="user",verbose_name="用户名")
    password = models.CharField(_('password'),max_length=128,default=make_password('temporary_password'))
    avatar = models.ImageField(upload_to=user_avatar_path,blank=True,null=True,verbose_name='头像',default='avatars/default.png')

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户管理'

    def __str__(self):
        return f"{self.username} 昵称：{self.nickname}"

    @property
    def avatar_url(self):
        # 如果没有头像，返回默认头像URL
        return self.avatar.url if self.avatar else '/media/avatars/default.png'

# 家长学生绑定关系模型
class ParentStudentBinding(models.Model):
    object = Manager
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_bindings', verbose_name='用户', default=1)
    student_id = models.CharField(max_length=100, verbose_name='学生学号')
    student_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='学生姓名')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='绑定时间')
    is_active = models.BooleanField(default=True, verbose_name='是否有效')

    class Meta:
        verbose_name = _("关系绑定")
        verbose_name_plural = _("家长学生绑定")

    def __str__(self):
        return f"{self.user.nickname}->{self.student_name}:{self.student_id}"



# 新增
# ------------------ 公告 / 评价 / 消息 / 请假 ----------------------
class Notice(models.Model):
    object = Manager
    title = models.CharField(max_length=200, verbose_name='标题')
    content = models.TextField(verbose_name='内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = _("公告")
        verbose_name_plural = _("公告管理")

    def __str__(self):
        return self.title


class Evaluation(models.Model):
    object = Manager
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name='学生')
    subject = models.CharField(max_length=100, verbose_name='学科', default='综合')
    teacher_name = models.CharField(max_length=100, verbose_name='教师', default='')
    comment = models.TextField(verbose_name='评价内容', default='')
    rating = models.IntegerField(verbose_name='评分', default=5)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = _("评价")
        verbose_name_plural = _("评价管理")

    def __str__(self):
        return f"{self.student.name} - {self.subject}"


class Message(models.Model):
    object = Manager
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户', related_name='messages')
    title = models.CharField(max_length=200, verbose_name='标题')
    content = models.TextField(verbose_name='内容')
    is_read = models.BooleanField(default=False, verbose_name='是否已读')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = _("消息")
        verbose_name_plural = _("消息管理")

    def __str__(self):
        return f"给 {self.user.nickname} -- {self.title}"


class LeaveRequest(models.Model):
    object = Manager
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name='学生')
    reason = models.TextField(verbose_name='请假原因')
    leave_type = models.CharField(max_length=50, verbose_name='请假类型', default='事假')
    start_date = models.DateField(verbose_name='开始日期')
    end_date = models.DateField(verbose_name='结束日期')
    status = models.CharField(max_length=20, verbose_name='状态', default='待审核')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = _("请假")
        verbose_name_plural = _("请假管理")

    def __str__(self):
        return f"{self.student.name} {self.start_date}~{self.end_date} {self.leave_type}"