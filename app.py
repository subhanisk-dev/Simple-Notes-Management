from turtle import title

from flask import Flask,flash,render_template,request,redirect,url_for,session,send_file,jsonify #create client-side-server data
from flask_session import Session #Stores secure server side session

from io import BytesIO

import os
import re
from dotenv import load_dotenv
load_dotenv()
from otp import generate_otp
from cmail import send_mail
from stoken import entoken,dntoken

from datetime import datetime,timedelta

from mysql.connector import (connection)

mydb=connection.MySQLConnection(
    user=os.getenv("user"),host=os.getenv("host"),
    password=os.getenv("dbpassword"),db=os.getenv("db"))

#Flask Instailzing
app = Flask(__name__)

app.secret_key="Subhani123" #for ensuring secure way of storage data in sesions
#app confinguration
app.config["SESSION_TYPE"]="filesystem"
Session(app) #it intialize the session data

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
                    flash('User already existed')
                    return redirect(url_for('login'))
                cursor.execute('update userdata set otp=%s,otp_expiry_time=%s,account_status=%s where useremail=%s',[server_otp,otp_exipry_time,'inactive',useremail])
            else:
                cursor.execute('insert into userdata(username,useremail,userpassword,otp,otp_expiry_time,account_status) values(%s,%s,%s,%s,%s,%s)',[username,useremail,userpassword,server_otp,otp_exipry_time,'inactive'])
            mydb.commit()
            cursor.close()

            #sending OTP Mail To User
            subject='User OPT Verification for SNM Application'
            body=f'Hello {username} use Otp For verification {server_otp}'
            send_mail(subject=subject,body=body,to=useremail)
            flash('OTP has Sent to the Email')
            return redirect(url_for('otp_verify',useremail=useremail))
        return render_template('register.html')
    except Exception as e:
        print("Error Occurred at ",e)
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
                flash('user not found in DataBase')
                return redirect(url_for('register'))
            if user_otp_time>stored_userdata[1]:
                flash('OTP Expired pls try again')
                return redirect(url_for('register'))
            if stored_userdata[2]=='active':
                flash('User Already Existed Pls')
                return redirect(url_for('otp_verify',useremail=useremail))
            if user_otp!=stored_userdata[0]:
                flash('Invalid OTP pls Try Again')
                return redirect(url_for('otp_verify'))
            cursor.execute("update userdata set otp=null,otp_expiry_time=null,account_status= 'active' where useremail=%s",[useremail])
            mydb.commit()
            cursor.close()
            flash('OTP Verified Successfuly & Registered Successfully')
            return redirect(url_for('login'))
        return render_template('otp.html')
    except Exception as e:
        mydb.rollback()
        print("Error Occurred at ",e)
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
                flash('Email Not Found Pls try again')
                return redirect(url_for('register'))
            if user_data[0]=='active':
                if user_data[1]==login_password:
                    print("Before",session)
                    session['user']=login_useremail
                    print("After",session)
                    flash('Login SuccessFull')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Invalid Password')
                    return redirect(url_for('login'))
            else:
                flash('Your Account still not verifed register Again')
                return redirect(url_for('register'))
        return render_template('login.html')
    except Exception as e:
        print(e)
        return redirect(url_for('login'))

@app.route('/dashboard',methods=['GET'])
def dashboard():
    if not session.get('user'):
        flash('To access dashboard pls login first')
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/addnotes',methods=['GET','POST'])
def addnotes():
    try:
        if not session.get('user'):
                flash('To access dashboard pls login first')
                return redirect(url_for('login'))
        if request.method=='POST':
            print(request.form)
            Notestitle=request.form.get('title')
            Notescontent=request.form.get('content')
            if not Notestitle:
                flash('Title is Required')
                return redirect(url_for('addnotes'))
            mydb.ping(reconnect=True)
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
            userid=cursor.fetchone()
            if not userid:
                flash('User not Found Pls check')
            cursor.execute('insert into notesdata(notestitle,notescontent,added_by) values(%s,%s,%s)',[Notestitle,Notescontent,userid[0]])
            mydb.commit()
            cursor.close()
            flash(f'Notes Added successfully {Notestitle}')
            return redirect(url_for('addnotes'))
        return render_template('addnotes.html')
    except Exception as e:
        print('Error in added Notes',e)
        flash('Could add notes')
        return redirect(url_for('addnotes'))

@app.route('/viewallnotes',methods=['GET'])
def viewallnotes():
    try:
        if not session.get('user'):
                flash('To access dashboard pls login first')
                return redirect(url_for('login'))
        mydb.ping(reconnect=True)
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select notesid,notestitle,created_at from notesdata inner join userdata on notesdata.added_by=userdata.userid where userdata.useremail=%s',[session.get('user')])
        notes_data=cursor.fetchall()
        print(notes_data)
        return render_template('viewallnotes.html',notes_data=notes_data)
    except Exception as e:
        print("Error in Fetching",e)
        flash("Couldn't fetch ")
        return redirect(url_for('dashboard'))

@app.route('/viewnotes/<notesid>',methods=['GET'])
def viewnotes(notesid):
    try:
        if not session.get('user'):
            flash('To access dashboard pls login first')
            return redirect(url_for('login'))
        mydb.ping(reconnect=True)
        cursor=mydb.cursor(buffered=True)
        cursor.execute("select notesid,notestitle,notescontent,created_at from notesdata inner join userdata on notesdata.added_by=userdata.userid where userdata.useremail=%s and notesdata.notesid=%s",[session.get('user'),notesid])
        data=cursor.fetchone()
        print(data)
        return render_template('viewnotes.html',data=data)
    except Exception as e:
            print("Error in Fetching",e)
            flash("Couldn't fetch ")
            return redirect(url_for('dashboard'))

@app.route('/updatenotes/<notesid>',methods=['GET','POST'])
def updatenotes(notesid):
    try:
        if not session.get('user'):
            flash('To access dashboard pls login first')
            return redirect(url_for('login'))
        mydb.ping(reconnect=True)
        cursor=mydb.cursor(buffered=True)
        if request.method=='POST':
            updated_title=request.form.get('title')
            updated_content=request.form.get('content')
            cursor.execute("update notesdata set notestitle=%s,notescontent=%s where notesid=%s and added_by=(select userid from userdata where useremail=%s)",[updated_title,updated_content,notesid,session.get('user')])
            mydb.commit()
            flash('Notes Updated Successfully')
            return redirect(url_for('viewallnotes'))

        cursor.execute("select notesid,notestitle,notescontent from notesdata inner join userdata on notesdata.added_by=userdata.userid where userdata.useremail=%s and notesdata.notesid=%s",[session.get('user'),notesid])
        data=cursor.fetchone()
        if not data:
            flash('Notes Not Found')
            return redirect(url_for('viewallnotes'))
        print(data)
        return render_template('updatenotes.html',data=data)
    
    except Exception as e:
        print("Error in Fetching",e)
        flash("Couldn't fetch ")
        return redirect(url_for('dashboard'))

@app.route('/delete/<notesid>',methods=['GET'])
def delete_notes(notesid):
    try:
        if not session.get('user'):
            flash('To access dashboard pls login first')
            return redirect(url_for('login'))
        if not notesid:
            flash('Notes ID Not Found')
            return redirect(url_for('viewallnotes'))
        mydb.ping(reconnect=True)
        cursor=mydb.cursor(buffered=True)
        cursor.execute("select notesid from notesdata inner join userdata on notesdata.added_by=userdata.userid where userdata.useremail=%s and notesdata.notesid=%s",[session.get('user'),notesid])
        data=cursor.fetchone()
        if not data:
            flash('Notes Not Found')
            return redirect(url_for('viewallnotes'))
        cursor.execute("delete from notesdata where notesid=%s and added_by=(select userid from userdata where useremail=%s)",[notesid, session.get('user')])
        mydb.commit()
        cursor.close()
        flash('Note deleted successfully')
        return redirect(url_for('viewallnotes'))
    except Exception as e:
        print("Error in deleting note",e)
        flash("Couldn't delete note")
        return redirect(url_for('dashboard'))

@app.route('/uploadfile',methods=['GET','POST'])
def uploadfile():
    try:
        if not session.get('user'):
            flash('To access dashboard pls login first')
            return redirect(url_for('login'))
        if request.method == 'POST':
            filedata=request.files.get('file')
            fdata=filedata.read()
            filename=filedata.filename
            mydb.ping(reconnect=True)
            cursor = mydb.cursor(buffered=True)
            cursor.execute("INSERT INTO filesdata (filename, filedata,added_by) VALUES (%s, %s, (SELECT userid FROM userdata WHERE useremail = %s))", (filename, fdata, session.get('user')))
            mydb.commit()
            cursor.close()
            flash('File uploaded successfully')
            return redirect(url_for('dashboard'))
        return render_template('uploadfile.html')
    except Exception as e:
        print("Error in uploading file", e)
        flash("Couldn't upload file")
        return redirect(url_for('dashboard'))

@app.route('/viewallfiles',methods=['GET'])
def viewallfiles():
    try:
        if not session.get('user'):
            flash('To access dashboard pls login first')
            return redirect(url_for('login'))
        mydb.ping(reconnect=True)
        cursor = mydb.cursor(buffered=True)
        cursor.execute("SELECT filesid, filename, created_at FROM filesdata WHERE added_by = (SELECT userid FROM userdata WHERE useremail = %s)", [session.get('user')])
        files_data = cursor.fetchall()
        cursor.close()
        return render_template('viewallfiles.html', files_data=files_data)
    except Exception as e:
        print("Error in fetching files", e)
        flash("Couldn't fetch files")
        return redirect(url_for('dashboard'))

@app.route('/viewfile/<filesid>',methods=['GET'])
def viewfile(filesid):
    try:
        if not session.get('user'):
            flash('To access dashboard pls login first')
            return redirect(url_for('login'))
        mydb.ping(reconnect=True)
        cursor = mydb.cursor(buffered=True)
        cursor.execute("SELECT filename, filedata FROM filesdata WHERE filesid = %s AND added_by = (SELECT userid FROM userdata WHERE useremail = %s)", [filesid, session.get('user')])
        file_data = cursor.fetchone()
        cursor.close()
        if not file_data:
            flash('File not found')
            return redirect(url_for('viewallfiles'))
        return send_file(BytesIO(file_data[1]), as_attachment=False,download_name=file_data[0])
    except Exception as e:
        print("Error in fetching file", e)
        flash("Couldn't fetch file")
        return redirect(url_for('dashboard'))

@app.route('/downloadfile/<filesid>',methods=['GET'])
def downloadfile(filesid):
    try:
        if not session.get('user'):
            flash('To access dashboard pls login first')
            return redirect(url_for('login'))
        mydb.ping(reconnect=True)
        cursor = mydb.cursor(buffered=True)
        cursor.execute("SELECT filename, filedata FROM filesdata WHERE filesid = %s AND added_by = (SELECT userid FROM userdata WHERE useremail = %s)", [filesid, session.get('user')])
        file_data = cursor.fetchone()
        cursor.close()
        if not file_data:
            flash('File not found')
            return redirect(url_for('viewallfiles'))
        return send_file(BytesIO(file_data[1]),as_attachment=True,download_name=file_data[0])
    except Exception as e:
        print("Error in downloading file", e)
        flash("Couldn't download file")
        return redirect(url_for('dashboard'))


@app.route('/deletefile/<filesid>',methods=['GET'])
def deletefile(filesid):
    try:
        if not session.get('user'):
            flash('To access dashboard pls login first')
            return redirect(url_for('login'))
        mydb.ping(reconnect=True)
        cursor = mydb.cursor(buffered=True)
        cursor.execute("SELECT filesid FROM filesdata WHERE filesid = %s AND added_by = (SELECT userid FROM userdata WHERE useremail = %s)", [filesid, session.get('user')])
        file_data = cursor.fetchone()
        if not file_data:
            flash('File not found')
            return redirect(url_for('viewallfiles'))
        cursor.execute("DELETE FROM filesdata WHERE filesid = %s AND added_by = (SELECT userid FROM userdata WHERE useremail = %s)", [filesid, session.get('user')])
        mydb.commit()
        cursor.close()
        flash('File deleted successfully')
        return redirect(url_for('viewallfiles'))
    except Exception as e:
        print("Error in deleting file", e)
        flash("Couldn't delete file")
        return redirect(url_for('dashboard'))

@app.route('/usersearch',methods=['GET','POST'])
def usersearch():
    try:
        if not session.get('user'):
                flash('To access dashboard pls login first')
                return redirect(url_for('login'))
        searchdata=request.form.get('data')
        strg=['A-Za-z0-9']
        pattern = re.compile(f'^{strg}',re.IGNORECASE)
        if searchdata and pattern.match(searchdata):
            mydb.ping(reconnect=True)
            cursor=mydb.cursor(buffered=True)
            cursor.execute("SELECT notesid, notestitle, created_at FROM notesdata INNER JOIN userdata ON notesdata.added_by=userdata.userid WHERE userdata.useremail=%s AND notesdata.notestitle LIKE %s", [session.get('user'), searchdata+'%'])
            notesdata=cursor.fetchall()
            cursor.execute("SELECT filesid, filename, created_at FROM filesdata WHERE added_by = (SELECT userid FROM userdata WHERE useremail = %s) AND filesdata.filename LIKE %s", [session.get('user'), f'%{searchdata}%'])
            filesdata=cursor.fetchall()
            cursor.close()
            return render_template('searchresults.html',notesdata=notesdata,filesdata=filesdata)
        return render_template('usersearch.html')
    except Exception as e:
        print("Error in Searching",e)
        flash("Couldn't Search")
        return redirect(url_for('dashboard'))

@app.route('/forgotpassword',methods=['GET','POST'])
def forgotpassword():
    try:
        if request.method=='POST':
            forgot_email=request.form.get("email")
            mydb.ping(reconnect=True)
            cursor=mydb.cursor(buffered=True)
            cursor.execute("select account_status from userdata where useremail=%s",[forgot_email])
            db_response=cursor.fetchone()
            if not db_response:
                flash("Could Not Fetch userdata")
                return redirect(url_for('forgotpassword'))
            if db_response=='inactive':
                flash("Please Register Again")
                return redirect(url_for('register'))
            if db_response=='suspended':
                flash("This email is suspended")
                return redirect(url_for('register'))
            resetlink=f"Use this Link to password update {url_for('newpassword',data=entoken(forgot_email),_external=True)}"
            subject="Reset Link for Notes"
            send_mail(to=forgot_email,subject=subject,body=resetlink)
            flash("Sending Mail pls Check")
            return redirect(url_for('forgotpassword'))
        return render_template('forgotpassword.html')
    except Exception as e:
        print("Error",e)
        flash("Couldn't Retireve")
        return redirect(url_for('dashboard'))

@app.route('/newpassword/<data>',methods=['GET','PUT'])
def newpassword(data):
    try:
        de_serialised_email=dntoken(data)
        if request.method=='PUT':
            print(request.get_json())
            newpassword=request.get_json()['password']
            confirmpassword=request.get_json()['cpassword']
            if (not newpassword) or (not confirmpassword):
                return jsonify({"status":"failed","message":"password or confirmpassword required"}),400
            mydb.ping(reconnect=True)
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select account_status from userdata where useremail=%s',[de_serialised_email])
            db_response=cursor.fetchone() #('active',) or None
            if not  db_response:
                return jsonify({"status":"failed","message":"User not found"}),400
            if db_response[0]=='Inactive':
                return jsonify({"status":"failed","message":"User not Verified"}),400
            if db_response[0]=='suspended':
                return jsonify({"status":"failed","message":"User email suspended"}),400
            cursor.execute('update userdata set userpassword=%s where useremail=%s',[newpassword,de_serialised_email])
            mydb.commit()
            return jsonify({"status":"ok","message":"password updated successfully"}),200
        return render_template('newpassword.html',token=data)  
    except Exception as e:
        print(e)
        return jsonify({"status":"failed","message":f"{str(e)}"}),500

@app.route('/userlogout',methods=['GET'])
def userlogout():
    if not session.get('user'):
        flash('TO LOGOT PLS LOGIN')
        return redirect(url_for('login'))
    session.pop('user') #deletes user session data
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True,use_reloader=True)