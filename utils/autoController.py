from pywinauto.application import Application
import pywinauto

import win32ui
import win32gui
import win32com.client

import serial
import serial.tools.list_ports

# from utils import send_crest_requset
import multiprocessing as mp
import time
import json

import redis
import socket

from utils.keys import Keys

from control import *
from control.matlab import *
import matplotlib.pyplot as plt 
import numpy as np
from datetime import datetime

class pCarsAutoController(mp.Process):
    def __init__(self):
        super(pCarsAutoController,self).__init__()

        self.get_focus()
        self.status = 'active'

        self.controlState = {
            'acc': False,
            'brake': False,
            'hand_brake': False,
            'steer': 0
        }
        
        self.keys = Keys()

        ''' Getting Local IP of this Computer '''
        self.local_ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1][0]
        print("Local IP for AutoController: ",self.local_ip)
        ''' Init Redis '''
        self.r = redis.StrictRedis(host='redis.hwanmoo.kr', port=6379, db=1)
        print("Redis connected for AutoController: ",self.r)

        

    def get_focus(self):
        # Make Pcars window focused
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys('%')
        
        PyCWnd1 = win32ui.FindWindow( None, "Project CARS™" )
        PyCWnd1.SetForegroundWindow()
        PyCWnd1.SetFocus()

        return PyCWnd1

    def parse_message(self, message):
        # Parse message from data_sender.py via redis
        message = message.decode("utf-8")
        message = message.replace('<','\'<')
        message = message.replace('>','>\'')

        msg = eval(message)
        ob = msg['game_data']
        s = msg['image_data']

        # Decode image within base64 
        s = base64.b64decode(s)
        s = Image.open(BytesIO(s))

        # s = s.resize((576,160), Image.ANTIALIAS)
        s = np.array(s)

        return ob, s

    def action_parser(self, action):
        _steer = int(action['steer']*100)/100
        _acc = action['acc']
        _brake = action['brake']

        self.move_steer(_steer)
        
        message = self.r.hget('pcars_data'+self.local_ip,self.local_ip)
        if message:
            data, _ = parse_message(message)

            _s = data["unfilteredSteering"]/127
            _a = data["unfilteredThrottle"]/255
            _b = data["unfilteredBrake"]/255

        if _brake < 0.08:
            _brake = 0
        
        if _acc < 0.08:
            _acc = 0

        if _brake > 0:
            if _b >= _brake:
                self.brakeOff()
            else:
                self.brakeOn()
        elif _brake == 0:
            self.brakeOff()

        if _acc > 0:
            if _a >= _acc:
                self.accOff()
            else:
                self.accOn()
        
    def steer_converter(self, n):
        # if n > 1:
        #     n = 1
        # elif n < -1:
        #     n = -1

        self.get_focus()
        rect = win32gui.GetWindowRect(win32gui.FindWindow( None, "Project CARS™" ))
        x = rect[0]
        y = rect[1]
        w = rect[2] - x
        h = rect[3] - y
        zero = [x + int(w/2), y + int(15 * int(h) / 16)]

        w = w-16 # Margin for window border
        d = int(w/2 * n)
        print("Steering:", n, "ACC", self.controlState['acc'], "Brake", self.controlState['brake'])
        t = [zero[0] + d, zero[1]]

        return t

    def move_steer(self, n):
        self.controlState['steer'] = n
        t = self.steer_converter(n)
        pywinauto.mouse.move(coords=(t[0], t[1]))

    def accOn(self):
        self.controlState['acc'] = True
        t = self.steer_converter(self.controlState['steer'])
        self.keys.directKey("a")

    def accOff(self):
        self.controlState['acc'] = False
        t = self.steer_converter(self.controlState['steer'])
        self.keys.directKey("a", self.keys.key_release)

    def brakeOn(self):
        self.controlState['brake'] = True
        t = self.steer_converter(self.controlState['steer'])
        self.keys.directKey("s")

    def brakeOff(self):
        self.controlState['brake'] = False
        t = self.steer_converter(self.controlState['steer'])
        self.keys.directKey("s", self.keys.key_release)

    def handBrakeOn(self):
        self.controlState['hand_brake'] = True
        t = self.steer_converter(self.controlState['steer'])
        self.keys.directKey("d")

    def handBrakeOff(self):
        self.controlState['hand_brake'] = False
        t = self.steer_converter(self.controlState['steer'])
        self.keys.directKey("d", self.keys.key_release)

    def reset_control(self):
        self.move_steer(0)
        self.accOff()
        self.brakeOff()
        self.handBrakeOff()

    def run(self):
        while True:

            message = self.r.hget('pcars_action'+local_ip,self.local_ip)
            force_acc = self.r.hget('pcars_force_acc', self.local_ip)

            if force_acc:

                if eval(force_acc) == True:
                    self.accOn()
                    
                    self.r.hdel('pcars_force_acc',self.local_ip)

            if message:
                action = eval(message)
                if action is False:
                    print("Control OFF")
                    self.move_steer(0)
                    self.brakeOff()
                    self.accOff()
                else:
                    self.action_parser(action)

                self.r.hdel('pcars_action'+self.local_ip,self.local_ip)
            

if __name__ == '__main__':
    ''' Getting Local IP of this Computer '''
    local_ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1][0]

    ''' Init Redis '''
    r = redis.StrictRedis(host='redis.hwanmoo.kr', port=6379, db=1)
    
    pc = pCarsAutoController()
    while True:
        try:
            message = r.hget('pcars_action'+local_ip,local_ip)
            # force_acc = r.hget('pcars_force_acc', local_ip)

            # if force_acc:

            #     if eval(force_acc) == True:
            #         pc.accOn()
                    
            #         r.hdel('pcars_force_acc',local_ip)
            print(message)
            if message:
                action = eval(message)
                if action is False:
                    print("Control OFF")
                    pc.reset_control()
                else:
                    pc.action_parser(action)

                r.hdel('pcars_action'+local_ip,local_ip)
        except:
            pass








