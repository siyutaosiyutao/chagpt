"""
小红书订单同步定时任务调度器
使用 APScheduler 定时执行订单同步
"""

import time
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from database import XHSConfig
from xhs_order_sync import sync_orders_from_db


class XHSSchedulerService:
    """小红书订单同步调度服务"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self.last_sync_result = None
        self.lock = threading.Lock()
        
    def sync_job(self):
        """同步任务"""
        with self.lock:
            if self.is_running:
                print("⚠️  上一次同步仍在进行中，跳过本次同步")
                return
            
            self.is_running = True
        
        try:
            print(f"\n{'='*60}")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行定时同步...")
            print(f"{'='*60}")
            
            result = sync_orders_from_db()
            self.last_sync_result = {
                **result,
                'sync_time': datetime.now().isoformat()
            }
            
            if result['success']:
                print(f"✅ 定时同步成功")
            else:
                print(f"❌ 定时同步失败: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ 定时同步异常: {str(e)}")
            self.last_sync_result = {
                'success': False,
                'error': str(e),
                'sync_time': datetime.now().isoformat()
            }
        finally:
            with self.lock:
                self.is_running = False
    
    def start(self):
        """启动调度器"""
        # 获取配置
        config = XHSConfig.get()
        
        if not config:
            print("❌ 未找到小红书配置，调度器启动失败")
            return False
        
        if not config['sync_enabled']:
            print("ℹ️  小红书订单同步未启用")
            return False
        
        if not config['cookies']:
            print("❌ 未配置Cookie，调度器启动失败")
            return False
        
        interval_hours = config['sync_interval_hours'] or 6
        
        # 添加定时任务
        self.scheduler.add_job(
            self.sync_job,
            trigger=IntervalTrigger(hours=interval_hours),
            id='xhs_order_sync',
            name='小红书订单同步',
            replace_existing=True
        )
        
        # 启动调度器
        self.scheduler.start()
        
        print(f"✅ 小红书订单同步调度器已启动")
        print(f"   同步间隔: 每 {interval_hours} 小时")
        print(f"   下次同步: {datetime.now().replace(microsecond=0)}")
        
        return True
    
    def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("✅ 小红书订单同步调度器已停止")
        
    def trigger_now(self):
        """立即触发一次同步"""
        print("🚀 手动触发订单同步...")
        
        # 在新线程中执行，避免阻塞
        threading.Thread(target=self.sync_job, daemon=True).start()
        
        return {'success': True, 'message': '同步任务已启动'}
    
    def get_status(self):
        """获取调度器状态"""
        config = XHSConfig.get()
        
        return {
            'enabled': config['sync_enabled'] if config else False,
            'interval_hours': config['sync_interval_hours'] if config else 6,
            'last_sync_at': config['last_sync_at'] if config else None,
            'last_error': config['last_error'] if config else None,
            'error_count': config['error_count'] if config else 0,
            'is_running': self.is_running,
            'last_sync_result': self.last_sync_result,
            'scheduler_running': self.scheduler.running if self.scheduler else False
        }
    
    def reload_config(self):
        """重新加载配置并重启调度器"""
        if self.scheduler.running:
            self.stop()
        
        return self.start()


# 全局调度器实例
xhs_scheduler = XHSSchedulerService()


if __name__ == "__main__":
    print("小红书订单同步调度器")
    print("="*60)
    
    # 启动调度器
    if xhs_scheduler.start():
        print("\n调度器运行中...")
        print("按 Ctrl+C 停止")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n正在停止调度器...")
            xhs_scheduler.stop()
            print("调度器已停止")
    else:
        print("调度器启动失败")
