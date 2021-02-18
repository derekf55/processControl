# This is supposed to be a remote object
import derek_functions as df
import os
import subprocess

class Remote():  
    buttonList = []
    remotes = []

    def __init__(self, room='Living_Room'):
        #self.createButtons()
        # Get all current active remotes
        self.room = room
        sql = "SELECT Name FROM RemoteSettings WHERE RemoteSettings.Active = 1 and RemoteSettings.Room = '{}'".format(room)
        results = df.runSql(sql)
        for result in results:
            self.remotes.append(result[0])
            self.createButtons(result[0])

    def main(self):
        pass

    def print_debugInfo(self):
        print("Active Remotes are {}".format(self.remotes))
        print("Current Room is {}".format(self.room))


    def createButtons(self, remoteName):
        sql = "SELECT Code, Protocol, ButtonName FROM Remote WHERE RemoteName = '{}'".format(remoteName)
        results = df.runSql(sql)
        for button in results:
            name = button[2]
            protocol = button[1]
            code = button[0]
            #print("Name is {} protocol is {} code is {}".format(name,protocol, code))
            b = Button(name, protocol, code)
            self.buttonList.append(b)

    def pushButton(self, buttonName):
        for b in self.buttonList:
            if b.name == buttonName:
                button = b

        command = 'sudo ir-ctl --scancode {}:{}'.format(button.protocol, button.code)
        print("Command is {}".format(command))
        try:
            subprocess.check_output(['sudo', 'ir-ctl', '--scancode', '{}:{}'.format(button.protocol, button.code)])
        except Exception as e:
            #print("Failed to send command {}".format(command))
            print(e)

class Button:

    def __init__(self, name, protocol, code):
        self.name = name
        self.protocol = protocol
        self.code = code

