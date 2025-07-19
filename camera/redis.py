import redis
from django.conf import settings


class RedisManager:
    def __init__(self):
        self.conn = redis.StrictRedis.from_url(
            settings.CACHES["default"]["LOCATION"],
            decode_responses=True
        )

    def set_var(self, key, value, ttl=None):
        """设置变量"""
        self.conn.set(key, value)
        if ttl:
            self.conn.expire(key, ttl)

    def get_var(self, key, default=None):
        """获取变量"""
        val = self.conn.get(key)
        return val if val is not None else default

    def publish(self, channel, message):
        """发布消息"""
        self.conn.publish(channel, message)


# 全局实例
redis_manager = RedisManager()