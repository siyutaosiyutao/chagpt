"""
小红书订单同步服务
使用 Cookie 认证自动提取订单号
"""

import time
import re
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from database import Order, XHSConfig


class XHSOrderSyncService:
    """小红书订单同步服务（使用 Cookie 认证）"""
    
    def __init__(self, headless=True):
        """
        初始化同步服务
        
        Args:
            headless: 是否使用无头模式
        """
        self.driver = None
        self.headless = headless
        self.order_url = "https://ark.xiaohongshu.com/app-order/order/query"
        
    def setup_driver(self):
        """配置并启动Chrome浏览器"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 设置用户代理
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print("✓ 浏览器已启动")
            return True
        except WebDriverException as e:
            print(f"✗ 浏览器启动失败: {str(e)}")
            return False
    
    def inject_cookies(self, cookies_dict):
        """
        注入 Cookie 到浏览器
        
        Args:
            cookies_dict: Cookie 字典或列表
        """
        try:
            # 先访问域名，否则无法设置Cookie
            self.driver.get("https://ark.xiaohongshu.com")
            time.sleep(2)
            
            # 如果是字符串，尝试解析为JSON
            if isinstance(cookies_dict, str):
                cookies_dict = json.loads(cookies_dict)
            
            # 如果是列表形式的Cookie
            if isinstance(cookies_dict, list):
                for cookie in cookies_dict:
                    try:
                        self.driver.add_cookie(cookie)
                    except Exception as e:
                        print(f"添加Cookie失败: {cookie.get('name', 'unknown')} - {e}")
            
            # 如果是字典形式的Cookie
            elif isinstance(cookies_dict, dict):
                for name, value in cookies_dict.items():
                    cookie = {
                        'name': name,
                        'value': value,
                        'domain': '.xiaohongshu.com'
                    }
                    try:
                        self.driver.add_cookie(cookie)
                    except Exception as e:
                        print(f"添加Cookie失败: {name} - {e}")
            
            print("✓ Cookie 注入成功")
            return True
            
        except Exception as e:
            print(f"✗ Cookie 注入失败: {str(e)}")
            return False
    
    def navigate_to_orders(self):
        """访问订单页面"""
        try:
            print(f"正在访问订单页面: {self.order_url}")
            self.driver.get(self.order_url)
            time.sleep(3)
            
            # 检查是否成功访问（不在登录页面）
            current_url = self.driver.current_url
            if 'login' in current_url.lower():
                print("✗ Cookie已过期或无效，需要重新登录")
                return False
            
            # 等待订单容器加载
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.order-container, div[class*='order']"))
                )
                print("✓ 订单页面加载成功")
                return True
            except TimeoutException:
                print("✗ 订单容器未找到，可能页面结构已变化")
                return False
                
        except Exception as e:
            print(f"✗ 访问订单页面失败: {str(e)}")
            return False
    
    def extract_orders_from_page(self):
        """从当前页面提取【已发货未签收】状态的订单号"""
        valid_orders = set()
        
        try:
            # 使用 JavaScript 从渲染后的 DOM 中提取订单和状态
            # 因为 page_source 可能没有经过 JS 渲染，状态文本可能不存在
            result_json = self.driver.execute_script("""
                const pageSource = document.documentElement.outerHTML;
                const blocks = pageSource.split(/订单号[：:]/);
                const results = [];
                
                for (let i = 1; i < blocks.length; i++) {
                    const block = blocks[i];
                    const orderMatch = block.match(/P\\d{15,}/);
                    if (!orderMatch) continue;
                    
                    const orderNum = orderMatch[0];
                    const context = block.substring(0, 1000);
                    
                    let status = '未知';
                    if (context.includes('已发货未签收')) status = '已发货未签收';
                    else if (context.includes('已取消')) status = '已取消';
                    else if (context.includes('已完成')) status = '已完成';
                    else if (context.includes('待付款') || context.includes('未付款')) status = '待付款';
                    else if (context.includes('待发货')) status = '待发货';
                    else if (context.includes('已签收')) status = '已签收';
                    
                    results.push({
                        order: orderNum,
                        status: status
                    });
                }
                
                return JSON.stringify(results);
            """)
            
            orders_data = json.loads(result_json)
            
            # 过滤并打印日志
            for item in orders_data:
                order_num = item['order']
                status = item['status']
                
                if status == '已发货未签收':
                    valid_orders.add(order_num)
                    print(f"  ✓ 找到符合条件的订单: {order_num} (已发货未签收)")
                elif status == '已取消':
                    print(f"  ✗ 过滤订单: {order_num} (已取消)")
                elif status == '已完成':
                    print(f"  ✗ 过滤订单: {order_num} (已完成)")
                elif status in ['待付款', '未付款']:
                    print(f"  ✗ 过滤订单: {order_num} (待付款)")
                elif status == '待发货':
                    print(f"  ✗ 过滤订单: {order_num} (待发货)")
                elif status == '已签收':
                    print(f"  ✗ 过滤订单: {order_num} (已签收)")
                else:
                    print(f"  ? 跳过订单: {order_num} (状态未识别: {status})")
            
            result = list(valid_orders)
            
            # 调试: 如果没找到符合条件的订单，保存完整数据
            if not result:
                print(f"  ⚠️ 未找到【已发货未签收】的订单")
                print(f"  ℹ️  总共提取到 {len(orders_data)} 个订单")
                # 保存 page_source 供调试
                with open("debug_page_source.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                # 保存提取到的订单数据
                with open("debug_orders.json", "w", encoding="utf-8") as f:
                    json.dump(orders_data, f, ensure_ascii=False, indent=2)
                print(f"  ℹ️  已保存 debug_page_source.html 和 debug_orders.json")
            
            return result
            
        except Exception as e:
            print(f"✗ 提取订单时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def scroll_and_load_all(self, max_scrolls=50, scroll_pause=2):
        """
        滚动页面加载所有订单
        
        Args:
            max_scrolls: 最大滚动次数
            scroll_pause: 每次滚动后的等待时间（秒）
        
        Returns:
            list: 所有提取到的订单号
        """
        all_orders = set()
        scroll_count = 0
        no_new_orders_count = 0
        
        print("\n开始提取订单...")
        
        # 查找可滚动的容器
        try:
            order_container = self.driver.find_element(By.CSS_SELECTOR, "div.order-container, div[scrollable='true']")
            print("✓ 找到订单容器")
        except:
            print("使用整个页面进行滚动")
            order_container = None
        
        while scroll_count < max_scrolls:
            # 提取当前页面的订单
            current_orders = self.extract_orders_from_page()
            
            # 添加到总集合
            old_count = len(all_orders)
            all_orders.update(current_orders)
            new_count = len(all_orders) - old_count
            
            if new_count == 0:
                no_new_orders_count += 1
                if no_new_orders_count >= 3:
                    print("\n✓ 已连续3次未发现新订单，提取完成")
                    break
            else:
                no_new_orders_count = 0
                print(f"  本次新增 {new_count} 个订单，当前共 {len(all_orders)} 个")
            
            # 滚动页面
            if order_container:
                self.driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight",
                    order_container
                )
            else:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            scroll_count += 1
            print(f"  滚动 {scroll_count}/{max_scrolls}")
            time.sleep(scroll_pause)
        
        print(f"\n✓ 提取完成！共找到 {len(all_orders)} 个订单号")
        return list(all_orders)
    
    def sync_with_cookies(self, cookies, max_scrolls=50):
        """
        使用Cookie同步订单
        
        Args:
            cookies: Cookie字符串或字典
            max_scrolls: 最大滚动次数
        
        Returns:
            dict: {'success': bool, 'new_orders': int, 'total_orders': int, 'error': str}
        """
        try:
            # 1. 启动浏览器
            if not self.setup_driver():
                return {'success': False, 'error': '浏览器启动失败'}
            
            # 2. 注入Cookie
            if not self.inject_cookies(cookies):
                return {'success': False, 'error': 'Cookie注入失败'}
            
            # 3. 访问订单页面
            if not self.navigate_to_orders():
                return {'success': False, 'error': '订单页面访问失败或Cookie已过期'}
            
            # 4. 提取所有订单
            order_numbers = self.scroll_and_load_all(max_scrolls=max_scrolls)
            
            if not order_numbers:
                return {'success': False, 'error': '未提取到任何订单'}
            
            # 5. 保存到数据库
            result = Order.batch_create(order_numbers)
            
            print(f"\n数据库同步结果:")
            print(f"  新增订单: {result['created']}")
            print(f"  已存在订单: {result['skipped']}")
            print(f"  总订单数: {len(order_numbers)}")
            
            return {
                'success': True,
                'new_orders': result['created'],
                'skipped_orders': result['skipped'],
                'total_orders': len(order_numbers),
                'order_numbers': order_numbers
            }
            
        except Exception as e:
            import traceback
            error_msg = f"同步过程出错: {str(e)}\n{traceback.format_exc()}"
            print(f"✗ {error_msg}")
            return {'success': False, 'error': error_msg}
            
        finally:
            self.close()
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
                print("✓ 浏览器已关闭")
            except:
                pass


def sync_orders_from_db():
    """
    从数据库读取Cookie配置并执行同步
    
    Returns:
        dict: 同步结果
    """
    # 获取配置
    config = XHSConfig.get()
    
    if not config:
        return {'success': False, 'error': '未找到小红书配置'}
    
    if not config['cookies']:
        return {'success': False, 'error': '未配置Cookie'}
    
    # 执行同步
    print("=" * 60)
    print("开始同步小红书订单...")
    print("=" * 60)
    
    service = XHSOrderSyncService(headless=True)
    
    try:
        # 解析Cookie
        cookies = json.loads(config['cookies'])
        
        # 执行同步
        result = service.sync_with_cookies(cookies, max_scrolls=100)
        
        if result['success']:
            # 更新最后同步时间
            XHSConfig.update_last_sync()
            print("\n✓ 同步成功！数据库已更新")
        else:
            # 记录错误
            XHSConfig.record_error(result.get('error', '未知错误'))
            print(f"\n✗ 同步失败: {result.get('error')}")
        
        return result
        
    except json.JSONDecodeError:
        error_msg = 'Cookie格式错误，无法解析JSON'
        XHSConfig.record_error(error_msg)
        return {'success': False, 'error': error_msg}
    
    except Exception as e:
        error_msg = f"同步异常: {str(e)}"
        XHSConfig.record_error(error_msg)
        return {'success': False, 'error': error_msg}


if __name__ == "__main__":
    # 测试同步
    result = sync_orders_from_db()
    
    print("\n" + "=" * 60)
    if result['success']:
        print(f"✅ 同步成功！")
        print(f"  新增订单: {result['new_orders']}")
        print(f"  已存在订单: {result['skipped_orders']}")
        print(f"  总订单数: {result['total_orders']}")
    else:
        print(f"❌ 同步失败: {result['error']}")
    print("=" * 60)
