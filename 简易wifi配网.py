import network
import socket
import ure
import time

NETWORK_PROFILES = 'wifi.dat'

wlan_ap = network.WLAN(network.AP_IF)
wlan_sta = network.WLAN(network.STA_IF)

server_socket = None


def send_header(conn, status_code=200, content_length=None ):
    conn.sendall("HTTP/1.0 {} OK\r\n".format(status_code))
    conn.sendall("Content-Type: text/html\r\n")
    if content_length is not None:
      conn.sendall("Content-Length: {}\r\n".format(content_length))
    conn.sendall("\r\n")

def send_response(conn, payload, status_code=200):
    content_length = len(payload)
    send_header(conn, status_code, content_length)
    if content_length > 0:
        conn.sendall(payload)
    conn.close()

def config_page():
    return b"""<html>
                    <head>
                        <title>ESP32-C3 AP Test</title>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1">
                    </head>
                    <body>
                        <h1>Wifi 配网</h1>
                        <form action="configure" method="post">
                            <div>
                                <label>SSID</label>
                                <input type="text" name="ssid">
                            </div>
                            <div>
                                <label>PASSWORD</label>
                                <input type="password" name="password">
                            </div>
                            <input type="submit" value="连接">
                        <form>
                    </body>
                </html>"""


def wifi_conf_page(ssid, passwd):
    return b"""<html>
                    <head>
                        <title>Wifi Conf Info</title>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1">
                    </head>
                    <body>
                        <h1>Post data:</h1>
                        <p>SSID: %s</p>
                        <p>PASSWD: %s</p>
                        <a href="/">Return Configure Page</a>
                    </body>
                </html>""" % (ssid, passwd)

def connect_sucess(new_ip):
    return b"""<html>
                    <head>
                        <title>Connect Sucess!</title>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1">
                    </head>
                    <body>
                        <p>Wifi Connect Sucess</p>
                        <p>IP Address: %s</p>
                        <a href="http://%s">Home</a>
                        <a href="/disconnect">Disconnect</a>
                    </body>
               </html>""" % (new_ip, new_ip)

def get_wifi_conf(request):
    match = ure.search("ssid=([^&]*)&password=(.*)", request)

    if match is None:
        return False

    try:
        ssid = match.group(1).decode("utf-8").replace("%3F", "?").replace("%21", "!")
        password = match.group(2).decode("utf-8").replace("%3F", "?").replace("%21", "!")
    except Exception:
        ssid = match.group(1).replace("%3F", "?").replace("%21", "!")
        password = match.group(2).replace("%3F", "?").replace("%21", "!")

    if len(ssid) == 0:
        return False
    return (ssid, password)


def handle_wifi_configure(ssid, password):
    if do_connect(ssid, password):
#         try:
#             profiles = read_profiles()
#         except OSError:
#             profiles = {}
#         profiles[ssid] = password
#         write_profiles(profiles)
#         
#         time.sleep(5)
#         
        new_ip = wlan_sta.ifconfig()[0]
        return new_ip
    else:
        print('connect fail')
        return False

def check_wlan_connected():
    if wlan_sta.isconnected():
        return True
    else:
        return False

def do_connect(ssid, password):
    wlan_sta.active(True)
    if wlan_sta.isconnected():
        return None
    print('Connect to %s' % ssid)
    wlan_sta.connect(ssid, password)
    for retry in range(100):
        connected = wlan_sta.isconnected()
        if connected:
            break
        time.sleep(0.1)
        print('.', end='')
    if connected:
        print('\nConnected : ', wlan_sta.ifconfig())
    else:
        print('\nFailed. Not Connected to: ' + ssid)
    return connected

def read_profiles():
    with open(NETWORK_PROFILES) as f:
        lines = f.readlines()
    profiles = {}
    for line in lines:
        ssid, password = line.strip("\n").split(";")
        profiles[ssid] = password
    return profiles


def write_profiles(profiles):
    lines = []
    for ssid, password in profiles.items():
        lines.append("%s;%s\n" % (ssid, password))
    with open(NETWORK_PROFILES, "w") as f:
        f.write(''.join(lines))

def stop():
    global server_socket

    if server_socket:
        server_socket.close()
        server_socket = None

def startAP():
    global server_socket
    stop()
    wlan_ap.active(True)
    wlan_ap.config(essid='ESP32-C3',authmode=0)

    server_socket = socket.socket()
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 80))
    server_socket.listen(3)


    while not wlan_sta.isconnected():
        conn, addr = server_socket.accept()
        print('Connection: %s ' % str(addr))

        try:
            conn.settimeout(3)
            request = b""

            try:
                while "\r\n\r\n" not in request:
                    request += conn.recv(512)
            except OSError:
                pass

            # url process
            try:
                url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", request).group(1).decode("utf-8").rstrip("/")
            except Exception:
                url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", request).group(1).rstrip("/")
            print("URL is {}".format(url))

            if url == "":
                response = config_page()
                send_response(conn, response)
            elif url == "configure":
                ret = get_wifi_conf(request)
                ret = handle_wifi_configure(ret[0], ret[1])
                if ret is not None:
                    response = connect_sucess(ret)
                    send_response(conn, response)
                    print('connect sucess')
            elif url == "disconnect":
                wlan_sta.disconnect()

        finally:
            conn.close()
    wlan_ap.active(False)
    print('ap exit')

def home():
    global server_socket
    stop()
    wlan_sta.active(True)
    ip_addr = wlan_sta.ifconfig()[0]
    print('wifi connected')
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 80))
    server_socket.listen(3)

    while check_wlan_connected():
        conn, addr = server_socket.accept()
        try:
            conn.settimeout(3)
            request = b""

            try:
                while "\r\n\r\n" not in request:
                    request += conn.recv(512)
            except OSError:
                pass

            # url process
            try:
                url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", request).group(1).decode("utf-8").rstrip("/")
            except Exception:
                url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", request).group(1).rstrip("/")

            if url == "":
                response = connect_sucess(ip_addr)
                send_response(conn, response)
            elif url == "disconnect":
                wlan_sta.disconnect()             
        finally:
            conn.close()

    wlan_sta.active(False)
    print('sta exit')


def main():
    while True:
        if not check_wlan_connected():
            startAP()
        else:
            home()


main()