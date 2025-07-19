from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.http import HttpResponse
import json
from camera.models import *
from django.forms import model_to_dict
import time
from camera.mqtt_client import client
from camera.consumers import frame_queue
import cv2
import base64

#  获取学生列表
def get_studenList(request):
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
def edit_studentInfo(request):
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




# daphne Tongxin.asgi:application --port 8001
# daphne Tongxin.asgi:application -p 8001 -b 192.168.1.2