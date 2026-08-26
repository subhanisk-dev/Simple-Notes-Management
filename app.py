from flask import Flask, render_template, request, redirect, url_for
import os
from dotenv import load_dotenv
load_dotenv()
from otp import generate_otp
from cmail import send_mail
from datetime import datetime,timedelta

from mysql.connector import (connection)

mydb=connection.MySQLConnection(
    user=os.getenv("user"),host=os.getenv("host"),
    password=os.getenv("dbpassword"),db=os.getenv("db"))

app = Flask(__name__)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
        if request.method=='POST':
            #Storing Data From User
            username = request.form.get('username')
            useremail = request.form.get('email')
            userpassword = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            #DB Storing details
            mydb.ping(reconnect=True) #it reconnect mysql server automatically if any blip or error occurs in db
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select account_status from userdata where useremail=%s',[useremail])
            db_response=cursor.fetchone()
            print(db_response)
            server_otp=generate_otp()
            otp_exipry_time=datetime.now()+timedelta(minutes=5)
            if db_response:
                if db_response[0]=='active':
                    return 'User already existed'
                cursor.execute('update userdata set otp=%s,otp_expiry_time=%s,account_status=%s where useremail=%s',[server_otp,otp_exipry_time,'inactive',useremail])
            else:
                cursor.execute('insert into userdata(username,useremail,userpassword,otp,otp_expiry_time,account_status) values(%s,%s,%s,%s,%s,%s)',[username,useremail,userpassword,server_otp,otp_exipry_time,'inactive'])
            mydb.commit()
            cursor.close()

            #sending OTP Mail To User
            subject='User OPT Verification for SNM Application'
            body=f'Hello {username} use Otp For verification {server_otp}'
            send_mail(subject=subject,body=body,to=useremail)
            return redirect(url_for('otp_verify',useremail=useremail))
        return render_template('register.html')
    except Exception as e:
        print(e)
        return redirect(url_for('register'))

@app.route('/otp_verify/<useremail>', methods=['GET', 'POST'])
def otp_verify(useremail):
    try:
        if request.method=='POST':
            #storing user entered otp
            user_otp=request.form.get('otp')
            user_otp_time=datetime.now()

            mydb.ping(reconnect=True)
            cursor=mydb.cursor(buffered=True)

            cursor.execute('select otp,otp_expiry_time,account_status from userdata where useremail=%s',[useremail])
            stored_userdata=cursor.fetchone()
            if not stored_userdata:
                return 'user not found in DataBase'
            if user_otp_time>stored_userdata[1]:
                return 'OTP Expired pls try again'
            if stored_userdata[2]=='active':
                return 'User Already Existed Pls'
            if user_otp!=stored_userdata[0]:
                return 'Invalid OTP pls Try Again'
            cursor.execute("update userdata set otp=null,otp_expiry_time=null,account_status= 'active' where useremail=%s",[useremail])
            mydb.commit()
            cursor.close()
            return redirect(url_for('login'))
        return render_template('otp.html')
    except Exception as e:
        print(e)
        return redirect(url_for('otp_verify',useremail=useremail))

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method=='POST':
            login_useremail=request.form.get("useremail")
            login_password=request.form.get("password")

            #accesing data from db
            mydb.ping(reconnect=True)
            cursor=mydb.cursor(buffered=True)
            cursor.execute("select account_status,userpassword from userdata where useremail=%s",[login_useremail])
            user_data=cursor.fetchone()

            if not user_data:
                return 'Email Not Found Pls try again'
            if user_data[0]=='active':
                if user_data[1]==login_password:
                    return redirect(url_for('dashboard'))
                else:
                    return 'Your Account still not verifed register Again'
            else:
                return 'User Not verified'
        return render_template('login.html')
    except Exception as e:
        print(e)
        return redirect(url_for('login'))

@app.route('/dashboard',methods=['GET'])
def dashboard():
    return render_template('dashboard.html')

@app.route('/addnotes',methods=['GET','POST'])
def addnotes():
    if request.method=='POST':
        #access the note details
        #store in db
        return redirect(url_for('dashboard'))
    return render_template('addnotes.html')

@app.route('/viewnotes',methods=['GET'])
def viewnotes():
    #fetch all notes from db
    return render_template('viewallnotes.html')

if __name__ == '__main__':
    app.run(debug=True,use_reloader=True)