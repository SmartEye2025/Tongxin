from django.contrib.auth import login, logout
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.http import HttpResponse
from django.db.models import Sum, Count
from camera.models import *
from camera.mqtt_client import client
from camera.consumers import frame_queue

from .models import ParentStudentBinding
from .models import Student
from .models import User
from .models import Behavior
from .models import Notice, Evaluation, Message, LeaveRequest

import cv2
import base64
import json
import random
import re
import os
from django.conf import settings


# ---------------------网页端------------------------
#  获取学生列表
def get_student_list(request):
    if request.method == 'GET':
        studentList = []
        for a in Student.objects.all():
            studentList.append({
                'student_id': a.student_id,
                'uwb_id': a.uwb_id,
                'class_id':a.class_id,
                'name': a.name,
                'age': a.age,
                'specialNeeds':a.speciality.split(' '),
                'seat_x': a.seat_x,
                'seat_y': a.seat_y,
            })
        return JsonResponse({'studentList':studentList},status=200)
    else:
        return HttpResponse('Expect a GET request', status=405)

@csrf_exempt
# 编辑学生信息
def edit_student_info(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        student = Student.objects.get(student_id=data['student_id'])
        student.uwb_id = data['uwb_id']
        student.class_id = data['class_id']
        student.name = data['name']
        student.age = data['age']
        student.seat_x = data['seat_x']
        student.seat_y = data['seat_y']
        student.speciality = ' '.join(data['specialNeeds'])
        student.save()
        return HttpResponse('success', status=200)
    else:
        return HttpResponse('Expect a POST request', status=405)

@csrf_exempt
# 添加学生
def add_student(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        student = Student(
            student_id=data['student_id'],
            uwb_id=data['uwb_id'],
            class_id = data['class_id'],
            name=data['name'],
            age=data['age'],
            seat_x = data['seat_x'],
            seat_y = data['seat_y'],
            speciality=' '.join(data['specialNeeds']),
        )
        student.save()
        return HttpResponse('success', status=200)
    else:
        return HttpResponse('Expect a POST request', status=405)

@csrf_exempt
# 删除学生
def delete_student(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        student = Student.objects.get(student_id=data['student_id'])
        student.delete()
        return HttpResponse('success', status=200)
    else:
        return HttpResponse('Expect a POST request', status=405)

@csrf_exempt
# 发送mqtt
def send_mqtt(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        rc, mid = client.publish(data['topic'], json.dumps(data['msg']))
        if rc==0:
            return HttpResponse('success', status=200)
        else:
            return HttpResponse('error', status=500)
    else:
        return HttpResponse('Expect a POST request', status=405)

@csrf_exempt
# 上传坐标变换矩阵
def uploadH(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            matrix = data.get('matrix')
            record, _ = Classroom.objects.get_or_create(
                class_id=data['class_id'],
                defaults={'matrix': None}
            )
            record.matrix = matrix
            record.save()
            return JsonResponse({
                'success': True,
            }, status=200)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    return JsonResponse({'error': 'Expect a POST request'}, status=405)

def getH(request):
    if request.method == 'GET':
        try:
            latest_matrix = Classroom.objects.last()  # 获取最后一条
            if not latest_matrix:
                return JsonResponse({
                    'success': False,
                    'error': 'No matrix found'
                }, status=404)

            return JsonResponse({
                'success': True,
                'matrix': latest_matrix.matrix,
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    return JsonResponse({'error': 'Expect a GET request'}, status=405)

def get_frame(request):
    if request.method != 'GET':
        return HttpResponse('Expect a POST request', status=405)
    try:
        # # 添加超时避免永久阻塞
        # frame = frame_queue.get(timeout=2.0)  # 2秒超时
        # _, buffer = cv2.imencode('.jpg', cv2.cvtColor(frame,cv2.COLOR_RGB2BGR))
        # return JsonResponse({
        #     'data': base64.b64encode(buffer).decode()
        # })
        return JsonResponse({
            'data': ''
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_calibration(request):
    if request.method == 'GET':
        try:
            obj = Classroom.objects.last()  # 获取最新一条
            if not obj:
                return JsonResponse({
                    'success': False,
                    'error': 'No data found'
                }, status=404)
            data = {
                'baseStations': {
                    'A': {'x': obj.baseA_x, 'y': obj.baseA_y},
                    'B': {'x': obj.baseB_x, 'y': obj.baseB_y},
                    'C': {'x': obj.baseC_x, 'y': obj.baseC_y},
                },
                'baseZ':obj.base_z,
                'servoOrigin': {'x': obj.ptz_x, 'y': obj.ptz_y, 'z': obj.ptz_z},
            }
            return JsonResponse({
                'success': True,
                **data
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    return JsonResponse({'error': 'Expect a GET request'}, status=405)

@csrf_exempt
# 上传基站和云台坐标
def upload_calibration(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # 获取最近一条记录，如果没有则创建
            record, _ = Classroom.objects.get_or_create(
                class_id=data['class_id'],
                defaults={'matrix': None}
            )
            record.baseA_x = data['baseStations']['A']['x']
            record.baseA_y = data['baseStations']['A']['y']
            record.baseB_x = data['baseStations']['B']['x']
            record.baseB_y = data['baseStations']['B']['y']
            record.baseC_x = data['baseStations']['C']['x']
            record.baseC_y = data['baseStations']['C']['y']
            record.base_z = data['baseZ']
            record.ptz_x = data['servoOrigin']['x']
            record.ptz_y = data['servoOrigin']['y']
            record.ptz_z = data['servoOrigin']['z']
            record.save()
            return JsonResponse({
                'success': True,
            }, status=200)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    return JsonResponse({'error': 'Expect a POST request'}, status=405)



# ------------------------小程序端------------------
# 生成验证码
def generate_verification_code():
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

# 验证手机号格式
def validate_phone(phone):
    pattern = r'^1[3-9]\d{9}$'
    return re.match(pattern, phone) is not None

@csrf_exempt
# 发送验证码
def send_verification_code(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone = data.get('phone')

            # 验证手机号
            if not validate_phone(phone):
                return JsonResponse({
                    'status': 'error',
                    'message': '手机号格式不正确'
                }, status=400)

            # 检查手机号是否已注册
            if User.objects.filter(phone=phone).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': '该手机号已注册'
                }, status=400)

            # 生成验证码
            code = generate_verification_code()

            # TODO: 实际应用中接入短信服务发送验证码
            # 这里仅做模拟
            print(f"验证码发送成功：{code}")

            # 创建临时用户或保存验证码
            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={
                    'username': phone,
                    'verification_code': code,
                    'verification_code_expires_at': timezone.now() + timezone.timedelta(minutes=10)
                }
            )

            if not created:
                user.verification_code = code
                user.verification_code_expires_at = timezone.now() + timezone.timedelta(minutes=10)
                user.save()

            return JsonResponse({
                'status': 'success',
                'message': '验证码发送成功'
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({'status': 'error', 'message': '无效请求'}, status=405)

@csrf_exempt
# 用户注册
def register(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone = data.get('phone')
            password = data.get('password')
            nickname = data.get('nickname', '')

            # 验证手机号和验证码
            try:
                user = User.objects.get(phone=phone)
            except User.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': '请先获取验证码'
                }, status=400)

            # 设置用户信息
            user.set_password(password)
            user.nickname = nickname
            user.phone_verified = True
            user.verification_code = None
            user.verification_code_expires_at = None
            user.save()

            return JsonResponse({
                'status': 'success',
                'message': '注册成功',
                'user': {
                    'username': user.username,
                    'nickname': user.nickname
                }
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({'status': 'error', 'message': '无效请求'}, status=405)

# 主页
def index(request):
    return HttpResponse("_____")

from django.contrib.auth import authenticate  # 导入authenticate

@csrf_exempt
# 用户登录
def user_login(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')

            # 正确验证用户：查询数据库并校验密码
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                return JsonResponse({
                    'status': 'success',
                    'message': '登录成功',
                    'user': {
                        'username': user.username,
                        'nickname': user.nickname
                    }
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': '用户名或密码错误'
                }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    return JsonResponse({'status': 'error', 'message': '无效请求'}, status=405)

# 用户注销
def user_logout(request):
    logout(request)
    return JsonResponse({'status': 'success', 'message': '注销成功'})

@csrf_exempt
# 更新用户信息
def update_profile(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': '仅支持POST请求'}, status=405)

    try:
        username = request.POST.get('username')
        if not username:
            return JsonResponse({'status': 'error', 'message': '必须提供username参数'}, status=400)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': '用户不存在'}, status=404)

        # 更新昵称
        nickname = request.POST.get('nickname')
        if nickname is not None:
            user.nickname = nickname

        # 更新头像
        avatar_file = request.FILES.get('avatar')
        if avatar_file:
            user.avatar = avatar_file

        user.save()

        return JsonResponse({
            'status': 'success',
            'message': '用户信息更新成功',
            'user': {
                'username': user.username,
                'nickname': user.nickname,
                'avatar_url': request.build_absolute_uri(user.avatar.url) if user.avatar else None,
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
# 更新头像
def update_avatar(request):
    try:
        username = request.POST.get('username')
        avatar_file = request.FILES.get('avatar')

        if not username or not avatar_file:
            return JsonResponse({'code': 400, 'message': '参数缺失'})

        # 获取用户信息
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'code': 404, 'message': '用户不存在'})

        # 删除旧头像（如果不是默认头像）
        if user.avatar and 'default.png' not in str(user.avatar):
            old_avatar_path = os.path.join(settings.MEDIA_ROOT, str(user.avatar))
            if os.path.exists(old_avatar_path):
                os.remove(old_avatar_path)

        # 保存新头像
        user.avatar = avatar_file
        user.save()

        return JsonResponse({
            'code': 200,
            'message': '头像更新成功',
            'data': {
                'avatar_url': request.build_absolute_uri(user.avatar.url) if user.avatar else None,
            }
        })
    except Exception as e:
        return JsonResponse({'code': 500, 'message': str(e)})

@csrf_exempt
@require_http_methods(["POST"])
# 更新昵称
def update_nickname(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        nickname = data.get('nickname')

        if not username or not nickname:
            return JsonResponse({'code': 400, 'message': '参数缺失'})

        # 获取用户信息
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'code': 404, 'message': '用户不存在'})

        user.nickname = nickname
        user.save()

        return JsonResponse({
            'code': 200,
            'message': '昵称更新成功',
            'data': {
                'nickname': nickname
            }
        })
    except Exception as e:
        return JsonResponse({'code': 500, 'message': str(e)})

@require_http_methods(["GET"])
# 获取用户信息
def get_user_info(request):
    try:
        username = request.GET.get('username')
        if not username:
            return JsonResponse({'code': 400, 'message': '参数缺失'})

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'code': 404, 'message': '用户不存在'})

        avatar_url = request.build_absolute_uri(user.avatar.url) if user.avatar else ''

        return JsonResponse({
            'code': 200,
            'data': {
                'nickname': user.nickname,
                'avatar_url': avatar_url
            }
        })
    except Exception as e:
        return JsonResponse({'code': 500, 'message': str(e)})

@csrf_exempt
# 用户绑定学生账号
def bind_student(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')  # 使用用户名
            student_id = data.get('student_id')

            if not username or not student_id:
                return JsonResponse({
                    'status': 'error',
                    'message': '缺少必要参数'
                }, status=400)

            # 获取用户对象
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': '用户不存在'
                }, status=404)

            # 检查用户是否已经绑定了其他学生
            if ParentStudentBinding.objects.filter(user=user, is_active=True).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': '您已经绑定了一个孩子，一个用户只能绑定一个孩子'
                }, status=400)

            # 检查学生是否已经被其他用户绑定
            if ParentStudentBinding.objects.filter(student_id=student_id, is_active=True).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': '该学号已经被其他用户绑定'
                }, status=400)

            # 检查学生是否存在
            try:
                student = Student.objects.get(student_id=student_id)
                student_name = student.name
            except Student.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': '未找到该学号对应的学生'
                }, status=404)

            # 创建绑定关系
            existing_binding = ParentStudentBinding.objects.filter(user=user, student_id=student_id).first()

            if existing_binding:
                # 如果有之前的绑定记录，重新激活它
                existing_binding.is_active = True
                existing_binding.student_name = student_name  # 更新学生姓名，以防学生信息有变更
                existing_binding.save()
                binding = existing_binding
            else:
                # 如果没有之前的绑定记录，创建新的绑定关系
                binding = ParentStudentBinding.objects.create(
                    user=user,
                    student_id=student_id,
                    student_name=student_name
                )

            return JsonResponse({
                'status': 'success',
                'message': '绑定成功',
                'data': {
                    'has_binding': True,
                    'username': user.username,
                    'student_id': student_id,
                    'student_name': student_name
                }
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({'status': 'error', 'message': '无效请求'}, status=405)

@csrf_exempt
# 解绑学生
def unbind_student(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')

            if not username:
                return JsonResponse({
                    'status': 'error',
                    'message': '缺少必要参数'
                }, status=400)

            # 获取用户对象
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': '用户不存在'
                }, status=404)

            # 查找并解除绑定关系
            try:
                binding = ParentStudentBinding.objects.get(user=user, is_active=True)
                binding.is_active = False
                binding.save()

                return JsonResponse({
                    'status': 'success',
                    'message': '解除绑定成功'
                })
            except ParentStudentBinding.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': '未找到绑定关系'
                }, status=400)

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({'status': 'error', 'message': '无效请求'}, status=405)

@csrf_exempt
# 获取绑定关系信息
def get_binding_info(request):
    if request.method == 'GET':
        try:
            username = request.GET.get('username')

            if not username:
                return JsonResponse({
                    'status': 'error',
                    'message': '缺少必要参数'
                }, status=400)

            # 获取用户对象
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': '用户不存在'
                }, status=404)

            # 查询用户绑定的学生
            try:
                binding = ParentStudentBinding.objects.get(user=user, is_active=True)
                return JsonResponse({
                    'status': 'success',
                    'data': {
                        'has_binding': True,
                        'student_id': binding.student_id,
                        'student_name': binding.student_name,
                        'binding_time': binding.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    }
                })
            except ParentStudentBinding.DoesNotExist:
                return JsonResponse({
                    'status': 'success',
                    'data': {
                        'has_binding': False
                    }
                })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({'status': 'error', 'message': '无效请求'}, status=405)

@csrf_exempt
# 由学号获取学生信息
def get_student_info(request):
    """根据学号获取学生信息"""
    if request.method == 'GET':
        try:
            student_id = request.GET.get('student_id')

            if not student_id:
                return JsonResponse({
                    'status': 'error',
                    'message': '缺少学号参数'
                }, status=400)

            try:
                student = Student.objects.get(student_id=student_id)
                return JsonResponse({
                    'status': 'success',
                    'data': {
                        'student_id': student.student_id,
                        'name': student.name
                    }
                })
            except Student.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': '未找到该学号对应的学生'
                }, status=404)

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({'status': 'error', 'message': '无效请求'}, status=405)


class BehaviorStatistics:
    # 获取时间范围
    @staticmethod
    def get_date_range(time_range):
        today = datetime.now().date()
        if time_range == '本周':  # 周一到今天
            weekday = today.weekday()  # 周一为0，周日为6
            start_date = today - timedelta(days=weekday)    # 获取周一
            end_date = today
        elif time_range == '上周':
            weekday = today.weekday()
            start_date = today - timedelta(days=weekday + 7)    #获取上周一
            end_date = today - timedelta(days=weekday + 1)
        elif time_range == '本月':    # 1号到今天
            start_date = today.replace(day=1)
            end_date = today
        elif '|' in time_range: # 自定义日期范围
            str1,str2 = time_range.split('|')
            start_date = datetime.strptime(str1, '%Y-%m-%d')
            end_date = datetime.strptime(str2, '%Y-%m-%d')
        else:
            raise ValueError(f"不支持的时间范围: {time_range}")
        return start_date, end_date

    # 获取更先的日期，用于计算趋势
    @staticmethod
    def get_previous_range(time_range):
        if time_range == '本周':
            return '上周'
        elif time_range == '上周':
            today = datetime.now().date()
            weekday = today.weekday()
            start = today - timedelta(days=weekday + 14)
            end = today - timedelta(days=weekday + 8)
            return start, end
        elif time_range == '本月':
            first_day_current = datetime.now().date().replace(day=1)
            last_day_prev = first_day_current - timedelta(days=1)
            start_prev = last_day_prev.replace(day=1)
            return start_prev, last_day_prev
        return None

    # 计算趋势
    @staticmethod
    def calculate_trend(current, previous):
        if previous == 0:
            return 0 if current == 0 else 100.0
        return round(((current - previous) / previous) * 100, 1)

    # 过滤学科
    @staticmethod
    def filter_by_subject(query, subject):
        if subject and subject != '全部学科':
            return query.filter(subject=subject)
        return query

    @classmethod
    def filter_by_time_range(cls, query, time_range):
        start, end = cls.get_date_range(time_range)
        start_datetime = timezone.make_aware(datetime.combine(start, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(end, datetime.max.time()))
        return query.filter(date__range=[start_datetime, end_datetime])

    @classmethod
    def get_bound_student(cls, username):
        try:
            user = User.objects.get(username=username)
            binding = ParentStudentBinding.objects.get(user=user, is_active=True)
            return binding.student_id
        except (User.DoesNotExist, ParentStudentBinding.DoesNotExist):
            return None

    # 获取统计数据，用于页面最上面的统计框
    @classmethod
    def get_statistics(cls, time_range, subject='全部学科', student_id=None):
        query = Behavior.objects.filter(student__student_id=student_id)
        query = cls.filter_by_time_range(query, time_range) # 时间筛选
        query = cls.filter_by_subject(query, subject)   # 学科筛选

        current_stats = query.aggregate(
            handup_count=Sum('hand_up'),
            leave_count=Sum('off_seat'),
            focus_total=Sum('focus_time'),
            record_count=Count('id')
        )
        current = {k: v or 0 for k, v in current_stats.items()}
        current['focus_average'] = current['focus_total'] / current['record_count'] if current['record_count'] > 0 else 0

        # 上一时间段
        prev_range = cls.get_previous_range(time_range)
        if not prev_range:
            return {
                'focus_time': round(current['focus_average'], 1),
                'focus_trend': 0,
                'leave_count': current['leave_count'],
                'leave_trend': 0,
                'handup_count': current['handup_count'],
                'handup_trend': 0,
            }
        elif isinstance(prev_range, str):
            prev_start, prev_end = cls.get_date_range(prev_range)
        else:
            prev_start, prev_end = prev_range
        prev_start_datetime = timezone.make_aware(datetime.combine(prev_start, datetime.min.time()))
        prev_end_datetime = timezone.make_aware(datetime.combine(prev_end, datetime.max.time()))
        prev_query = Behavior.objects.filter(
            date__range=[prev_start_datetime, prev_end_datetime]
        )###
        prev_stats = prev_query.aggregate(
            handup_prev=Sum('hand_up'),
            leave_prev=Sum('off_seat'),
            focus_prev_total=Sum('focus_time'),
            prev_record_count=Count('id')
        )
        prev = {k: v or 0 for k, v in prev_stats.items()}
        prev['focus_prev_average'] = prev['focus_prev_total'] / prev['prev_record_count'] if prev['prev_record_count'] > 0 else 0

        return {
            'focus_time': round(current['focus_average'], 1),
            'focus_trend': cls.calculate_trend(current['focus_average'], prev['focus_prev_average']),
            'leave_count': current['leave_count'],
            'leave_trend': cls.calculate_trend(current['leave_count'], prev['leave_prev']),
            'handup_count': current['handup_count'],
            'handup_trend': cls.calculate_trend(current['handup_count'], prev['handup_prev']),
        }

    # 获取一周的每日数据，用于统计图（柱状图和折线图）
    @classmethod
    def get_weekly_data(cls, time_range, subject='全部学科', student_id=None):
        query = Behavior.objects.filter(student__student_id=student_id)
        query = cls.filter_by_time_range(query, time_range)  # 时间筛选
        query = cls.filter_by_subject(query, subject)  # 学科筛选

        records = list(query)
        if time_range == '本月':  # 一月 按周算
            distraction_counts = [0] * 4
            focus_time = [0] * 4
            for record in records:
                week_of_month = (record.date.day - 1) // 7
                if 0 <= week_of_month < 4:
                    distraction_counts[week_of_month] += (record.stand_up or 0) + (record.hyperactive or 0) + (
                                record.look_around or 0) + (record.off_seat or 0) + (record.sleeping or 0)
                    focus_time[week_of_month] += record.focus_time or 0
            # 将专注时间转换为五分钟
            focus_time = [round(hours / 5, 1) for hours in focus_time]
        elif '周' in time_range:   # 一周 按天算
            distraction_counts = [0] * 5
            focus_time = [0] * 5
            for record in records:
                weekday = record.date.weekday()  # 0-6， 周一~周日
                distraction_counts[weekday] += (record.stand_up or 0) + (record.hyperactive or 0) + (
                            record.look_around or 0) + (record.off_seat or 0) + (record.sleeping or 0)
                focus_time[weekday] += record.focus_time or 0
            focus_time = [round(hours / 5, 1) for hours in focus_time]
        else:  # 自定义日期区间
            distraction_counts = []
            focus_time = []
            for record in records:
                distraction_counts.append((record.stand_up or 0) + (record.hyperactive or 0) + (
                            record.look_around or 0) + (record.off_seat or 0) + (record.sleeping or 0))
                focus_time.append(record.focus_time)
            # 限制列表长度
            if len(focus_time)>20:
                focus_time = focus_time[:20]
                distraction_counts = distraction_counts[:20]

        return {
            'focus_time': focus_time,
            'distraction_count': distraction_counts
        }

    # 获取各种分心次数，用于饼状图
    @classmethod
    def get_distraction_types(cls, time_range, subject='全部学科', student_id=None):
        query = Behavior.objects.filter(student__student_id=student_id)
        query = cls.filter_by_time_range(query, time_range)  # 时间筛选
        query = cls.filter_by_subject(query, subject)  # 学科筛选

        type_stats = query.aggregate(
            hyperactive=Sum('hyperactive'),
            look_around=Sum('look_around'),
            off_seat=Sum('off_seat'),
            sleeping=Sum('sleeping'),
            stand_up=Sum('stand_up')
        )
        return [
            {'type': '多动', 'count': type_stats['hyperactive'] or 0},
            {'type': '东张西望', 'count': type_stats['look_around'] or 0},
            {'type': '离座', 'count': type_stats['off_seat'] or 0},
            {'type': '瞌睡', 'count': type_stats['sleeping'] or 0},
            {'type': '起立', 'count': type_stats['stand_up'] or 0}
        ]

def weekly_data(request):
    try:
        get_data = request.GET
        time_range = get_data.get('time_range', '本周')
        subject = get_data.get('subject', '全部学科')
        username = get_data.get('username', None)  # 家长端通过用户名查询
        student_id = get_data.get('student_id', None)  # 通过学号直接查询
        class_id = get_data.get('class_id', None)  # 通过班级号查询
        data = None
        if username:
            student_id = BehaviorStatistics.get_bound_student(username)
            data = BehaviorStatistics.get_weekly_data(time_range, subject, student_id)
        elif student_id:
            data = BehaviorStatistics.get_weekly_data(time_range, subject, student_id)
        elif class_id:
            # 将每个学生行为数据累加
            for student in Student.objects.filter(class_id=class_id):
                student_id = student.student_id
                temp = BehaviorStatistics.get_weekly_data(time_range, subject, student_id)
                if not data:
                    data = temp
                else:
                    for key in data.keys():
                        for i in range(len(data[key])):
                            data[key][i] += temp[key][i]
        print('333',data)
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def distraction(request):
    try:
        get_data = request.GET
        time_range = get_data.get('time_range', '本周')
        subject = get_data.get('subject', '全部学科')
        username = get_data.get('username', None)  # 家长端通过用户名查询
        student_id = get_data.get('student_id', None) # 通过学号直接查询
        class_id = get_data.get('class_id', None) # 通过班级号查询
        data = None
        if username:
            student_id = BehaviorStatistics.get_bound_student(username)
            data = BehaviorStatistics.get_distraction_types(time_range, subject, student_id)
        elif student_id:
            data = BehaviorStatistics.get_distraction_types(time_range, subject, student_id)
        elif class_id:
            # 将每个学生行为数据累加
            for student in Student.objects.filter(class_id=class_id):
                student_id = student.student_id
                temp = BehaviorStatistics.get_distraction_types(time_range, subject, student_id)
                if not data:
                    data = temp
                else:
                    for i in range(len(data)):
                        data[i]['count'] += temp[i]['count']
        print('222',data)
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def statistics(request):
    try:
        get_data = request.GET
        time_range = get_data.get('time_range', '本周')
        subject = get_data.get('subject', '全部学科')
        username = get_data.get('username', None)  # 家长端通过用户名查询
        student_id = get_data.get('student_id', None)  # 通过学号直接查询
        class_id = get_data.get('class_id', None)  # 通过班级号查询
        data = None
        if username:
            student_id = BehaviorStatistics.get_bound_student(username)
            data = BehaviorStatistics.get_statistics(time_range, subject, student_id)
        elif student_id:
            data = BehaviorStatistics.get_statistics(time_range, subject, student_id)
        elif class_id:
            cnt = 0
            # 将每个学生行为数据累加
            for student in Student.objects.filter(class_id=class_id):
                student_id = student.student_id
                cnt += 1
                temp = BehaviorStatistics.get_statistics(time_range, subject, student_id)
                if not data:
                    data = temp
                elif temp:
                    for key in data.keys():
                        data[key] += temp[key]
            if data:
                for key in data.keys():
                    data[key] = round(data[key]/cnt, 1)
        print('111',data)
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def get_rank(request):
    try:
        get_data = request.GET
        time_range = get_data.get('time_range', '本周')
        subject = get_data.get('subject', '全部学科')
        class_id = get_data.get('class_id', None) # 通过班级号查询
        data = []
        if class_id:
            for student in Student.objects.filter(class_id=class_id):
                student_id = student.student_id
                temp = BehaviorStatistics.get_statistics(time_range, subject, student_id)
                data.append({})
                data[-1]['student_id'] = student_id
                data[-1]['name'] = student.name
                data[-1]['leaveTimes'] = temp['leave_count']
                data[-1]['focusTime'] = temp['focus_time']
                data[-1]['progress'] = temp['focus_trend']
        data.sort(key=lambda x: x['progress'], reverse=True)
        print('444',data)
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ---------------- 公告 / 评价 / 消息 / 请假 接口 ----------------
@require_http_methods(["GET"])
def list_notices(request):
    try:
        notices = Notice.objects.all().order_by('-created_at')[:50]
        data = [
            {
                'id': n.id,
                'title': n.title,
                'content': n.content,
                'created_at': n.created_at.strftime('%Y-%m-%d %H:%M')
            } for n in notices
        ]
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
def list_evaluations(request):
    try:
        username = request.GET.get('username')
        student_id = BehaviorStatistics.get_bound_student(username)
        if not student_id:
            return JsonResponse({'success': True, 'data': []})
        evaluations = Evaluation.objects.filter(student__student_id=student_id).order_by('-created_at')[:100]
        data = [
            {
                'id': e.id,
                'student_name': e.student.name,
                'subject': e.subject,
                'teacher': e.teacher_name,
                'comment': e.comment,
                'rating': e.rating,
                'created_at': e.created_at.strftime('%Y-%m-%d %H:%M')
            } for e in evaluations
        ]
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
def list_messages(request):
    try:
        username = request.GET.get('username')
        if not username:
            return JsonResponse({'success': True, 'data': []})
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'success': True, 'data': []})
        msgs = Message.objects.filter(user=user).order_by('-created_at')[:100]
        data = [
            {
                'id': m.id,
                'title': m.title,
                'content': m.content,
                'is_read': m.is_read,
                'created_at': m.created_at.strftime('%Y-%m-%d %H:%M')
            } for m in msgs
        ]
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_leave_request(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        reason = data.get('reason')
        leave_type = data.get('leave_type', '事假')
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if not all([username, reason, start_date, end_date]):
            return JsonResponse({'success': False, 'error': '参数缺失'}, status=400)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': '用户不存在'}, status=404)

        student_id = BehaviorStatistics.get_bound_student(username)
        if not student_id:
            return JsonResponse({'success': False, 'error': '未绑定学生'}, status=400)

        try:
            student = Student.objects.get(student_id=student_id)
        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'error': '学生不存在'}, status=404)

        leave = LeaveRequest.objects.create(
            user=user,
            student=student,
            reason=reason,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            status='待审核'
        )
        # 同时给用户生成一条消息
        Message.objects.create(user=user, title='请假提交成功', content=f'您的请假申请已提交：{start_date}~{end_date} {leave_type}')

        return JsonResponse({'success': True, 'data': {'id': leave.id}})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# daphne Tongxin.asgi:application --port 8001
# daphne Tongxin.asgi:application -p 8001 -b 192.168.1.2