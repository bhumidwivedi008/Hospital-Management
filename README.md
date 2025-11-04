Python - Flask
======================
This is a simple Python - Flask application. This application serves as a basic template for a web server using python for the backend, flask as the web application framework.

What does this application do?
-------------------------------
This application serves a simple web server that listens on defined port, default: `5000`.


# How to run?
You can run the application in one of the following ways:

1. Press `F5`. This will start the application in debug mode.

2. Open a terminal by going to 'View' -> 'Terminal'. Then, run following command: 
   > `flask --app app.py run --host=0.0.0.0 --port=5000 --debug`

This will start the application in development mode.


Via curl command:
-----------------
1. Open a terminal.
2. Type the following command: 
   > `curl http://localhost:5000`
3. Press 'Enter' to make the request.

Via Thunder Client:
-------------------
1. Click on the Thunder Client icon on the activity bar on the side. If you can't find it, you can search for 'Thunder Client' in the 'View' -> 'Extensions' menu.
2. Once Thunder Client is open, click on 'New Request'.
3. In the 'Request URL' field, enter the URL of your application (e.g., http://localhost:5000) and select the HTTP method from the dropdown menu.
5. Click on 'Send' to make the request.

Visit [Flask Quickstart](https://flask.palletsprojects.com/en/latest/quickstart/) for more information.

Happy coding! 🙂