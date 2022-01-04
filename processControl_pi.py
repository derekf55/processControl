#Derek Franz
#Last updated 2/6/21
#Program runs on the raspberry pi and checks the servers database for commands then runs them
#!/usr/bin/env python3
from gtts.tokenizer.tokenizer_cases import other_punctuation
import mysql.connector 
import subprocess,time
import random, os, sys
import derek_functions as df
from remote import *
from gtts import gTTS 
import pysftp
from requests.api import post, get
import json
import datetime

QUOTE_PATH = '/mnt/pi/DONNY_MP3_FILES/'
ERROR_FILE = 'error.log'

class ProcessController:

    def __init__(self,device_name, room_name) -> None:
        self.device_name = device_name
        self.room_name = room_name
        self.remote = Remote(room=room_name)
        self.unknown_commands = []


    #Gets the oldest command in the queue 
    #@param conn, cursor: Takes the current connection object and cursor object 
    #@returns the command from the database
    def fetchCommand(self):
        #sql = "SELECT command FROM `ProcessToRun` WHERE Server='{}' HAVING MAX(id) ".format(self.device_name)
        sql = f"SELECT Command, args FROM ProcessToRun WHERE Server = '{self.device_name}' ORDER BY ID"
        querry_results = df.runSql(sql)
        commands = []
        if len(querry_results) == 0:
            return commands

        for command in querry_results:
            #print("Processing command {}".format(command))
            d = {}
            d['Command'] = command[0]
            try:
                d['Args'] = command[1]
            except Exception as e:
                pass
            commands.append(d)
            #print("Appending {} to commands".format(command[0]))
        return commands 


    #@param conn, cursor: Takes the current connection object and cursor object
    #Removes the last command 
    def removeCompleted(self):
        sql = f"DELETE FROM `ProcessToRun` WHERE Server='{self.device_name}' ORDER BY id ASC LIMIT 1"
        df.runSql(sql)

    def getPeopleHere(self):
        sql = 'SELECT Name FROM `PeopleHere` ORDER by Resident, Name'
        results = df.runSql(sql)
        people = []
        for item in results:
            people.append(item[0])
        return people

    def generateTTS(self,text,outputFile):
        language = 'en'
        soundObject = gTTS(text=text, lang=language, slow=False)
        soundObject.save(outputFile)


    #@param conn, cursor: Takes the current connection object and cursor object 
    #Runs one of the listed commands
    def runCommand(self,commandList):
        if len(commandList) == 0:
            print("No commands")
        for commandDict in commandList:
            command = commandDict['Command']
            try:
                args = commandDict['Args']
            except Exception as e:
                pass
            print("Running {}".format(command))
            if command == 'Donny':
                subprocess.check_output(['omxplayer','-o','local',random_quote()])
                self.removeCompleted()
                continue
            elif command == 'tts':
                sql = "SELECT TTS, ID, Speaker FROM `SoundQueue` order by id "
                playbackText, ID, speaker = df.runSql(sql)[0]
                url = "https://derekfranz.ddns.net:8542/api/services/tts/google_say"
                headers = df.HOME_ASSISTANT_HEADERS

                if speaker == "Derek's Room":
                    speaker = "media_player.dereks_room_speaker"
                elif speaker == "Living Room ":
                    speaker = "media_player.living_room_speaker"
                elif speaker == "Sam's Room":
                    speaker = "media_player.sams_room_speaker"

                data = {"entity_id": speaker, 'message': playbackText, 'cache': 'true'}
                response = post(url, headers=headers, verify=False, json=data)

                sql = f"DELETE FROM SoundQueue WHERE ID = {ID}"
                df.runSql(sql)

                self.removeCompleted()
                continue
        
            elif command == 'Presence_Phone':
                people = self.getPeopleHere()
                mp3File = 'PresenceDetection.mp3'
                wavFile = 'PresenceDetection.wav'
                stringToRead = "People that are currently here.  "
                for person in people:
                    stringToRead += f"{person}, "
                self.generateTTS(stringToRead,mp3File)
                subprocess.check_output(['ffmpeg','-i',mp3File,'-ac','1','-ar','8000',wavFile,'-y'])
                df.sendToPhone(wavFile,f'/var/lib/asterisk/sounds/en/custom/{wavFile}')
                os.remove(mp3File)
                os.remove(wavFile)
                df.delete_old_voicemails()

            elif command == "personArrival":
                # if args in current_voicemails:
                #     removeCompleted()
                #     return
                text = f"{args} has just arrived"
                mp3File = 'newArrival.mp3'
                current_num_voicemails = df.get_num_voicemails()
                required_digits = 4 - len(str(current_num_voicemails))
                wavFile = 'msg'
                textFile = 'msg'
                while required_digits > 0:
                    wavFile += '0'
                    textFile += '0'
                    required_digits -=1
                wavFile += f'{current_num_voicemails}.wav'
                textFile += f'{current_num_voicemails}.txt'
                            
                self.generateTTS(text,mp3File)
                subprocess.check_output(['ffmpeg','-i',mp3File,'-ac','1','-ar','8000',wavFile,'-y'])
                # origdate=Fri Jul 30 05:59:11 PM UTC 2021
                voiceText = f""";
                            ; Message Information file
                            ;
                            [message]
                            origmailbox=100
                            context=macro-vm
                            macrocontext=ext-local
                            exten=s-NOANSWER
                            rdnis=unknown
                            priority=2
                            callerchan=PJSIP/300-0000006d
                            callerid="Alaska" <300>
                            origdate={datetime.datetime.now()}
                            origtime=1627667951
                            category=
                            msg_id=1627667951-00000002
                            flag={args}
                            duration=1
                            """
                
                #textFile = f'msg{current_num_voicemails}.txt'
                f = open(textFile,'w')
                f.write(voiceText)
                f.close()
                df.sendToPhone(wavFile,f'/var/spool/asterisk/voicemail/default/100/INBOX/{wavFile}')
                df.sendToPhone(textFile,f'/var/spool/asterisk/voicemail/default/100/INBOX/{textFile}')
                os.remove(mp3File)
                os.remove(wavFile)
                df.delete_old_voicemails()
                df.remove_duplicate_voicemails()
                
                
            
            elif command == 'switch_light':
                devices = [args]
                if args == 'all':
                    devices = ['derektemp_dereksroom','christmaslights_dereksroom']
                
                for device in devices:

                    # Get state 
                    url = f"https://derekfranz.ddns.net:8542/api/states/light.{device}"
                    
                    headers = df.HOME_ASSISTANT_HEADERS
                    response = get(url,headers=headers,verify=False)
                    
                    jsonData = json.loads(response.text)

                    
                    try:
                        current_state = jsonData['state']
                    except Exception as e:
                        self.write_error(command,args)
                        self.removeCompleted()
                        continue

                    if current_state == 'on':
                        new_state = 'off'
                    else:
                        new_state = 'on'

                    url = f"https://derekfranz.ddns.net:8542/api/services/light/turn_{new_state}"
                    headers = df.HOME_ASSISTANT_HEADERS
                    
                    service_data = {"entity_id":f"light.{device}"}
                    check = post(url,headers=headers,json=service_data,verify=False)
                
                    print(check)


            else:
                try:
                    self.remote.pushButton(command)
                except Exception as e:
                    print('Invalid command')
                    self.write_error(command,args)

            self.removeCompleted()

    def write_error(self,command,args=None):
        if command not in self.unknown_commands:
            self.unknown_commands.append(command)
            with open(ERROR_FILE,'a') as writer:
                message = f'{command}:{args}\n'
                writer.write(message)

    def main(self):
        while True:
            self.runCommand(self.fetchCommand())
            time.sleep(.1)
    

# Function written by Sam
# @return: Returns the path of the audio file to play
def random_quote():
    quotes = os.listdir(QUOTE_PATH)

    for quote in quotes:
        if quote[0] == ".":
            quotes.remove(quote)

    rand = random.randrange(len(quotes))

    selectedQuotePath = os.path.join(QUOTE_PATH, quotes[rand])

    return selectedQuotePath



#Tries to connect to the server and if the connection is closed reconnect
def main():

    if len(sys.argv) != 3:
        print('Usage: Type deviceName RoomName')
        exit()
    
    device_name = sys.argv[1]
    room_name = sys.argv[2]

    

    p = ProcessController(device_name,room_name)
    p.main()

    
        
if __name__ == '__main__':
    main()
    
