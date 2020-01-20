# -*- coding: utf-8 -*-
import socket, sys
import threading
from time import strftime, localtime
import datetime

lock = threading.Lock()

class Server:
    def __init__(self, host='127.0.0.1', port=10080):
        #print("Python HTTP Web Server start", host + ":", port)
        self.running = True
        self.login = []
        self.maxclient = 100
        self.packetsize = 1024
        try:
            self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_addr = host, port
            self.serverSocket.bind(server_addr)
            self.running = True
            #print("Server success port:", port)
        except Exception as e:
            self.running = False
            #print("__init__() Exception: " + str(e))
        #print('=================================================================')

    def serverSocket_listen(self):
        self.serverSocket.listen(self.maxclient)
        while self.running:
            (client, address) = self.serverSocket.accept()
            t = threading.Thread(target=self.handle_client, args=(client, address))
            t.start()

    def handle_client(self, client, address):
        while True:
            try:
                #print("connection from:", address)
                data = client.recv(self.packetsize)
                self.send_response(bytes.decode(data), client)
                #print('--------------------------------------------------------------------------------')
            except:
                try:
                    client.send(b'HTTP/1.1 500 Internal Server Error\r\n\r\n')
                except:
                    pass
            finally:
                client.close()
                break

    def shutdown(self):
        try:
            #print("shutdown the server")
            self.running = False
            self.serverSocket.shutdown(socket.SHUT_RDWR)
            self.serverSocket.close()
            sys.exit()
        except Exception as e:
            print("shutdown() Exception: " + str(e))

    def generate_headers(self, id, code):
        header_server = 'Server: Python HTTP Web Server\n'
        header_cookie = ''
        if len(id) > 0:
            expires = datetime.datetime.now() + datetime.timedelta(seconds=30)  # expires in 30 secs
            maxage = 30
            header_cookie = 'Set-Cookie: user_id={a1}\n'.format(a1=id)
            header_cookie += 'Set-Cookie: max-age={a2}\n'.format(a2=maxage)
            header_cookie += 'Set-Cookie: expires={a3}\n'.format(a3=expires)
        header_connection = 'Connection: close\n\n'

        if code == 200:
            header = 'HTTP/1.1 200 OK\n'
        elif code == 403:
            header = 'HTTP/1.1 403 Forbidden\n'
        elif code == 404:
            header = 'HTTP/1.1 404 Not Found\n'
        return header + 'Date: ' + str(strftime("%Y-%m-%d %H:%M:%S", localtime())) +'\n' + header_server \
               + header_cookie + header_connection

    def cookie_string_parser(self, string):
        cookie_user_id = ''
        cookie_expires_str = ''
        if 'Cookie: ' in string:
            cookie_string = string.split('Cookie: ')[1]
            #print('cookie_string:', cookie_string)
            if 'user_id=' in cookie_string:
                cookie_user_id = cookie_string.split('user_id=')[1]
                cookie_user_id = cookie_user_id.split(';')[0]
                cookie_user_id = cookie_user_id.strip()
            if 'expires=' in cookie_string:
                cookie_expires_str = cookie_string.split('expires=')[1]
                cookie_expires_str = cookie_expires_str.split(';')[0]
                cookie_expires_str = cookie_expires_str.strip()
        return cookie_user_id, cookie_expires_str

    def send_response(self, string, conn):
        global lock
        id = ''
        request_method = string.split(' ')[0]
        #print ("Request body:\n\t", string.replace('\n', '\n\t'))
        #print ("Request body end.")

        if request_method == 'GET':
            error_code = 0
            file_requested = string.split(' ')[1].split('?')[0]

            now_time = datetime.datetime.now()
            cookie_expires = now_time
            cookie_user_id, cookie_expires_str = self.cookie_string_parser(string)
            #print("cookie_user_id:", cookie_user_id)
            #print("cookie_expires_str:", cookie_expires_str)

            if (len(cookie_expires_str) > 10):
                #print('cookie_expires_str:', cookie_expires_str)
                lock.acquire()
                try:
                    cookie_expires = datetime.datetime.strptime(cookie_expires_str, '%Y-%m-%d %H:%M:%S.%f')
                    #print('cookie_expires:', cookie_expires)
                    #print('now_time', now_time)
                    if (cookie_expires < now_time):
                        error_code = 403
                except Exception as e:
                    #print("datetime.datetime.strptime() Exception: " + str(e) + cookie_expires_str)
                    pass
                finally:
                    lock.release()

            if (file_requested == '/cookie.html'):
                if (len(cookie_user_id) == 0 or error_code == 403):
                    file_requested = '/'

            if (file_requested == '/secret.html'):
                error_code = 0
                login_string = string.split(' ')[1].split('login')[0]
                #print('login_string', login_string)
                if 'user_id=' in login_string:
                    id = login_string.split('user_id=')[1]
                    id = id.split('&')[0].strip()
                    self.login.append([id, localtime()])
                elif(cookie_expires < now_time):
                    error_code = 403

            if (file_requested == '/'):
                error_code = 0
                file_requested = '/index.html'

            try:
                if error_code == 0:
                    if (file_requested == '/cookie.html'):
                        timedelta = cookie_expires - now_time
                        response_content = '''
                                           <html lang="en">
                                               <head>
                                                   <meta charset="UTF-8">
                                                   <title>Welcome {idid}</title><p>
                                                    <script type="text/javascript">
                                                    <!--
                                                        setTimeout("location.reload()",1000)
                                                    //-->
                                                    </script>
                                               </head>
                                               <body>
                                                   <a>Hello {idid}</a><p>
                                                   <a>{leftleft} seconds left until your cookie expires.</a><p>
                                               <body>
                                           </html>'''.format(idid=cookie_user_id,
                                                             leftleft=round(timedelta.total_seconds()))
                        response_content = response_content.encode()
                    else:
                        file_requested = "." + file_requested
                        file_handler = open(file_requested, 'rb')
                        response_content = file_handler.read()
                        file_handler.close()
                    response_headers = self.generate_headers(id, 200)
                elif error_code == 403:
                    response_headers = self.generate_headers(id, error_code)
                    response_content = b"<html><body><h2>Error 403: Forbidden</h2></body></html>"
            except Exception as e:
                response_headers = self.generate_headers(id, 404)
                response_content = b"<html><body><h2>Error 404: File not found</h2></body></html>"
            data = response_headers.encode() + response_content
            conn.send(data)
        else:
            # print("Unknown HTTP request method:", request_method)
            pass

if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try :
        s.connect(('google.com', 80))
        IPAddr = s.getsockname()[0]
    except :
        hostname = s.gethostname()
        IPAddr = s.gethostbyname(hostname)
    finally:
        s.close()
    server = Server(host=IPAddr, port=10080)
    server.serverSocket_listen()