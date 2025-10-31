"""
测试自动踢人功能
"""
from database import AutoKickConfig, KickLog

print("=" * 60)
print("测试自动踢人配置")
print("=" * 60)

# 1. 获取配置
config = AutoKickConfig.get()
print(f"\n当前配置:")
print(f"  启用状态: {config['enabled']}")
print(f"  检测间隔: {config['check_interval_min']}-{config['check_interval_max']} 秒")
print(f"  运行时间: {config['start_time']} - {config['end_time']}")
print(f"  时区: {config['timezone']}")

# 2. 更新配置
print(f"\n更新配置...")
AutoKickConfig.update(
    enabled=True,
    check_interval_min=90,
    check_interval_max=120,
    start_time='09:00',
    end_time='22:00'
)

# 3. 再次获取配置
config = AutoKickConfig.get()
print(f"\n更新后的配置:")
print(f"  启用状态: {config['enabled']}")
print(f"  检测间隔: {config['check_interval_min']}-{config['check_interval_max']} 秒")
print(f"  运行时间: {config['start_time']} - {config['end_time']}")

# 4. 查看踢人日志
print(f"\n踢人日志:")
logs = KickLog.get_all(10)
if logs:
    for log in logs:
        status = "✅ 成功" if log['success'] else f"❌ 失败: {log['error_message']}"
        print(f"  [{log['created_at']}] {log['email']} - {status}")
else:
    print(f"  暂无日志")

print(f"\n{'=' * 60}")
print(f"✅ 测试完成!")
print(f"{'=' * 60}")

