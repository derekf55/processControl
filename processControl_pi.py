#Derek Franz
#Last updated 2/6/21
#Program runs on the raspberry pi and checks the servers database for commands then runs them
#!/usr/bin/env python3
import mysql.connector 
import subprocess,time
import random, os, sys
import derek_functions as df
from remote import *
from gtts import gTTS 
import pysftp

# Global variables 
DEVICE_NAME = ''
ROOM_NAME = ''
QUOTE_PATH = '/mnt/pi/DONNY_MP3_FILES/'
PHONE_INPUT_FILE = 'PresenceDetection.mp3'


#Gets the oldest command in the queue 
#@param conn, cursor: Takes the current connection object and cursor object 
#@returns the command from the database
def fetchCommand():
    #sql = "SELECT command FROM `ProcessToRun` WHERE Server='{}' HAVING MAX(id) ".format(DEVICE_NAME)
    sql = "SELECT Command FROM ProcessToRun WHERE Server = '{}' ORDER BY ID".format(DEVICE_NAME)
    querry_results = df.runSql(sql)
    commands = []
    if len(querry_results) == 0:
        return commands

    for command in querry_results:
        #print("Processing command {}".format(command))
        commands.append(command[0])
        #print("Appending {} to commands".format(command[0]))
    return commands

#@param conn, cursor: Takes the current connection object and cursor object
#Removes the last command 
def removeCompleted():
    sql = "DELETE FROM `ProcessToRun` WHERE Server='{}' ORDER BY id ASC LIMIT 1".format(DEVICE_NAME)
    df.runSql(sql)

def getPeopleHere():
    sql = 'SELECT Name FROM `PeopleHere` ORDER by Resident, Name'
    results = df.runSql(sql)
    people = []
    for item in results:
        people.append(item[0])
    return people

def generatePhoneTTS(people):
    language = 'en'
    stringToRead = "People that are currently here.  "
    for person in people:
        stringToRead += f"{person}, "

    soundObject = gTTS(text=stringToRead, lang=language, slow=False)
    soundObject.save(PHONE_INPUT_FILE)


#@param conn, cursor: Takes the current connection object and cursor object 
#Runs one of the listed commands
def runCommand(commandList):
    if len(commandList) == 0:
        print("No commands")
    for command in commandList:
        print("Running {}".format(command))
        if command == 'Donny':
            subprocess.check_output(['omxplayer','-o','local',random_quote()])
            removeCompleted()
            continue
        if command == 'tts':
            sql = "SELECT TTS, ID FROM `SoundQueue` order by id "
            playbackText, ID = df.runSql(sql)[0]
            language = 'en'
            soundObject = gTTS(text=playbackText, lang=language, slow=False)
            soundObject.save("output.mp3")
            subprocess.check_output(['omxplayer','-o','local','output.mp3'])
            sql = f"DELETE FROM `SoundQueue` WHERE ID = {ID}"
            df.runSql(sql)
            removeCompleted()
            continue
    
        if command == 'Presence_Phone':
            generatePhoneTTS(getPeopleHere())
            subprocess.check_output(['ffmpeg','-i',PHONE_INPUT_FILE,'-ac','1','-ar','8000',df.PHONE_OUTPUT_FILE])
            df.sendToPhone()
    

        try:
            remote.pushButton(command)
        except Exception as e:
            pass
        removeCompleted()
    

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
    global DEVICE_NAME
    global ROOM_NAME
    global remote

    if len(sys.argv) != 3:
        print('Usage: Type deviceName RoomName')
        exit()
    
    DEVICE_NAME = sys.argv[1]
    ROOM_NAME = sys.argv[2]

    remote = Remote(room=ROOM_NAME)

    try:
        while True:
            runCommand(fetchCommand())
            time.sleep(.2)
    except Exception as e:
        time.sleep(1)
        main()
        
if __name__ == '__main__':
    main()
    
