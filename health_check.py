import os
import time
import threading
import requests
from datetime import datetime

class HealthCheck:
    """
    健康检查和自动恢复模块，用于解决Render免费服务的503问题
    """
    def __init__(self, app, check_interval=300):
        """
        初始化健康检查模块
        
        Args:
            app: Flask应用实例
            check_interval: 健康检查间隔（秒），默认5分钟
        """
        self.app = app
        self.check_interval = check_interval
        self.last_check_time = None
        self.service_url = os.environ.get('SERVICE_URL', 'http://localhost:5000')
        self.is_running = False
    
    def add_health_endpoints(self):
        """
        添加健康检查端点到Flask应用
        """
        @self.app.route('/health')
        def health_check():
            self.last_check_time = datetime.now()
            return {
                'status': 'ok',
                'timestamp': self.last_check_time.isoformat(),
                'uptime': self._get_uptime()
            }
        
        @self.app.route('/ping')
        def ping():
            self.last_check_time = datetime.now()
            return 'pong'
    
    def _get_uptime(self):
        """
        获取服务运行时间
        """
        if not hasattr(self, 'start_time'):
            self.start_time = datetime.now()
        
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{int(days)}天{int(hours)}小时{int(minutes)}分钟{int(seconds)}秒"
    
    def start_self_ping(self):
        """
        启动自我ping线程，保持服务活跃
        """
        if self.is_running:
            return
        
        self.is_running = True
        self.start_time = datetime.now()
        self.last_check_time = self.start_time
        
        def ping_worker():
            while self.is_running:
                try:
                    # 计算距离上次检查的时间
                    if self.last_check_time:
                        time_since_last_check = (datetime.now() - self.last_check_time).total_seconds()
                        # 如果最近有外部请求，可以延迟自我ping
                        if time_since_last_check < self.check_interval:
                            time.sleep(min(60, self.check_interval - time_since_last_check))
                            continue
                    
                    # 执行自我ping
                    response = requests.get(f"{self.service_url}/ping")
                    if response.status_code == 200:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 自我健康检查成功")
                    else:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 自我健康检查失败: {response.status_code}")
                except Exception as e:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 自我健康检查异常: {str(e)}")
                
                # 等待下一次检查
                time.sleep(self.check_interval)
        
        # 启动健康检查线程
        health_thread = threading.Thread(target=ping_worker)
        health_thread.daemon = True
        health_thread.start()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 健康检查服务已启动，间隔: {self.check_interval}秒")

def setup_health_check(app, check_interval=300):
    """
    设置健康检查，在主应用中调用此函数
    
    Args:
        app: Flask应用实例
        check_interval: 健康检查间隔（秒）
    
    Returns:
        HealthCheck实例
    """
    health_check = HealthCheck(app, check_interval)
    health_check.add_health_endpoints()
    health_check.start_self_ping()
    return health_check