#All the imports
from flask import Flask, render_template, request, url_for, redirect, session, flash
from hashlib import sha512
from db_control import *
from time import mktime
import feedparser
import json
import re
import datetime

#Creates a new flask application
app = Flask(__name__)

#The secret key is used to sign session cookies to stop they being tampered with
app.secret_key = "seckey12345"

#This creates a new database object
#Refer to 'db_control.py' for more information about the database handling
db = Database("users.db")

#This tries to make 2 new tables within the database
try:
	#Creates a table with the name "creds" (short for credentials) and with the attributes (column headers) of 'username' and 'password'
	db.create_table("cred",('username','password'))

	#Creates a table with the name "feeds" and with the attributes of 'username' and 'feed'
	db.create_table("feeds",('username','feed'))
except:
	#If and exception is raised then that means theses tables already exist
	print("Tables in database already exist.")

#Opens a JavaScript Object Notation file which contains all the url's for the different RSS feeds
#This file has the structure off:
'''
{
	"news_station_1" : {
		"link" : "url/to/xml/for/rss/feed1",
		"name" : "This is the name of the station which will be displayed to the user e.g. News Station 1"
	},
	"news_station_2" : {
		"link" : "url/to/xml/for/rss/feed2",
		"name" : "News Station 2"
	}
}
'''
with open("feed_urls.json") as f:
	#The contents of the file is loaded in as a python dictionary
	url_data = json.load(f)

#This is a function to remove any html from a string
def remove_html(s):
	#A regular expression is used to identify any html text (as we know all html will be between < and >) and replace it with a blank string
	new_string = re.sub("<.*?>","",s)
	#The sanitised string is then retured
	return new_string

#This is a function that removes any special characters from a string
def remove_s_chars(s):
	#Again a regex is used for this
	new_string = re.sub("&#.*?;"," ",s)
	#The sanitised string is then retured
	return new_string

#Jinja is used for the html templating so this allows use to use functions within the html file
@app.template_filter("format_time")
def format_time(t):
	#'t' will be in the form of a unix timestamp and then it is converted in to datetime
	t = datetime.datetime.fromtimestamp(t)
	#This datetime is then formatted to make more sense, the seconds get ommited and then it is returned
	return format(t, '%Y/%m/%d %H:%M')

#This adds the default root to the flask app and allows it with the methods of GET and POST
@app.route("/", methods=["POST", "GET"])
def log_in():
	#If data is posted to the server
	if request.method == "POST":
		#Requests all the form data 
		data = request.form

		#Gets the entered username from the form data
		username = data["username"]

		#Gets the password from the form data and then hashes it with SHA(secure hashing algorithm)512 as this is a password so it is important that it is kept secure
		password = sha512((data["password"]).encode()).hexdigest()

		#Gets all results from the "cred" table with the entered username
		db_results = db.get_values("cred","username",username)

		#If some results are recieved from the database
		if len(db_results) > 0:
			#If the hash of the password entered matches the hash of the password stored in the databse linking to the username then the user is valid
			if db_results[0][1] == password:
				#Sets the username stored in the session to the entered username
				session["username"] = username

				#Sets the maximum number of articles the user will recieve (option to change this on the page)
				session["max_items"] = 15

				#Redirects the user to the feed page where they will be able to view the headlines
				return redirect(url_for("feed"))
			else:
				#If the password hashes don't match then the user entered incorrect credentials and "Incorrect credentials!" is displayed to the user
				flash("Incorrect credentials!")
		else:
			#If the entered username is not in the database then the user entered incorrect credentials
			flash("Incorrect credentials!")

	#Renders log in html file
	return render_template("log_in.html")

#This adds the sign up route to the app with the GET and POST methods allowed
@app.route("/sign-up", methods=["POST", "GET"])
def sign_up():
	#If data is posted to the server
	if request.method == "POST":
		#Gets all the entered data from the form
		data = request.form
		username = data["username"]
		password = sha512((data["password"]).encode()).hexdigest()

		#If the entered username doesnt currently exists in the credentials database
		if len(db.get_values("cred","username",username)) == 0:
			#Adds the new username and hashed password to the "cred" table in the database
			db.insert_values("cred",(username, password))
			#Sets the session username to the username that the user entered
			session["username"] = username

			#Sets the maximum number of articles the user will recieve (option to change this on the page)
			session["max_items"] = 15

			#Creates a blank string where the RSS feeds they subscribe to will be stored
			selected_stations = ""

			#This loops through all the input fields posted to the server
			for station in data:
				#If the field is not the username or password
				if station not in ["username", "password"]:
					#It will add that station to the selected station string followed by a comma
					selected_stations += station+","

			#Adds the users selected feeds/news stations to the "feeds" table with the user's username as the primary key
			db.insert_values("feeds",(username, selected_stations))

			#Redirects the user to the feed page where they will be able to view the headlines
			return redirect(url_for("feed"))
		else:
			#If the username they entered already exists within the "cred" table
			flash("This username already exists!")

	#Returns the html file for the sign up page along with the data for the news feed url's,
	#this data is passed through to the sign up page as this allows the user to choose what news stations they want to subscribe to
	return render_template("sign_up.html", url_data=url_data)

#This adds the feed route to the app
@app.route("/feed")
def feed():
	#For the users news feed to be displayed they need to be logged in so if they arent logged in then they are redirected to the log in page
	if "username" not in session:
		return redirect(url_for("log_in"))

	#First the "feeds" table is queried for the "feed" of the user with the given username,
	#since the feed is in the format of "feed1,feed2,feed3," the database result is then split up with a "," as the separator
	my_feed_urls = db.get_values("feeds","username",session["username"])[0][1].split(",")
	#Since the feed ends in a comma when the string is split by comma location it causes an empty string to be added to the resultant list so this removes it
	my_feed_urls = list(filter(None, my_feed_urls))

	#An empty list where the articles are going to be added to
	my_feed_data = []
	#Itterates through all of the RSS stations the user has selected
	for src in my_feed_urls:
		#Requests and parses the RSS feed from the link for that station
		result = feedparser.parse(url_data[src]["link"])

		#Itterates though all of the items in the the previously requested feed
		for item in result["items"]:
			#Sets the articles "src" (source) to the display name for that station
			item_data = {"src" : url_data[src]["name"]}

			#If the article has a title
			if "title" in item:
				#Removes any html and/or special characters from the title and sets the articles title to it
				item_data["title"] = remove_s_chars(remove_html(item["title"]))
			else:
				#If it doesnt have a title then the articles title is set to None
				item_data["title"] = None

			#If the article has a summary
			if "summary" in item:
				#Removes any html and/or special characters from the summary and sets the articles summary to it
				item_data["summary"] = remove_s_chars(remove_html(item["summary"]))
			else:
				#If it doesnt have a summary then the articles summary is set to None
				item_data["summary"] = None

			#Different RSS feeds have different keys for the time it was published so this is to get the time regardkess of what key is being used
			if "published_parsed" in item:
				#Sets the articles time to the unix timestamp for when it was published
				item_data["time"] = mktime(item["published_parsed"])
			elif "updated_parsed" in item:
				#Sets the articles time to the unix timestamp for when it was published
				item_data["time"] = mktime(item["updated_parsed"])
			else:
				#If the time of publication is unable to be found then the articles time if set to None
				item_data["time"] = 0

			#If a link to the original article is found it is added to the articles data
			if "link" in item:
				item_data["link"] = item["link"]
			elif "links" in item:
				item_data["link"] = item["links"]["href"]
			else:
				item_data["link"] = None

			#Adds the article to the users feed data
			my_feed_data.append(item_data)

	#Once all of the articles have been added to the users feed the feed is then sorted bassed on when the articles where published,
	#this sorts it so that the newly published articles will be at the start of the list and therefore displayed at the top of the webpage
	my_feed_data = sorted(my_feed_data, key=lambda attr: attr["time"], reverse=True)

	#If there is more articles in the list than the maximum number of articles the user wants to see
	if session["max_items"] <= len(my_feed_data):
		#Then the users feed sliced so that it takes the first n elements where n is the maximum number of articles the user would like to see
		my_feed_data = my_feed_data[:session["max_items"]]

	#Returns the html file for the users feed along with the cusers 
	return render_template("feed.html", articles=my_feed_data, url_data=url_data, my_feed_urls=my_feed_urls)

#This adds the "update" route to the app with the POST and GET methods allowed
@app.route("/update", methods=["POST", "GET"])
def update():
	#To update the users preferences they need to be logged in
	if "username" not in session:
		#So if they arent looged in they are redirected to the login page
		return redirect(url_for("log_in"))

	#A try clause is used as it could be possible that someone visits "/update" and doesnt post and data to the server and if this wasnt handled for it could throw an exception for the user
	try:
		#Gets the data from the request
		req = str(request.data)
		#Splits the data in to a list
		#The format of this list is: [max_articles, "true"/"false", "true"/"false", "true"/"false" ...]
		#The value of these "true"/"false" statements represents the state of the checkboxes for the different RSS feeds where "true" means that thet user wants to view items from that feed
		req_data = req[3:len(req)-2].split(",")

		#The session is then updated with the the new maximum number of articles the user wishes to see
		session["max_items"] = int(req_data[0])

		#A new blank string is made where the new selected station will be stored
		new_selected_stations = ""
		#The data for all the RSS feeds is itterated through simultaneously with all the data in the request after the first element
		for station, state in zip(url_data, req_data[1:]):
			#If the state of the checkbox is "true" then we want to add that station to the new string of the selected stations
			if state == "true":
				#The station is added to the string along with a comma
				new_selected_stations += station+","

		#Then the "feeds" table is updated with the new selected station
		db.update_values(table_name="feeds", pk=session["username"], pk_cond="username", cond="feed", value=new_selected_stations)

	except Exception as e:
		#If an exception occurs it is just printed out
		print(e)

	#Returns the user back to the feed page
	return redirect(url_for("feed"))

#Adds the "log-out" route to the app
@app.route("/log-out")
def log_out():
	#If the user is logged in
	if "username" in session:
		#Remove their username from the session
		session.pop("username", None)

	#Redirect the user to the log in page
	return redirect(url_for("log_in"))

#Main
if __name__ == "__main__":
	#Runs the app on the servers ip, the default HTTP port and in threaded mode to allow the server to efficently handle multiple users.
	app.run(host='0.0.0.0', port=80, threaded=True)
