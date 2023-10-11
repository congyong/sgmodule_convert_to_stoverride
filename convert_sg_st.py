import re
import os
import random
import time
import string
import webbrowser
import ttkbootstrap as ttk
import pyautogui
import yaml
from tkinter import messagebox
import threading

def click(img):
    """点击图片中心"""
    time.sleep(1) 
    enter_mt_btn = pyautogui.locateCenterOnScreen(img,confidence=0.8)  # 锁定位置
    print(enter_mt_btn) 
    if enter_mt_btn:
        pyautogui.moveTo(enter_mt_btn)  # 移动到这里
        pyautogui.click()  # 单击一下
    return enter_mt_btn

def enter_wd(msg):
    """输入信息"""
    pyautogui.write(msg)
   # time.sleep(2)

def enter_password(password):
 
 if os.name == 'nt':
    import win32gui
    for i in range(30):
        handle_root = win32gui.FindWindow('Qt5158QWindowIcon','加入会议')
        print(handle_root)
        if handle_root:
            break
        else:
            time.sleep(1)
    if handle_root:
        win32gui.SetForegroundWindow(handle_root)
        enter_wd(password)

        rect = win32gui.GetWindowRect(handle_root)
        #根据按钮相对坐标 定位button
        width = rect[2] - rect[0]  
        height = rect[3] - rect[1]
        x = width * 217 / 300 + rect[0]
        y = height * 312 / 350  + rect[1]
        pyautogui.moveTo(x,y)
        pyautogui.click(x, y)
        #判断窗口还在不在 如果还在 再点击几次-- (其实这段时间在联网验证密码--)
        if win32gui.SetForegroundWindow(handle_root):
            for i in range(30):
                if win32gui.SetForegroundWindow(handle_root):
                    pyautogui.click(x, y)
                    time.sleep(0.1)

     
 else:  # linux/macos
        entm= click("entm.png")  #根据底库图像对比查找按钮.可以加上缩放比例TODO 否则换电脑得重新截图做底库.
        if entm:
        #tab 换到密码框位置
            pyautogui.press('tab')  #-- 用户名
            pyautogui.press('tab')  #-- 密码
            enter_wd(password)
            #定位到开始会议
            pyautogui.moveTo(entm) 
            pyautogui.click()
        



def parse_text(text):
    meeting_code = re.search(r'(\d+-\d+-\d+)', text) 
    if meeting_code:
        meeting_code = meeting_code.group(1).replace('-', '')
    else:
        meeting_code = re.search(r'p/(\d+)', text)
        if meeting_code:
            meeting_code = meeting_code.group(1)
    
    password = re.search(r'会议密码.\s*(\d+)', text)
    if password:
        password = password.group(1)
    else:
        password = ''
    
    return meeting_code, password

def open_meeting(meeting_code, launch_id):
    url = f'wemeet://page/inmeeting?meeting_code={meeting_code}&launch_id={launch_id}&rs=5'
    webbrowser.open(url)

def load_history():
    if os.path.exists("meeting_rec.yaml"):
        with open("meeting_rec.yaml", "r") as file:
            history = yaml.safe_load(file)
    else:
        history = []
    return history

def save_history(history):
    with open("meeting_rec.yaml", "w") as file:
        yaml.dump(history, file)

def load_and_display_history():
    # 加载历史记录
    history = load_history()

    # 更新Label显示最新的内容
    if history:
        history_text.delete('1.0', ttk.END)  # 清空Text控件内容
        history_text.insert('1.0', "当前历史记录：\n"+history[0])  # 插入最新的历史记录
    else:
        history_text.delete('1.0', ttk.END)  # 清空Text控件内容
        history_text.insert('1.0', "empty history\n")  # 插入最新的历史记录

# 更新历史记录的显示在Label上
def update_history_text(value):
    value = int(round(float(value)))   # 将value转换为整数
    history_data = load_history()
    
    if value < 0:
        value = 0
    elif value >= len(history_data):
        value = len(history_data) - 1

    #history_text.config(text="当前历史记录：" + history_data[value])
    if history_data :
        history_text.delete('1.0', ttk.END)  # 清空Text控件内容
        history_text.insert('1.0', "当前历史记录：\n"+history_data[value])  # 插入最新的历史记录


def start_meeting():
    text = input_text.get('1.0', 'end')
        # 如果输入文本为空，使用label的内容代替
    if not text  or text=='\n':
        text = history_text.get("1.0", "end-1c")  # 获取Text控件中的文本
        text = text.replace("当前历史记录：\n", "").strip()

    meeting_code, password = parse_text(text)
    result_text['text'] = f'当前会议号为:{meeting_code}   当前密码为:{password}'
    launch_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10)) 

    # 加载历史记录
    history = load_history()

    # 更新历史记录
    if meeting_code:
        history.insert(0, text)

    # 最多保留10个历史记录
    if len(history) > 10:
        history.pop()

    # 保存历史记录
    save_history(history)


    open_meeting(meeting_code, launch_id)
    if password :
        enter_password(password)
    
    #重置线程检查mask
    global continue_show_messagebox
    continue_show_messagebox = True
    time.sleep(2)  #避免在窗口加载完成前 就开启检查线程 
    # 使用线程锁确保只创建一个线程
    with thread_lock:
        if not hasattr(start_meeting, "check_thread") or not start_meeting.check_thread.is_alive():
            start_meeting.check_thread = threading.Thread(target=check_windows)
            start_meeting.check_thread.daemon = True  # 设置为守护线程，以便在主程序退出时自动结束线程
            start_meeting.check_thread.start()


#多线程 检查 会议中断！windows 通过检查到会议一小时弹窗 或者会议窗口消失判断
#linux 系统 还布吉岛--- 

def find_windows(class_name, title):
    if os.name == 'nt':
        import win32gui
        windows = []
    
        def callback(hwnd, extra):
            class_name = win32gui.GetClassName(hwnd)
            window_title = win32gui.GetWindowText(hwnd)
            if class_name == extra['class'] and window_title == extra['title']:
                windows.append(hwnd)
    
        win32gui.EnumWindows(callback, {'class': class_name, 'title': title})
    
        return windows
    else:
        pass #linux 系统窗口怎么做窗口检查 --


def close_windows(hwnd):
    if os.name == 'nt':
        import win32gui
        import win32con
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    else:
        pass

#设置一个全局变量flag    
continue_show_messagebox = True

def check_windows():
    
    class_name_1 = "TXGuiFoundation"
    global continue_show_messagebox 
    while True :
        #print(continue_show_messagebox)
        if continue_show_messagebox: #这个是会议中断弹出的窗口
           # 检查并关闭classname为"TXGuiFoundation"且title为空的窗口
           windows_1 = find_windows(class_name_1, "")
           for hwnd in windows_1:
               close_windows(hwnd)
               if auto_rejoin_var.get():
                   start_meeting()  # 调用重新进入会议的函数
               else:
                   response = messagebox.askquestion("提示", "会议窗口已关闭0，是否重新进入会议？")
                   if response == "yes":
                       start_meeting()  # 调用重新进入会议的函数
                   else:
                       continue_show_messagebox = False

           class_name_2 = "Qt5158QWindowIcon"
           title_2 = "腾讯会议"
           # 检查是否存在classname为"Qt5158QWindowIcon"且title为"腾讯会议"的窗口
           #这里就 持续检查 会议窗口是否存在
           windows_2 = find_windows(class_name_2, title_2)
         #  print(windows_2)
           if not windows_2:
               if auto_rejoin_var.get():
                   start_meeting()  # 调用重新进入会议的函数
               else:
                   response = messagebox.askquestion("提示", "会议窗口已关闭1，是否重新进入会议？")
                   if response == "yes":
                       start_meeting()  # 调用重新进入会议的函数
                   else :
                       continue_show_messagebox = False

        time.sleep(2)  # 每2秒检查一次
        
# 创建一个线程锁
thread_lock = threading.Lock()

#root = tk.Tk()
root = ttk.Window(
        title="我爱开会",        #设置窗口的标题
        themename="darkly",     #设置主题
        size=(480,760),        #窗口的大小
        position=(100,100),     #窗口所在的位置
        minsize=(0,0),          #窗口的最小宽高
    #    maxsize=(1920,1080),    #窗口的最大宽高
        resizable=None,         #设置窗口是否可以更改大小
        alpha=1.0,              #设置窗口的透明度(0.0完全透明）
        )
# 在初始化GUI时加载并显示历史记录
history_text = ttk.Text(root, height=6,state=ttk.NORMAL)
#history_text.config(height=6)
history_text.pack()
load_and_display_history()

# 添加一个Scale控件用于挑选历史记录
history_scale = ttk.Scale(root, from_=0, to=10, orient=ttk.HORIZONTAL, command=update_history_text,style="warning")
history_scale.pack()
history_scale.set(0)

# 创建复选框并关联变量
# 创建一个变量来存储复选框的状态
auto_rejoin_var = ttk.BooleanVar()
auto_rejoin_var.set(False)  # 初始状态为未选中
auto_rejoin_checkbox = ttk.Checkbutton(root, text="是否自动重入会", variable=auto_rejoin_var)
auto_rejoin_checkbox.pack()

tip_label = ttk.Label(root,text="请在下方输入会议链接(支持输入密码),或者拖动选择历史记录")
tip_label.pack()


input_text = ttk.Text(root,)
input_text.pack()
result_text = ttk.Label(root, text='')
result_text.pack()

start_btn = ttk.Button(root, text='开会咯!', command=start_meeting)
start_btn.pack()

root.mainloop()

