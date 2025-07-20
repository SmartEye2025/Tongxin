from django.contrib.auth import login, logout
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.http import JsonResponse
from django.http import HttpResponse
from camera.models import *
from camera.mqtt_client import client
from camera.consumers import frame_queue

from .models import ParentStudentBinding
from .models import Student
from .models import User

import cv2
import base64
import json
import random
import re
import os
from django.conf import settings

#  获取学生列表
def get_student_list(request):
    if request.method == 'GET':
        studentList = []
        for a in Student.objects.all():
            studentList.append({
                'student_id': a.student_id,
                'uwb_id': a.uwb_id,
                'name': a.name,
                'age': a.age,
                'specialNeeds':a.speciality.split(' ')
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
        student.name = data['name']
        student.age = data['age']
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
            name=data['name'],
            age=data['age'],
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
        # 添加超时避免永久阻塞
        frame = frame_queue.get(timeout=2.0)  # 2秒超时
        _, buffer = cv2.imencode('.jpg', frame)
        return JsonResponse({
            'data': base64.b64encode(buffer).decode()
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


@csrf_exempt
# 用户登录
def user_login(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')

            user = User(username=username, password=password)

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



# daphne Tongxin.asgi:application --port 8001
# daphne Tongxin.asgi:application -p 8001 -b 192.168.1.2