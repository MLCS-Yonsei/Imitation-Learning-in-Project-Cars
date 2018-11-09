'''
This code is for the computer that runs Project Cars in Windows.
Basic purpose of this script is to get Pcars data from CREST API and capture the game screen
and resize it, then send it to REDIS server so that the A3C can take the data.
To minimize the elapsed time, each process is divided into threads.

author : Hwanmoo Yong
'''

import redis
import json
import time
from io import BytesIO

import mss
import mss.tools

from PIL import Image
import base64
import numpy as np

from threading import Thread
from multiprocessing import Process

from utils.pcars_stream.src.pcars.stream import PCarsStreamReceiver
from utils.autoController import pCarsAutoController

import http.client
import socket 


from utils.keys import Keys
from time import sleep

from pywinauto.application import Application
import pywinauto

import win32ui
import win32gui
import win32com.client

import os
from datetime import datetime

''' Getting Local IP of this Computer '''
local_ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1][0]
print("Local ip",local_ip)
''' Init Redis '''
r = redis.StrictRedis(host='redis.hwanmoo.kr', port=6379, db=1)

''' CREST Thread '''
class PCarsListener(object):
    def __init__(self):
        self.data = None

    def handlePacket(self, data):
        # You probably want to do something more exciting here
        # You probably also want to switch on data.packetType
        # See listings in packet.py for packet types and available fields for each
        # print(data._data)
        self.data = data._data
        # print(self.data)

class screen_capture_thread(Thread):        

    def __init__(self, listener):
        self.img = None
        self.listener = listener

        super(screen_capture_thread, self).__init__()

    def run(self):
        try:
            import win32gui
            # import win32ui
            # import win32con
            
            # Get Focus on project cars window
            windowname = "Project CARS™"
            hwnd = win32gui.FindWindow(None, windowname)
            
            # Get window properties and take screen capture
            l, t, _r, b = win32gui.GetWindowRect(hwnd)

            target_w = 800
            target_h = 600

            margin_w  = int((_r-l-target_w) / 2)

            l = l + margin_w
            _r = _r - margin_w
            b = b - margin_w
            t = t + ((b-t-target_h))
            w = _r - l
            h = b - t

            with mss.mss() as sct:
                # The screen part to capture
                monitor = {'top': t, 'left': l, 'width': w, 'height': h}

                # Grab the data
                msg = self.listener.data
                sct_img = sct.grab(monitor)

            img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')

            buf= BytesIO()
            img = img.resize((200,150), Image.ANTIALIAS)
            img.save(buf, format= 'PNG')

            self.img = base64.b64encode(buf.getvalue()).decode("utf-8")
            result = False
            
            # print(msg)
            if msg is not None:
                if "participants" in msg:
                    if "worldPositionX" in msg["participants"][0]:
                        cur_position_x = msg["participants"][0]["worldPositionX"]
                        cur_position_y = msg["participants"][0]["worldPositionY"]
                        cur_position_z = msg["participants"][0]["worldPositionZ"]
                        
                        if self.listener.data is not False and self.listener.data is not None and self.img is not None:
                            ob = self.listener.data

                            if "gameState" in ob:
                                gameState = ob["gameState"].value
                                raceState = ob["raceState"].value

                                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                                # print(current_time, gameState, raceState)
                                if (gameState == 2 and raceState == 2):
                                    result = {'game_data':self.listener.data,'image_data':self.img,'current_time':current_time}                
        
            if result is not False:
                # print("Screen Capture")
                r.hset('pcars_data'+local_ip,local_ip,result)
            exit(0)
            
        except Exception as ex:
            print("Pcars Screen Capture Error :", ex)
            exit(0)
        

def send_data(listener, sct):
    sct.join()

    message = listener.data.decode("utf-8")
    message = message.replace('<','\'<')
    message = message.replace('>','>\'')

    msg = eval(message)

    cur_position_x = msg["participants"][0]["worldPositionX"]
    cur_position_y = msg["participants"][0]["worldPositionY"]
    cur_position_z = msg["participants"][0]["worldPositionZ"]

    print(cur_position_x)
    # Set game_data from pcars udp listener after taking screen capturing
    if listener.data is not False and sct.img is not None:
        result = {'game_data':listener.data,'image_data':sct.img}
    else:
        result = False

    r.hset('pcars_data'+local_ip,local_ip,result)

def start_capture(listener):
    sct = screen_capture_thread(listener)
    sct.daemon = True 
    sct.start()

    return sct

def run_pac(r, local_ip):
    pc = pCarsAutoController()
    while True:
        try:
            message = r.hget('pcars_action'+local_ip,local_ip)
            force_acc = r.hget('pcars_force_acc', local_ip)

            if force_acc:

                if eval(force_acc) == True:
                    pc.accOn()
                    
                    r.hdel('pcars_force_acc',local_ip)

            if message:
                action = eval(message)
                if action is False:
                    print("Control OFF")
                    pc.move_steer(0)
                    pc.brakeOff()
                    pc.accOff()
                else:
                    pc.action_parser(action)

                r.hdel('pcars_action'+local_ip,local_ip)
        except:
            pass

reboot_time = 3600 * 3 # in seconds
def reboot_protocol():
    keys = Keys()

    print("Reboot in 3600s.")
    print("Project Cars will be launched in 10s.")
    sleep(10)
    # mouse movement
    # for i in range(100):
    #     keys.directMouse(-1*i, -1*i)
    #     # sleep(0.004)
    pywinauto.mouse.click(button='left', coords=(0, 0))

    # keys.directMouse(buttons=keys.mouse_lb_press)
    # sleep(0.1)
    # keys.directMouse(buttons=keys.mouse_lb_release)

    def key_input(key):
        keys.directKey(key)
        sleep(0.04)
        keys.directKey(key, keys.key_release)

    for key in "project":
        key_input(key)

    key_input("Return")
    print("Waiting for Pcars to be launched for 30s.")
    sleep(30)

    def get_focus():
        # Make Pcars window focused
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys('%')
        
        PyCWnd1 = win32ui.FindWindow( None, "Project CARS™" )
        PyCWnd1.SetForegroundWindow()
        PyCWnd1.SetFocus()

        return PyCWnd1

    rect = win32gui.GetWindowRect(win32gui.FindWindow( None, "Project CARS™" ))
    x = rect[0]
    y = rect[1]
    w = rect[2] - x
    h = rect[3] - y
    zero = [x + int(w/2), y + int(15 * int(h) / 16)]

    pywinauto.mouse.click(button='left', coords=(zero[0], zero[1]))

    get_focus()
    key_input("j")

    for i in range(5):
        key_input("Left")
        key_input("Up")

    key_input("Right")
    key_input("Return")

    sleep(1)
    get_focus()
    for i in range(5):
        key_input("Left")
        key_input("Up")

    key_input("Return")
    get_focus()
    


if __name__ == '__main__':
    print('Starting Data Sender.. [A3C on Project Cars]')
    ''' 
    Listening Pcars UDP port 
    Make sure to set udp setting in the game option as 1
    '''
    # reboot_protocol()

    listener = PCarsListener()
    stream = PCarsStreamReceiver()
    stream.addListener(listener)
    stream.start()

    pac = Thread(target=run_pac, args=(r,local_ip,))
    pac.start()

    stime = datetime.now()

    while True:
        ctime = datetime.now()
        delta = ctime - stime
        
        # if delta.seconds > reboot_time:
        #     print("Rebooting")
        #     os.system('shutdown /f /r /t 1')
        #     break
        # else:
                
        # Taking Screen Capture form Pcars
        '''
        스크린샷찍는 process가 0.4초정도 걸리므로
        일단은 귀찮아서 0.08초 단위로 쓰레드를 만들어서 함.
        코드 수정필요
        '''
        # interval = 0.08

        # sct = start_capture(listener)
        # time.sleep(interval)
        sct = screen_capture_thread(listener)
        sct.daemon = True 
        sct.start()
        sct.join()
        # print(123)

        

