import pyautogui
import time
import ctypes
from PIL import Image
import mss
import win32gui
import win32api
import win32con
import os
import logging
import sys
import configparser

# --- 日志记录设置 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bongo_cat_helper.log", mode='w', encoding='utf-8'), # 写入文件
        logging.StreamHandler(sys.stdout) # 同时在控制台显示
    ]
)

# --- 配置文件处理 ---
CONFIG_FILE = 'config.ini'

def create_default_config():
    """如果配置文件不存在，则创建一个默认的。"""
    if not os.path.exists(CONFIG_FILE):
        logging.info(f"未找到配置文件，正在创建默认的 '{CONFIG_FILE}'...")
        config = configparser.ConfigParser()
        config['Settings'] = {
            'window_title': 'BongoCat',
            'default_cat_x': '3711',
            'default_cat_y': '799',
            'gift_image': 'gift.png',
            'confidence': '0.8',
            'check_interval': '1.0',
            'search_width': '400',
            'search_height': '400'
        }
        config['TestMode'] = {
            'enabled': 'false',
            'test_image': 'wechat.png',
            'test_interval': '5.0'
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
            config.write(configfile)

def load_config():
    """从 .ini 文件加载配置。"""
    create_default_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding='utf-8')
    return config

# --- 初始化 ---
try:
    # 提高程序对高DPI屏幕的兼容性
    ctypes.windll.user32.SetProcessDPIAware()
except AttributeError:
    pass

# --- 核心功能函数 ---
def fast_foreground_click(x, y):
    """一个极快的前台点击，用于确保能点到重要目标，然后鼠标归位。"""
    original_pos = pyautogui.position()
    pyautogui.click(x, y)
    pyautogui.moveTo(original_pos)

def background_click(hwnd, x, y):
    """向指定窗口发送后台点击消息，完全不移动鼠标。"""
    try:
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        client_x = x - left
        client_y = y - top
        l_param = win32api.MAKELONG(client_x, client_y)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, l_param)
        time.sleep(0.05)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, l_param)
    except win32gui.error:
        logging.warning(f"后台点击失败，窗口句柄 {hwnd} 可能已失效。")
        pass # 窗口可能已关闭，忽略错误

def set_foreground_window(hwnd):
    """将指定句柄的窗口带到前台并设置为活动焦点。"""
    try:
        # 模拟按下并释放ALT键，以绕过Windows对SetForegroundWindow的限制
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)

        # 使用 SW_RESTORE 来处理最小化的窗口，并激活
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except win32gui.error:
        logging.warning(f"设置前台窗口失败，句柄 {hwnd} 可能已失效。")
        return False

# --- 主程序 ---
def main():
    # 从文件加载配置
    try:
        config = load_config()
        # [Settings]
        WINDOW_TITLE = config.get('Settings', 'window_title')
        CAT_X = config.getint('Settings', 'default_cat_x')
        CAT_Y = config.getint('Settings', 'default_cat_y')
        GIFT_IMAGE = config.get('Settings', 'gift_image')
        CONFIDENCE = config.getfloat('Settings', 'confidence')
        CHECK_INTERVAL = config.getfloat('Settings', 'check_interval')
        SEARCH_WIDTH = config.getint('Settings', 'search_width')
        SEARCH_HEIGHT = config.getint('Settings', 'search_height')
        # [TestMode]
        TEST_MODE_ENABLED = config.getboolean('TestMode', 'enabled')
        TEST_IMAGE = config.get('TestMode', 'test_image')
        TEST_INTERVAL = config.getfloat('TestMode', 'test_interval')
    except (configparser.NoSectionError, configparser.NoOptionError, ValueError) as e:
        logging.error(f"读取配置文件 '{CONFIG_FILE}' 出错: {e}")
        logging.error("请检查配置文件是否完整或格式正确。")
        return

    logging.info("Bongo Cat 小助手启动...")
    logging.info(f"已从 '{CONFIG_FILE}' 加载配置。")

    # 检查所需图片文件是否存在
    if not os.path.exists(GIFT_IMAGE):
        raise FileNotFoundError(f"错误: 找不到礼包图片文件 '{GIFT_IMAGE}'。")
    if TEST_MODE_ENABLED and not os.path.exists(TEST_IMAGE):
        raise FileNotFoundException(f"错误: 测试模式启用，但找不到测试图片 '{TEST_IMAGE}'。")

    # 获取用户点击坐标
    choice = input("\n是否要更新点击坐标？(直接按 Enter 使用配置文件中的默认坐标，输入任意字符后按 Enter 更新): ")
    if choice:
        input("请将鼠标移动到新的点击位置（猫咪礼包附近），然后按 Enter 确认...")
        cat_x, cat_y = pyautogui.position()
        logging.info(f"坐标已更新为: X={cat_x}, Y={cat_y}")
    else:
        cat_x, cat_y = CAT_X, CAT_Y
        logging.info(f"使用默认坐标: X={cat_x}, Y={cat_y}")

    # 计算搜索区域并绑定游戏窗口
    screen_width, screen_height = win32api.GetSystemMetrics(78), win32api.GetSystemMetrics(79)
    search_left = max(0, cat_x - SEARCH_WIDTH // 2)
    search_top = max(0, cat_y - SEARCH_HEIGHT // 2)
    actual_width = min(search_left + SEARCH_WIDTH, screen_width) - search_left
    actual_height = min(search_top + SEARCH_HEIGHT, screen_height) - search_top
    search_region = (search_left, search_top, actual_width, actual_height)
    
    logging.info(f"\n屏幕尺寸: {screen_width}x{screen_height}")
    logging.info(f"搜索区域: {search_region}")

    # 不再在此处初始化 hwnd，将其移入主循环以动态获取
    # hwnd = win32gui.FindWindow(None, WINDOW_TITLE)
    # if hwnd == 0:
    #     raise Exception(f"找不到窗口 '{WINDOW_TITLE}'。请检查游戏是否打开且标题正确。")
    # logging.info(f"成功绑定到窗口: '{WINDOW_TITLE}' (句柄: {hwnd})")
    
    if TEST_MODE_ENABLED:
        logging.info("\n*** 测试模式已启用 ***")
    
    logging.info("\n助手运行中... 将鼠标快速移动到屏幕左上角(0,0)可强制停止。")

    # 进入主循环
    gift_collected_count = 0
    animation_chars = ['-', '\\', '|', '/']
    animation_index = 0
    last_hwnd = 0 # 用于检测句柄变化
    with mss.mss() as sct:
        while True:
            # 安全退出机制 (已注释掉，以防止电脑锁屏或休眠时程序意外退出)
            # if pyautogui.position() == (0, 0):
            #     logging.info("\n检测到紧急停止信号，程序退出。")
            #     break

            # --- 动态获取窗口句柄，确保句柄始终有效 ---
            hwnd = win32gui.FindWindow(None, WINDOW_TITLE)
            if hwnd == 0:
                # 使用 \r 实现原地刷新，避免刷屏
                status_message = f"[-] 正在等待 '{WINDOW_TITLE}' 窗口出现..."
                sys.stdout.write(f"{status_message:<80}\r")
                sys.stdout.flush()
                time.sleep(CHECK_INTERVAL)
                continue # 继续下一次循环查找
            
            # 当窗口句柄发生变化时（例如游戏重启），打印一条日志
            if hwnd != last_hwnd:
                logging.info(f"\n成功绑定到窗口: '{WINDOW_TITLE}' (句柄: {hwnd})")
                last_hwnd = hwnd

            # 旧的 IsWindow 检查不再需要，因为 FindWindow 已经保证了窗口存在
            # if not win32gui.IsWindow(hwnd):
            #     logging.info("\n游戏窗口已关闭，程序退出。")
            #     break

            # 截取指定区域的屏幕
            search_area_image = None
            try:
                monitor_region = {"top": search_region[1], "left": search_region[0], "width": search_region[2], "height": search_region[3]}
                sct_img = sct.grab(monitor_region)
                search_area_image = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception as e:
                logging.error(f"截图或图像转换时发生错误: {e}")
                time.sleep(CHECK_INTERVAL)
                continue # 跳过本次循环

            if TEST_MODE_ENABLED:
                # --- 测试模式逻辑 ---
                debug_filename = "debug_test_search_area.png"
                search_area_image.save(debug_filename)
                logging.info(f"测试模式: 已保存搜索区域截图 '{debug_filename}'。")
                
                # 使用 try-except 防止因找不到图片而崩溃
                cat_location = None
                try:
                    cat_location = pyautogui.locate(TEST_IMAGE, search_area_image, confidence=CONFIDENCE)
                except pyautogui.ImageNotFoundException:
                    pass # 找不到图片是正常情况，忽略

                if cat_location:
                    logging.info("测试模式: 找到目标图片, 正在进行模仿点击。")
                    cat_center = pyautogui.center(cat_location)
                    # --- 改回前台点击 ---
                    click_x = search_region[0] + cat_center.x
                    click_y = search_region[1] + cat_center.y
                    fast_foreground_click(click_x, click_y)
                else:
                    logging.info("测试模式: 未能在截图中找到目标图片。")
                
                logging.info(f"将在 {TEST_INTERVAL} 秒后重试...")
                time.sleep(TEST_INTERVAL)

            else:
                # --- 正常模式逻辑 ---
                # 如需调试，可取消下面一行的注释来保存每次的截图
                # search_area_image.save("debug_normal_search_area.png")

                # 尝试定位礼包
                gift_location = None
                try:
                    # 使用 grayscale=True 可以提高识别速度和准确性
                    gift_location = pyautogui.locate(GIFT_IMAGE, search_area_image, confidence=CONFIDENCE, grayscale=True)
                except pyautogui.ImageNotFoundException:
                    pass # 找不到是正常情况，直接忽略
                except Exception as e:
                    logging.error(f"在定位礼包图片时发生未知错误: {e}")
                    pass

                if gift_location:
                    # 清理之前的状态行
                    print("\n" + "="*40) 
                    logging.info(f"检测到礼包，尝试收取...")
                    
                    # --- 同样改回前台点击 ---
                    gift_center = pyautogui.center(gift_location)
                    click_x = search_region[0] + gift_center.x
                    click_y = search_region[1] + gift_center.y
                    
                    fast_foreground_click(click_x, click_y)
                    
                    logging.info("已点击礼包，暂停5秒后进行确认...")
                    time.sleep(5.0)

                    # 5秒后再次截图确认
                    try:
                        sct_img_check = sct.grab(monitor_region)
                        check_area_image = Image.frombytes("RGB", sct_img_check.size, sct_img_check.bgra, "raw", "BGRX")
                        pyautogui.locate(GIFT_IMAGE, check_area_image, confidence=CONFIDENCE, grayscale=True)
                        logging.warning("确认失败：礼包仍然存在。本次收取不计数。")
                    except pyautogui.ImageNotFoundException:
                        gift_collected_count += 1
                        logging.info(f"确认成功：礼包已消失！(累计收取: {gift_collected_count})")
                    except Exception as e:
                        logging.error(f"确认礼包时发生错误: {e}")
                    
                    logging.info("="*40 + "\n")

                else:
                    # 未找到礼包时，显示旋转动画
                    char = animation_chars[animation_index]
                    status_message = f"[{char}] 正在识别... (已收取: {gift_collected_count})"
                    # 使用 logging.info 并通过 \r 实现原地刷新
                    sys.stdout.write(f"{status_message:<80}\r")
                    sys.stdout.flush()
                    animation_index = (animation_index + 1) % len(animation_chars)
                    
                    time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.info("\n程序已手动停止。")
    except Exception as e:
        logging.error(f"\n程序因未捕获的严重错误而终止: {e}", exc_info=True)
    finally:
        input("\n按 Enter 键退出...")