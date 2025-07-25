class User: 
	def __init__(self, username: str, status: str = "ONLINE"): 
		self.username = username
		self.status = status
		
	def __str__(self):
		return f"Username: {self.username}, Status: {self.status}"	
