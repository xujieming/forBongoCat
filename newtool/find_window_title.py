# find_window_title.py
import win32gui

def enum_window_callback(hwnd, all_windows):
    """
    EnumWindows的回调函数。
    检查窗口是否可见且有标题，然后添加到列表中。
    """
    if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) != '':
        title = win32gui.GetWindowText(hwnd)
        all_windows.append(title)

def list_all_window_titles():
    """列出所有可见窗口的标题。"""
    windows = []
    try:
        # EnumWindows会为每个顶级窗口调用一次回调函数
        win32gui.EnumWindows(enum_window_callback, windows)
        
        if not windows:
            print("没有找到任何可见的窗口。")
            return

        print("--- 所有可见窗口的标题列表 ---")
        # 排序后打印，方便查找
        for title in sorted(windows):
            print(f"'{title}'")
        print("---------------------------------")
        print("\n请从上面的列表中找到你的游戏窗口标题，然后完整复制它（包括单引号内的所有内容）。")

    except Exception as e:
        print(f"出错了: {e}")
        print("请确认你已经运行 'pip install pywin32'")

if __name__ == "__main__":
    # 确保游戏窗口已经打开
    print("正在查找所有可见窗口...")
    list_all_window_titles()
    input("\n按 Enter 键退出...")