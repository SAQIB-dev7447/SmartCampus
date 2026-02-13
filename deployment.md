Smart Campus Deployment Guide
This guide describes how to deploy the Smart Campus application to a client PC (Windows).

Prerequisites
Python 3.10+: Ensure Python is installed and added to the System PATH.
Verify by opening PowerShell and typing: python --version
Internet Connection: Required initially to install dependencies.
Installation Steps
Copy Files: Copy the entire SmartCampus folder to the client PC (e.g., C:\SmartCampus).

Open Terminal: Open PowerShell or Command Prompt and navigate to the folder:

powershell
cd C:\SmartCampus
Create and Activate Virtual Environment:

powershell
python -m venv venv
.\venv_new\Scripts\python.exe run.py
Install Dependencies: Run the following command to install required libraries:

powershell
pip install -r requirements.txt
Initialize Database: Run the database initialization command (only needed once):

powershell
python -m flask --app app init-db
Running the Application
Option A: Using the Batch Script (Easiest)
Double-click the start_server.bat file in the folder. This will open a terminal window and start the server.

Option B: Manual Start
Run the following command in the terminal:

powershell
python run.py
Accessing the App
Local Access: Open your browser and go to http://127.0.0.1:5000.
Network Access (LAN): To allow other computers on the network to access the app:
Open run.py in a text editor.
Change app.run(debug=True) to app.run(host='0.0.0.0', port=5000).
Restart the server.
On other devices, access via http://[YOUR_PC_IP_ADDRESS]:5000.
Production Note
This setup uses the Flask development server. for a robust production deployment on Windows, consider using Waitress:

Install: pip install waitress
Create a file serve.py:
python
from waitress import serve
from app import create_app
app = create_app()
serve(app, host='0.0.0.0', port=8080)
Run: python serve.py

Comment
Ctrl+Alt+M



Admin — just go to login, select "Administrator", enter admin@campus.edu / admin123
Student — sign up with role "Student" (e.g. student1@uni.edu / pass123), then log in
Staff — sign up with role "University Staff" (e.g. staff@uni.edu / pass123), then log in