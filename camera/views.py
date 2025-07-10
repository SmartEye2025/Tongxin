from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.http import HttpResponse
import json
from camera.models import *
from django.forms import model_to_dict
import time
from camera.mqtt_client import client

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
            timestamp = data.get('timestamp')
            # 存入数据库
            saved_matrix = TransformationMatrix.objects.create(
                matrix=matrix,
                timestamp=timestamp
            )

            return JsonResponse({
                'success': True,
                'id': saved_matrix.id
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
            latest_matrix = TransformationMatrix.objects.last()  # 获取最新一条
            if not latest_matrix:
                return JsonResponse({
                    'success': False,
                    'error': 'No matrix found'
                }, status=404)

            return JsonResponse({
                'success': True,
                'matrix': latest_matrix.matrix,
                'timestamp': latest_matrix.timestamp.isoformat()
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    return JsonResponse({'error': 'Expect a GET request'}, status=405)
# daphne Tongxin.asgi:application --port 8000