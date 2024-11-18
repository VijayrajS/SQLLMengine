from langchain_community.utilities import SQLDatabase

class DatabaseConnection:
    def __init__(self, uri="sqlite:///Chinook.db"):
        """
        Initialize the database connection.

        Args:
            uri (str): The uri of the database.
        """
        uri = "mysql+mysqlconnector://root:Kavyasrit%402000@localhost/local_norp"
        self.db = SQLDatabase.from_uri(uri)
        # print(self.db.dialect)
        # print(self.db.get_usable_table_names())
        # self.db.run("SELECT * FROM Artist LIMIT 10;")

    def execute(self, query):
        """
        Method to execute the SQL query and return the results.
        """
        self.db.run(query)
