from langchain_community.utilities import SQLDatabase



class DatabaseConnection:
	def __init__(self, uri="sqlite:///Chinook.db"):
		"""
		Initialize the database connection.

		Args:
			uri (str): The uri of the database
		"""

		self.db = SQLDatabase.from_uri(uri)
		print(db.dialect)
		print(db.get_usable_table_names())
		db.run("SELECT * FROM Artist LIMIT 10;")

	def execute(self, query):
		db.run(query)

