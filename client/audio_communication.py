import pyaudio
from threading import Thread
import socket
import tkinter as tk
from tkinter import ttk


class AudioCommunication:
    def __init__(self, target_address, target_port = 9010, local_port = 9011):
        self.target_address = target_address
        self.TARGET_PORT = target_port
        self.LOCAL_PORT = local_port

        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.recv_socket.bind(("", self.LOCAL_PORT))  
        self.recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)

        self.chunk_size = 2048
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.p = pyaudio.PyAudio()
        
        self.is_muted = False
        self.coms_threads = False


    def record_audio(self):
        print("++++record_audio started++++")

        stream = self.p.open(format=self.format,
                         channels=self.channels,
                         rate=self.rate,
                         input=True,
                         frames_per_buffer=self.chunk_size)

        while self.coms_threads:
            data = stream.read(self.chunk_size, exception_on_overflow=False)
            if not self.is_muted:
                self.send_socket.sendto(data, (self.target_address, self.TARGET_PORT))

        print("------record_audio ended------")


    def play_audio(self):
        print("++++play_audio started++++")

        stream = self.p.open(format=self.format,
                         channels=self.channels,
                         rate=self.rate,
                         output=True,
                         frames_per_buffer=self.chunk_size)
        
        self.recv_socket.settimeout(1)

        while self.coms_threads:
            try:
                data, _ = self.recv_socket.recvfrom(65536)
                print(f"Received packet size: {len(data)} bytes")
                if data:
                    stream.write(data)
            except socket.timeout:
                continue
            except OSError as e:
                print(f"Socket error: {e}")
                break

        print("------play_audio ended------")
        stream.close()

    def start_communication(self):
        self.coms_threads = True
        
        self.record_thread = Thread(target=self.record_audio, daemon=True)
        self.play_thread = Thread(target=self.play_audio, daemon=True)

        self.record_thread.start()
        self.play_thread.start()

    def stop_communication(self):
        self.coms_threads = False
        self.record_thread.join()
        self.play_thread.join()

        self.send_socket.shutdown(socket.SHUT_RDWR)
        self.send_socket.close()

        self.recv_socket.shutdown(socket.SHUT_RDWR)
        self.recv_socket.close()
        self.p.terminate()

    def mute(self):
        self.is_muted = True

    def unmute(self):
        self.is_muted = False

# # TEST 1
# ac = AudioCommunication("192.168.0.19") # dodaj target address kao parametar konstruktora
# ac.start_communication()
# try:
#     while True:
#         sleep(1)  # Keeps the program running, allowing the threads to work
# except KeyboardInterrupt:
#     ac.stop_communication()


# TEST 2 - SIMPLE GUI
# def goo():
#     global ac
#     ac = AudioCommunication('192.168.0.19')
#     ac.start_communication()

# def open_call_window():
#    cw = tk.Toplevel(window)

#    btnStart = ttk.Button(cw, text='start', command=goo)
#    btnStart.pack()
   

# window = tk.Tk()
# btnOpen = ttk.Button(window, text="Open call window", command=open_call_window)

# btnOpen.pack()
# window.mainloop()