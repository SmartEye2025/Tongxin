from django.contrib import admin
from django.contrib.auth.models import Group

from .models import *

# Register your models here.

admin.site.register(Behavior)
admin.site.register(Student)
admin.site.register(User)
admin.site.register(ParentStudentBinding)

admin.site.register(Notice)
admin.site.register(Evaluation)
admin.site.register(Message)
admin.site.register(LeaveRequest)