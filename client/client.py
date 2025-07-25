import tkinter as tk
from tkinter import ttk, messagebox
from common.user import User
from threading import Thread
from socket import *
import json
import pickle
import pyaudio
import wave
from client.audio_communication import AudioCommunication

# Change server parameters if needed	
SERVER_ADDRESS = "192.168.0.33"
SERVER_PORT = 9007


class CallDialog(tk.Toplevel):
	def __init__(self, parent, callerName, callerAddress, state):
		super().__init__(parent)

		self.geometry("200x150")
		self.grab_set()
		self.transient(parent)
	
		self.offset_x = 200
		self.offset_y = 50

		self.parent = parent
		self.callerName = callerName
		self.callerAddress = callerAddress
		self.state = state

		self.update_position()
		self.parent.bind("<Configure>", self.update_position)
		self.bind("<Configure>", self.update_offset)

		if self.state == "CALL_RECEIVED":
			acc_frame = ttk.Frame(self)

			lblCaller = ttk.Label(acc_frame, text=f"Incomming call from: {callerName}")

			btnAnswer = ttk.Button(acc_frame, text="Answer", command=self.answer_call)
			btnDecline = ttk.Button(acc_frame, text="Decline", command=self.decline_call)

			acc_frame.pack()
			lblCaller.pack(pady=30)
			btnAnswer.pack(side="left")
			btnDecline.pack(padx=10)

			self.ring_thread = Thread(target=self.play_ringtone, daemon=True)
			self.ring_thread.start()
			self.frame = acc_frame

		elif self.state == "CALL_SENT":
			wait_frame = ttk.Frame(self)

			lblCall = ttk.Label(wait_frame, text=f"Calling {callerName}...")
			btnEndCall = ttk.Button(wait_frame, text="End", command=self.end_call_for_both)
			wait_frame.pack()
			lblCall.pack(pady=10)
			btnEndCall.pack(side="bottom")
			self.frame = wait_frame


	def play_ringtone(self):
		
		try:
			self.ringtone = wave.open("client/ringtone.wav", "rb")
			CHUNK = 1024
			self.ring_p = pyaudio.PyAudio()
			self.ring_stream = self.ring_p.open(
				format=self.ring_p.get_format_from_width(self.ringtone.getsampwidth()),
				channels=self.ringtone.getnchannels(),
				rate=self.ringtone.getframerate(),
				output=True
			)

			self.ring_thread_running = True
			
			while self.ring_thread_running:
				data = self.ringtone.readframes(CHUNK)
				if not data:  
					self.ringtone.rewind()
					continue
				self.ring_stream.write(data)

		except Exception as e:
			print(f"Error playing ringtone: {e}")


	def stop_ringtone(self):

		self.ring_thread_running = False 
		
		if hasattr(self, "ring_stream"):
			self.ring_stream.close()
		if hasattr(self, "ring_p"):
			self.ring_p.terminate()
		if hasattr(self, "ringtone"):
			self.ringtone.close()


	def decline_call(self):
		print(f"Declining call from {self.callerName}")

		self.stop_ringtone()

		send_request(self.parent.client_socket, "DECLINE_CALL", [self.callerName])
		self.parent.unbind("<Configure>")
		delattr(self.parent, "call")
		self.destroy()

	def answer_call(self):
		
		self.stop_ringtone()
		self.set_in_call_frame()
		
		self.ac = AudioCommunication(self.callerAddress[0])
		self.ac.start_communication()
		self.state = "IN_CALL"
		# send address as response
		send_request(self.parent.client_socket, "ACCEPT_CALL", [self.callerName])
		
		
	def set_in_call_frame(self):
		self.frame.pack_forget()
		self.frame = ttk.Frame(self)

		lblCall = ttk.Label(self.frame, text=f"In a call with: {self.callerName}")
		btnEndCall = ttk.Button(self.frame, text="End", command=self.end_call_for_both)

		self.muteState = tk.StringVar(self.frame, value="Mute")
		btnMute = ttk.Button(self.frame, textvariable=self.muteState, command=self.mute_unmute)

		self.frame.pack()
		lblCall.pack(pady=10)
		btnEndCall.pack(side="bottom")
		btnMute.pack()

	def mute_unmute(self):
		if  self.muteState.get() == "Mute":
			self.ac.mute()
			self.muteState.set("Unmute")
		else:
			self.ac.unmute()
			self.muteState.set("Mute") 
		

	def end_call_for_both(self):
		if hasattr(self, "ac"):
			self.ac.stop_communication()

		send_request(self.parent.client_socket, "ENDING_CALL_FOR_BOTH", [self.callerName])
		self.parent.unbind("<Configure>")
		delattr(self.parent, "call")
		self.destroy()


	def update_offset(self, event=None):
		if self.winfo_exists():
			self.offset_x = self.winfo_x() - self.parent.winfo_x()
			self.offset_y = self.winfo_y() - self.parent.winfo_y()
	

	def update_position(self, event=None):
		if self.winfo_exists():
			self.geometry(f"+{self.parent.winfo_x() + self.offset_x}+{self.parent.winfo_y() + self.offset_y}")




class MainForm(tk.Tk):
	def __init__(self, user, client_socket):
		super().__init__()
		
		self.client_socket = client_socket
		self.running = True
		self.protocol("WM_DELETE_WINDOW", self.on_closing)
		self.user = user

		self.title(self.user.username)
		self.geometry("500x500")
		self.resizable(False, False)
		
		
		left_frame = ttk.Frame(self)
		right_frame = ttk.Frame(self)

		self.tvOnlines = ttk.Treeview(left_frame, columns=("name", "status"), show="headings")
		self.tvOnlines.heading("name", text="Name")
		self.tvOnlines.heading("status", text="Status")
		self.tvOnlines.column("name", width=100, anchor="center")
		self.tvOnlines.column("status", width=100, anchor="center")

		self.btnCall = ttk.Button(right_frame, text="Call", command=self.make_call)
		self.btnTest = ttk.Button(right_frame, text="Test", command=self.send_test_request)

		left_frame.place(relwidth=0.6, relheight=1, relx=0)
		right_frame.place(relwidth=0.4, relheight=1, relx=0.6)

		self.tvOnlines.pack(padx=10, pady=10, fill="x")
		self.btnCall.pack(anchor=tk.CENTER, pady=10)
		self.btnTest.pack(anchor=tk.CENTER, pady=10)

		self.update_thread = Thread(target=self.listen_for_updates, daemon=True)
		self.update_thread.start()

	def update_online_users(self, online_users):
		for row in self.tvOnlines.get_children():
			self.tvOnlines.delete(row)

		for user in online_users:
			self.tvOnlines.insert("", "end", values=user)

	def listen_for_updates(self):
		self.client_socket.settimeout(1)
		buffer = ""
		while self.running:
			try:
				response = self.client_socket.recv(4096).decode()
				if response:
					buffer += response
					while "\n" in buffer:
						json_str, buffer = buffer.split("\n", 1)
						response = json.loads(json_str)
						
						if response["info"] == "UPDATE_ONLINE_USERS":
							self.after(0, self.update_online_users, response["result"])

						elif response["info"] == "RESPONSE_TO_CALL":
							print(f'-----> {response["result"]["address"]}')
							if hasattr(self, "call"):
								if response["result"]["address"] == None:
									messagebox.showinfo(message=f'{response["result"]["from"]} has declined call')
									self.end_call()
								else:
									self.call.set_in_call_frame()
									self.call.ac = AudioCommunication(response["result"]["address"], 9011, 9010)
									self.call.state = "IN_CALL"
									self.call.ac.start_communication()

						elif response["info"] == "INCOMMING_CALL":
							# Make call dialog
							self.call = CallDialog(self, response["result"]["from"], response["result"]["address"], "CALL_RECEIVED")
							
						elif response["info"] == "STATUS_CHANGED":
							messagebox.showinfo(message=response["result"])

						elif response["info"] == "ENDING_CALL":
							self.end_call()
							messagebox.showinfo(message=f'{response["result"]} has ended call')
							
			except timeout:
				pass
			except OSError:
				break
			except Exception as e:
				print(f"Error receiving update: {e}")
				break  
		print("listen_for_updates() thread finished")


	def send_test_request(self):
		send_request(self.client_socket, "TEST_REQUEST")


	def req_change_status(self, newStatus):
		send_request(self.client_socket, "CHANGE_STATUS", [newStatus])


	def make_call(self):
		selected_item = self.tvOnlines.selection()

		if selected_item:
			values = self.tvOnlines.item(selected_item[0], "values")  
			usernameToCall, status = values
			if status != "BUSY":
				send_request(self.client_socket, "GET_IP", [usernameToCall])
				self.call = CallDialog(self, usernameToCall, None, "CALL_SENT")
			else:
				messagebox.showerror("Error", f"User is already in a call!")
		else:
			messagebox.showerror("Error", f"You must choose user to call!")
	

	def end_call(self):
		if (hasattr(self.call, "ring_thread") and self.call.ring_thread.is_alive()):
			self.call.stop_ringtone()
		
		if hasattr(self.call, "ac"):
			self.call.ac.stop_communication()

		self.call.destroy()
		delattr(self, "call")
		self.req_change_status("ONLINE")
	

	def on_closing(self):
		self.running = False  
		send_request(self.client_socket, "DISCONNECT")
		self.client_socket.close()
		
		if self.update_thread.is_alive():
			self.update_thread.join() 
		self.destroy()




class LoginForm(tk.Tk):
	def __init__(self):
		super().__init__()
		
		self.title("Connect")
		self.geometry("300x150")
		self.resizable(False, False)

		self.input_frame = ttk.Frame(master=self)

		self.label = ttk.Label(master=self.input_frame, text="Username: ", font="Arial 13")
		self.entry = ttk.Entry(master=self.input_frame)
		self.label.pack(side = "left")
		self.entry.pack()
		self.input_frame.pack(pady=10)

		btnConnect = ttk.Button(master=self, text="Connect", command=self.connect)
		btnConnect.pack()


	def connect(self):
		username = self.entry.get().strip()
		if self.check_username(username):
			try:
				u1 = User(username)
				serialized_u = pickle.dumps(u1)
				client_socket = socket(AF_INET, SOCK_STREAM)
				
				client_socket.connect((SERVER_ADDRESS, SERVER_PORT))
				client_socket.send(serialized_u)
				self.destroy()

				c = Client(client_socket,u1)

			except Exception as e:
				messagebox.showerror("Error", f"An error occurred: {e}")
		else:
			messagebox.showerror("Error", f"Invalid username!")
	

	@staticmethod
	def check_username(username):
		if (3 < len(username) < 15 and username.isalnum()):
			return True
		return False


def send_request(client_socket, operation, parameters=None):
	if parameters is None:
		parameters = []
	
	request = {
        "operation": operation,
        "parameters": parameters
    }
	
	try:
		# print(client_socket.fileno())
		client_socket.sendall(json.dumps(request).encode())

	except Exception as e:
		print(f"Error sending request: {e}")




class Client(Thread):
	def __init__(self, client_socket, user):
		super().__init__()
		self.client_socket = client_socket
		self.user = user
		self.start()
	
	def run(self):
		mf = MainForm(self.user, self.client_socket)
		mf.mainloop()
		

if __name__ == "__main__":
    window = LoginForm()
    window.mainloop()