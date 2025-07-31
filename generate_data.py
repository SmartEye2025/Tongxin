import datetime
from camera.models import Behavior
start_date = datetime.date(2025, 7, 31)
end_date = datetime.date(2025, 9, 30)
delta = datetime.timedelta(days=1)
subjects = ["语文", "数学", "外语", "美术"]
test_data = []
current_date = start_date
while current_date <= end_date:
    print(f"{current_date} and {end_date}")
    if current_date.weekday() < 5:  # 0-4代表周一到周五
        num_records = 2 if current_date.weekday() in [1, 3] else 3
        for i in range(num_records):
            import random
            subject_weights = [0.3, 0.3, 0.2, 0.2]  # 权重分布
            subject = random.choices(subjects, weights=subject_weights)[0]
            hour = random.randint(9, 16)
            minute = random.randint(0, 59)
            record_datetime = datetime.datetime.combine(
                current_date,
                datetime.time(hour, minute)
            )
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
                "hand_up": hand_up,
                "focus_time": focus_time,
                "hyperactive": hyperactive,
                "look_around": look_around,
                "off_seat": off_seat,
                "sleeping": sleeping,
                "stand_up": stand_up
            })
    current_date += delta

def insert_test_data():
    for data in test_data:
        Behavior.objects.create(**data)
    print(f"成功插入 {len(test_data)} 条测试数据")

# 修改数据
from django.db import models
from camera.models import Behavior
# 将所有记录的 focus_time 翻倍
Behavior.objects.update(focus_time=models.F('focus_time') / 2)