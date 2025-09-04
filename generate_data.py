import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Tongxin.settings")
django.setup()

import datetime
import random  # 移到顶部统一导入
from camera.models import Behavior, Student  # 确保同时导入 Student
import string

start_date = datetime.date(2025, 7, 1)
end_date = datetime.date(2025, 8, 31)
delta = datetime.timedelta(days=1)
subjects = ["语文", "数学", "外语", "美术"]
subject_weights = [0.3, 0.3, 0.2, 0.2]  # 权重移到顶部，避免重复定义
test_data = []
current_date = start_date

# 获取已存在的学生（假设已生成10个学生）
students = Student.objects.all()
if not students.exists():
    raise ValueError("请先生成学生数据！数据库中没有找到学生记录")

while current_date <= end_date:
    if current_date.weekday() < 5:  # 周一到周五
        num_records = 2 if current_date.weekday() in [1, 3] else 3
        for _ in range(num_records):
            # 为每个学生生成行为数据
            for student in students:
                subject = random.choices(subjects, weights=subject_weights)[0]
                hour = random.randint(9, 16)
                minute = random.randint(0, 59)
                record_datetime = datetime.datetime.combine(
                    current_date,
                    datetime.time(hour, minute)
                )

                # 根据学科生成行为数据（保持原有逻辑）
                if subject == "语文":
                    focus_time = round(random.uniform(30, 45), 1)
                    hand_up = random.randint(2, 5)
                    hyperactive = random.randint(1, 3)
                    look_around = random.randint(0, 2)
                    off_seat = random.randint(0, 1)
                    sleeping = random.randint(0, 1)
                    stand_up = random.randint(0, 2)
                elif subject == "数学":
                    focus_time = round(random.uniform(25, 40), 1)
                    hand_up = random.randint(1, 4)
                    hyperactive = random.randint(2, 4)
                    look_around = random.randint(1, 3)
                    off_seat = random.randint(0, 2)
                    sleeping = random.randint(0, 1)
                    stand_up = random.randint(0, 1)
                elif subject == "外语":
                    focus_time = round(random.uniform(20, 35), 1)
                    hand_up = random.randint(1, 3)
                    hyperactive = random.randint(2, 5)
                    look_around = random.randint(1, 4)
                    off_seat = random.randint(0, 2)
                    sleeping = random.randint(0, 2)
                    stand_up = random.randint(0, 1)
                else:  # 美术
                    focus_time = round(random.uniform(35, 50), 1)
                    hand_up = random.randint(3, 7)
                    hyperactive = random.randint(0, 2)
                    look_around = random.randint(1, 4)
                    off_seat = random.randint(0, 2)
                    sleeping = random.randint(0, 2)
                    stand_up = random.randint(0, 3)

                test_data.append({
                    "date": record_datetime,
                    "subject": subject,
                    "student": student,  # 关联学生
                    "hand_up": hand_up,
                    "focus_time": focus_time,
                    "hyperactive": hyperactive,
                    "look_around": look_around,
                    "off_seat": off_seat,
                    "sleeping": sleeping,
                    "stand_up": stand_up
                })
    current_date += delta

# 添加学生的行为数据
def insert_test_data():
    Behavior.objects.bulk_create([
        Behavior(**data) for data in test_data
    ])
    print(f"成功插入 {len(test_data)} 条测试数据")

# 生成学生数据
def generate_students(num_students=10):
    students = []
    for i in range(1, num_students + 1):
        name = f"学生{i}"
        student_id = f"S{i:04d}"
        uwb_id = f"UWB{i:04d}"
        age = random.randint(7, 18)
        speciality = random.choice(["无", "近视", "多动", "听力障碍", "色弱", "无"])
        seat_x = round(random.uniform(0.0, 10.0), 2)
        seat_y = round(random.uniform(0.0, 10.0), 2)
        students.append(Student(
            name=name,
            student_id=student_id,
            uwb_id=uwb_id,
            age=age,
            speciality=speciality,
            seat_x=seat_x,
            seat_y=seat_y
        ))
    Student.objects.bulk_create(students)
    print(f"成功生成 {num_students} 个学生数据")

# 在这里添加要使用的函数，终端输入python generate_data.py即可
if __name__ == "__main__":
    insert_test_data()