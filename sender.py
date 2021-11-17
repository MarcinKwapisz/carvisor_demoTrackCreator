import json
import requests
import configparser
import logging
import os
import time,datetime

class RequestAPI:

    def __init__(self, login_data):
        # initialize variables with login data from config file
        self.failure_response = requests.models.Response()
        self.base_url = login_data['base_url']
        self.connection_retries_number = 3
        self.tag = login_data["tag"]
        self.login_data = json.dumps({"licensePlate": login_data['license_plate'], 'password': login_data['password']})
        self.create_own_response()
        self.session = requests.Session()
        self.start_session_car()

    def POST(self,url,data_to_send={}):
        req = requests.Request("POST", self.base_url + url, data=data_to_send)
        ready_request = self.session.prepare_request(req)
        try:
            request = self.session.send(ready_request)
        except requests.exceptions.RequestException:
            return self.failure_response
        return request

    def GET(self,url):
        try:
            request = self.session.request("GET", self.base_url + url)
        except requests.exceptions.RequestException:
            return self.failure_response
        return request

    def start_session_car(self):
        # starting new session with server
        for i in range(self.connection_retries_number):
            response = self.POST("API/carAuthorization/authorize", self.login_data)
            if response.status_code == 200:
                logging.debug("Device connected to server")
                break
            elif response.status_code == 406:
                logging.warning("Wrong licence plate or/and password in config file")
                break
            else:
                logging.warning("Server unreachable, error code: " + str(response.status_code))

    def send_obd_data(self, obd_data):
        response = self.POST("API/track/updateTrackData/", json.dumps(obd_data))
        if response.status_code == 200:
            logging.debug("Sending obd data finished")
        else:
            logging.warning(
                "Problem occurred when sending obd data to server, error code: " + str(response.status_code))


    def start_track(self,gps_pos):
        start_data = json.dumps({"nfc_tag": "ACC", "time": datetime.datetime.now().strftime("%s"), "private": False,
                                 "gps_longitude": str(gps_pos[0]), "gps_latitude": str(gps_pos[1])})
        for i in range(self.connection_retries_number):
            response = self.POST("API/track/start", start_data)
            if response.status_code == 200:
                logging.debug("Track started")
                break
            elif response.status_code == 409:
                logging.debug("Track exist, working on existing track")
                break
            else:
                logging.warning("Problem occurred while starting a new track: " + str(response.status_code))

    def check_authorization(self):
        response = self.GET("API/carAuthorization/status")
        if response.status_code == 200:
            logging.debug("Track started")
            return response.json()["logged"]
        elif response.status_code == 409:
            logging.debug("Track exist, working on existing track")
            return False
        else:
            logging.warning("Problem occurred while starting a new track: " + str(response.status_code))
            return False

    def create_own_response(self):
        self.failure_response.code = "expired"
        self.failure_response.error_type = "expired"
        self.failure_response.status_code = 400



class Config:

    def __init__(self, config_filename = 'config.ini'):
        # initializing config parser and checking if config file exist
        # if config file doesn't exist, create a new one
        # if file exist, read config
        self.config_filename = config_filename
        self.parser = configparser.ConfigParser()
        if not os.path.exists(self.config_filename):
            print("No config file")
        else:
            self.parser.read(self.config_filename)

    def section_returner(self, section):
        # returning a dictionary of requested section
        return dict(self.parser.items(section))


config = Config()
API = RequestAPI(config.section_returner('login'))
API.check_authorization()
czas = int(time.mktime(datetime.datetime.today().timetuple()))
inputjson = open(config.section_returner('file')["file"],'r')
parsedjson = json.load(inputjson)
track_starter = True
for i in parsedjson["_default"]:
    for j in parsedjson["_default"][i]:
        data = {czas: parsedjson["_default"][i][j]}
        if track_starter:
            poz = parsedjson["_default"][i][j]["gps_pos"]
            poz = poz["longitude"],poz["latitude"]
            API.start_track(poz)
            time.sleep(5)
            track_starter = False
        API.send_obd_data(data)
        czas+=1
        # print(data)
        time.sleep(1)

