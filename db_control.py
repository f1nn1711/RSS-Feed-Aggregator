#Import statements
import sqlite3

#Defines the class for the Database
class Database():
	#Database initialisation functionn which takes the databases files name as a parameter
	def __init__(self, filename):
		#Sets the filename to the database object
		self.filename = filename

		#The connection to the database must be opened in each statement as SQLite3 doesnt allow the use of a cursor opened in a different thread

	#Function to create a new table in the database
	def create_table(self, table_name, headers):
		#Connects the the database
		con = sqlite3.connect(self.filename)

		#Creates a new cursor in the table
		cur = con.cursor()

		#Formats the SQL statement with the passed values of a name for the table along with the headers/attributes for the columns in the table
		command = f"CREATE TABLE {table_name} {headers}"

		#Exceutes the command on the database
		cur.execute(command)

		#Commit the changes to the database
		con.commit()

		#Close the connection to the database
		con.close()

	def insert_values(self, table_name, values):
		con = sqlite3.connect(self.filename)
		cur = con.cursor()

		#This commands adds a set of values (a row) to a given table
		command = f"INSERT INTO {table_name} VALUES {values}"

		cur.execute(command)
		con.commit()
		con.close()

	def get_values(self, table_name, cond, value):
		con = sqlite3.connect(self.filename)
		cur = con.cursor()

		#Selects all of the rows in a given table where a certain condition matches a given value
		command = f"SELECT * FROM {table_name} WHERE {cond}='{value}'"

		result = cur.execute(command).fetchall()
		#Since this is command is not modifying the database then the it doesnt need to be committed

		con.close()

		#Return the result of the select command
		return result

	def update_values(self, table_name, pk, pk_cond, cond, value):
		con = sqlite3.connect(self.filename)
		cur = con.cursor()

		#This command updates a certain value in a table on rows where a certain attribute is equal to a certain value
		#Explanation of the parameters
		#"table_name" - this is the name of the table to be modified - an example would be "feeds"
		#"cond" - this is the attribute of the row which will be updated - an example is "feed"
		#"value" - this is the new value for the "cond" - an example would be 'bbc,sky,guardian,'
		#"pk_cond" - this is the attribute which will be compared to see if this row needs to be updates - an exmaple would be "username"
		#"pk" - this is what the "pk_cond" will be compared to to check if this row needs to be updates - an example would be "Hunt1234"
		command = f"UPDATE {table_name} SET {cond}='{value}' WHERE {pk_cond}='{pk}'"

		cur.execute(command)

		#This needs to be committed as executing this command has altered the database
		con.commit()
		con.close()
