import socket
import webbrowser
import requests
import pkce
import json
from tkinter import *
from tkinter import ttk
from elevenlabslib import *
import jwt
from addict import Dict

# global variables
authBaseUri = "https://ident.familysearch.org/cis-web/oauth2/v3/authorization"
tokenBaseUri = "https://ident.familysearch.org/cis-web/oauth2/v3/token"
regularBaseUri = "https://api.familysearch.org/"
clientID = ""
elevenClientID = ""
redirectUri = "http://127.0.0.1:5000"
outState = "237589753"
tokenDict = Dict()
pIdsList = []
peopleList = []
peopleGenderList = []
personGender = ""
textMemoryLocationsList = []
textMemoryTitleList = []
memoryIndex = 0

def Main():
    # setup tkinter
    root = Tk()
    root.title("Text Memories to Speech")
    root.maxsize(950, 600)

    # set left frame
    leftFrame = Frame(root, width=275, height=400)
    leftFrame.grid(row=0, column=0, padx=10, pady=5)

    # set right frame
    rightFrame = Frame(root, width=650, height=400)
    rightFrame.grid(row=0, column=1, padx=10, pady=5)

    # instructor user on how to proceeed
    SendTextMale("Press the login to FamilySearch button to begin the authentication process")

    # populate main window
    PopulateMainWindow(leftFrame, rightFrame)

    # begin main loop for tkinter
    root.mainloop()

def PopulateMainWindow(leftFrame, rightFrame):
    """Populates the tkinter window with GUI elements.

    Parameters
        leftFrame: a frame set up within tkinter for the left side of interface
        rightFrame: a frame set up with tkinter for the right side of interface
    
    """
    # create gui elements for tkinter
    ancestorChosen = ttk.Combobox(leftFrame, width=40, justify="left", state="readonly")
    memoriesChosen = ttk.Combobox(leftFrame, width=40, justify="left", state="readonly")
    storyLabel = Label(rightFrame, text="", justify="left", wraplength=620)
    
    loginButton = Button(leftFrame, text="Login to FamilySearch", justify="center")
    loginButton.place(x=0, y=0)

    def MemorySelected(event):
        """ Event that retrives current selected text memory, and begins reading the text memory.
        
        Parameters
            event: is a event triggered when selected from the drop down menu.
        """
        # set initial variables for presenting string with data from text file from FamilySearch
        global personGender
        storyLabel.config(text="")
        storyResponse = GetTextMemory(memoriesChosen.current())
        storyLabel.config(text=storyResponse)
        storyLabel.place(x=0, y=0)
        
        # read the string with data from text file from FamilySearch based on ancestor's gender
        if personGender == "Male":
            ReadTextMale(storyResponse)

        if personGender == "Female":
            ReadTextFemale(storyResponse)

    def AncestorSelected(event):
        """ Event that retrives the current selected ancestor, and retrives a list of text memories
        attached to that ancestor.
        
        Parameters
            event: an event that is triggered when selected from a drop down menu.
        """
        # set initial variables and clear old variables
        global memoryIndex
        global personGender
        textMemoryTitleList.clear()
        textMemoryLocationsList.clear()
        memoriesChosen.set("")
        storyLabel.config(text="")
        memoryIndex = 0
        
        # tell user what the program is doing
        SendTextMaleNoBack(f"Acquiring a list of text memories for {peopleList[ancestorChosen.current()]}")
        personGender = peopleGenderList[ancestorChosen.current()]

        # get a list of memory for the chosen ancestor
        GetMemories(ancestorChosen.current())

        # bind event to element
        memoriesChosen.bind("<<ComboboxSelected>>", MemorySelected)

        # create drop down menu with values
        memoriesLabel = Label(leftFrame, text="Text Memories:", justify="left")
        memoriesLabel.place(x=0, y=50)

        memoriesChosen['values'] = textMemoryTitleList
        memoriesChosen.place(x=0, y=75)

        # ask user to select text memory
        SendTextMale("Please select a text memory to view from the drop down list")

        # set focus to list of text memories
        memoriesChosen.focus()
        
    def ProcessFamilySearchAuth():
        """Begins and processes the FamilySearch authentication flow. This function
        is a part of the PopulateMainWindow function to populate necessary GUI elements.
        """
        # begin FamilySearch authentication process
        persons = BeginFamilySearchAuth()

        # bind event to drop down menu
        ancestorChosen.bind("<<ComboboxSelected>>", AncestorSelected)
                
        # create combox box with ancestor list
        ancestorLabel = Label(leftFrame, text="Ancestors:", justify="left")
        ancestorLabel.place(x=0, y=0)

        # generate ancestor list element
        ancestorChosen['values'] = persons
        ancestorChosen.place(x=0, y=25)

        # set ancestor list as focus in tkinter
        ancestorChosen.focus()

        # destroy login button
        loginButton.destroy()

    # set event for login button
    loginButton.config(command=ProcessFamilySearchAuth)

def BeginFamilySearchAuth():
    """Starts the FamilySearch authentication flow, and creates list of deceased
    ancestors for current user

    Return: a list of deceased ancestors for current user
    """
    # create PKE strings for FamilySearch
    codeVerifier, codeChallenge = pkce.generate_pkce_pair()

    # create socket listener
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    serverName = "127.0.0.1"
    serverAddress = (serverName, 5000)
    sock.bind(serverAddress)
    sock.listen(1)

    # prepare authentication string to send via browser
    authRequest = f"{authBaseUri}?client_id={clientID}&redirect_uri={redirectUri}&response_type=code&state={outState}&code_challenge={codeChallenge}&code_challenge_method=S256&scope=openid%20profile%20email%20qualifies_for_affiliate_account%20country"

    # send authentication string
    webbrowser.open(authRequest)

    while True:
        connection, clientAddress = sock.accept()
        data = connection.recv(1000)
        connection.send(b'HTTP/1.0 200 OK\n')
        connection.send(b'Content-Type: text/html\n')
        connection.send(b'\n')
        connection.send(b"""
        <html>
        <script>window.close();
        </script>
        <body>
        </body>
        </html>
        """)
        connection.close()
        break

    # split string from web browser to get authentication code and state
    data = str(data)
    data = data.split("?")
    data = data[1]
    data = data.split(" ")
    data = data[0]
    data = data.split("&")
    authCode = data[0]
    inState = data[1]

    authCode = CodeToSplit(data[0])
    inState = CodeToSplit(data[1])

    # continue FamilySearch authentication flow
    if inState == outState:
        GetAccessToken(authCode, codeVerifier)
        DecodeJWT()
        currentUserDict = GetCurrentUser()
        pedigreeDict = GetAncestry(currentUserDict)
        persons = CreatePersonsList(pedigreeDict)
        CreatePidsList(pedigreeDict)

    return persons

def CodeToSplit(codeToSplit):
    """Splits a string into two separate pieces to return the second element

    Parameters
        codetoSplit: a string that needs to be split into two

    Return: a string of the second element in the split
    
    """
    codeToSplit = codeToSplit.split("=")
    codeToSplit = codeToSplit[1]
    return codeToSplit

def CheckResponseStatus(status_code):
    """Checks a http response to see if the status code is equal to OK.

    Parameters
        status_code: an int that is the response code from the server
    Return: a bool of true is response is 200, or false if response is other than 200

    """
    if status_code == 200:
        return True
    else:
        return False

def SendTextMale(textToSend):
    """Sends a string in the background to ElevenLabs to get
    audio in male voice.

    Parameters
        textToSend: a string of text to be sent to ElevenLabs for processing
    """
    user = ElevenLabsUser(elevenClientID)
    voice = user.get_voices_by_name("Josh")[0]
    playbackOptions = PlaybackOptions(runInBackground=True)
    voice.generate_stream_audio_v2(
        prompt=textToSend,
        playbackOptions=playbackOptions
    )

def SendTextMaleNoBack(textToSend):
    """ Sends a string to ElevenLabs to get audio in a male voice

    Parameters
       textToSend: a string of text to be sent to ElevenLabs for processing
    """
    user = ElevenLabsUser(elevenClientID)
    voice = user.get_voices_by_name("Josh")[0]

    playbackOptions = PlaybackOptions(runInBackground=False)
    voice.generate_stream_audio_v2(
        prompt=textToSend,
        playbackOptions=playbackOptions
    )

def ReadTextFemale(textToSend):
    """ Sends a string in the background to ElevenLabs to get audio in 
    a female voice. Function is for reading text memory back to user.

    Parameters
       textToSend: a string of text to be sent to ElevenLabs for processing
    """
    user = ElevenLabsUser(elevenClientID)
    voice = user.get_voices_by_name("Grace")[0]
    playbackOptions = PlaybackOptions(runInBackground=True)
    voice.generate_stream_audio_v2(
        prompt=textToSend,
        playbackOptions=playbackOptions
    )

def ReadTextMale(textToSend):
    """Sends a string in the background to ElevenLabs to get audio in
    a male voice. Function is for reading text memory back to user.

    Parameters
        textToSend: a string of text to be sent to ElevenLabs for processing
    """
    user = ElevenLabsUser(elevenClientID)
    voice = user.get_voices_by_name("Clyde")[0]
    playbackOptions = PlaybackOptions(runInBackground=True)
    voice.generate_stream_audio_v2(
        prompt=textToSend,
        playbackOptions=playbackOptions
    )

def GetAccessToken(authCode, codeVerifier):
    """Exchanges the FamilySearch authorization code for an access token.

    Parameters
        authCode: a string that contains the FamilySearch authorization code.
        codeVerifier: a string that contains the code verifier for FamilySearch
    """
    global tokenDict
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    dataBody = {
        "code": f"{authCode}",
        "grant_type": "authorization_code",
        "client_id": f"{clientID}",
        "code_verifier": f"{codeVerifier}"
        }

    response = requests.post(tokenBaseUri, data=dataBody, headers=headers)

    if CheckResponseStatus(response.status_code):
        jsonDict = json.loads(response.text)
        tokenDict = Dict(jsonDict)

def DecodeJWT():
    """ Decodes the identity token from FamilySearch, and sends a welcome 
    message to a user based on information from the JWT identity token
    """
    # decode identity token
    global tokenDict
    decodedJWT = jwt.decode(tokenDict.id_token, options={"verify_signature": False})
    identityToken = Dict(decodedJWT)
    
    # welcome user based on gender and if Church member
    if identityToken.qualifies_for_affiliate_account == "true":
        if identityToken.gender == "M":
            SendTextMaleNoBack("Hello and welcome Brother " + identityToken.family_name)
        elif identityToken.gender == "F":
           SendTextMaleNoBack("Hello and welcome Sister " + identityToken.family_name)
        elif identityToken.qualifies_for_affiliate_account == "false":
            SendTextMaleNoBack("Hello and welcome " + identityToken.given_name)

def GetCurrentUser():
    """Gets the PID for the currently logged in user from FamilySearch
    Return: a dictionary that contains data from FamilySearch
    """
    global tokenDict
    apiRoute = "platform/users/current";
    apiRequest = f"{regularBaseUri}{apiRoute}"

    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer " + tokenDict.access_token
    }

    response = requests.get(apiRequest, headers=headers)

    if CheckResponseStatus(response.status_code):
        jsonDict = json.loads(response.text)
        currentUserDict = Dict(jsonDict)

        return currentUserDict

def GetAncestry(currentUserDict):
    """Gets a 4 generation pedigree of the currently logged in user from FamilySearch

    Parameters
        currentUserDict: a dictionary that contains data about the current user
    Return: a dictionary with the 4 generation pedigree of the current user
    """
    SendTextMale("Please select a deceased ancestor from the drop down list")
    global tokenDict
    apiRoute = "platform/tree/ancestry"
    person = "?person=" + currentUserDict.users[0].personId
    generations = "&generations=4"
    apiRequest = f"{regularBaseUri}{apiRoute}{person}{generations}"

    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer " + tokenDict.access_token
    }

    response = requests.get(apiRequest, headers=headers)

    if CheckResponseStatus(response.status_code):
        jsonDict = json.loads(response.text)
        pedigreeDict = Dict(jsonDict)

        return pedigreeDict

def CreatePersonsList(pedigreeDict):
    """Creates a list of persons with gender from FamilySearch

    Parameters
        pedigreeDict: a dictionary containing the pedigree of the current user
    Return: a list of people generated from the pedigree of the current user
    """
    persons = []

    for i in range(len(pedigreeDict.persons)):
        if pedigreeDict.persons[i].living == False:
            person = pedigreeDict.persons[i].display.name
            peopleGenderList.append(pedigreeDict.persons[i].display.gender)
            pID = pedigreeDict.persons[i].id
            peopleList.append(person)
            persons.append(person + " " + pID)

    return persons

def CreatePidsList(pedigreeDict):
    """Creates a list of pids from the pedigree of the current user

    Parameters
        pedigreeDict: a dictionary containing the pedigree of the current user
    """

    for i in range(len(pedigreeDict.persons)):
        if pedigreeDict.persons[i].living == False:
            pID = pedigreeDict.persons[i].id
            pIdsList.append(pID)

def GetMemories(pidIndex):
    """Gets a ist of text memories attached to a specific deceased ancestor

    Parameters
        pidIndex: an int containing the PID of a deceased ancestor from FamilySearch
    """
    # prepare api request with necessary elements
    global memoryIndex
    global tokenDict
    apiRoute = "platform/tree/persons/"
    memoryCount = "/memories?start="
    countString = str(memoryIndex)

    # set the api request string to get text memories for selected ancestor.
    apiRequest = f"{regularBaseUri}{apiRoute}{pIdsList[pidIndex]}{memoryCount}{countString}"

    # set request headers
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer " + tokenDict.access_token
    }

    # send http request
    response = requests.get(apiRequest, headers=headers)

    # if response is good create dictionary with text memory 
    if CheckResponseStatus(response.status_code):
        jsonDict = json.loads(response.text)
        memoryDict = Dict(jsonDict)

        # add the current index of amount of memories given from FamilySearch
        memoryIndex += len(memoryDict.sourceDescriptions)

        # create lists of memory titles and locations
        for index in range(len(memoryDict.sourceDescriptions)):
            if memoryDict.sourceDescriptions[index].mediaType == "text/plain":
                textMemoryLocationsList.append(memoryDict.sourceDescriptions[index].about)
                textMemoryTitleList.append(memoryDict.sourceDescriptions[index].titles[0].value)
        
        # repeat function to continue to retrive memories attached to ancestor
        print("loading memories...")
        GetMemories(pidIndex)
    
    # if there are no more memories attached to ancestor terminate loop
    elif response.status_code == 204:
        print("finished loading memories!")
        return

def GetTextMemory(indexToGet):
    """Gets a text file from FamilySearch, and returns the text of the response

    Parameters
        indexToGet: an int with the index of the text memory to get from FamilySearch
    Return: a string containing the data from the text file from FamilySearch
    """
    response = requests.get(textMemoryLocationsList[indexToGet])
    
    return response.text

if __name__ == "__main__":
    Main()