from __future__ import print_function
from ast import Break
from cgitb import html
from dis import dis
import email
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import sys
import MySQLdb.cursors
import re
import numpy as np
import pandas as pd
from soupsieve import select
app = Flask(__name__, template_folder='templates')


app.secret_key = 'your secret key'

app.config['MYSQL_HOST'] = 'foodflix.cwrr6um6hx4i.us-west-1.rds.amazonaws.com'
app.config['port'] = '3306'
app.config['MYSQL_USER'] = 'admin'
app.config['MYSQL_PASSWORD'] = 'adminadmin'
app.config['MYSQL_DB'] = 'foodflixdb'

mysql = MySQL(app)

@app.route('/')
@app.route('/login', methods =['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM userdata WHERE email = %s AND password = %s', (email, password))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['email'] = account['email']
            msg = 'Logged in successfully !'
            return redirect(url_for('search',email=email))
        else:
            msg = 'Incorrect email / password !'
    return render_template('newlogin.html', msg = msg)
@app.route('/register', methods =['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' :
        firstName = request.form['userName']
        email = request.form['email']
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM userdata WHERE email = %s', [email])
        account = cursor.fetchone()
        msg="Account already exists"
        if check(email):
            if account==None:
                password = request.form['password']
                if len(validate(password))==0:
                    cursor = mysql.connection.cursor()
                    cursor.execute("INSERT INTO userdata(firstName,email,password) VALUES (%s,%s,%s)", (firstName,email,password))
                    mysql.connection.commit()
                    cursor.close()
                    return redirect(url_for('input',email=email))
                else:
                    msg=validate(password)
        else:
            msg="Invalid Email ID"
    return render_template('newregister.html', msg = msg)



@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route("/input/<email>/", methods =['GET', 'POST'])
def input(email):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM dataset3")
    dishlist=cursor.fetchall()
    dishid=request.form.getlist("id")
    dishid=",".join(dishid)
    if len(dishid)>0:
        cursor.execute("select * from userdata where email=%s",[email])
        record = cursor.fetchone()
        input_data=dishid
        cursor.execute("Update userdata set preference=%s where email=%s ",[input_data , email ])
        mysql.connection.commit()
        cursor.execute("select id from userdata where email=%s ",[ email ])
        id = cursor.fetchone()
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("select * from userdata where id=%s ",[ id ])
        recipelist = cursor.fetchone()
        recipelist=list(recipelist["preference"])
        cur=""
        for i in range(len(recipelist)):
            
            if (recipelist[i]==",") or (recipelist[i]!="," and i==len(recipelist)):
                cursor.execute("INSERT INTO ratingdb(id, dish_id,rating) VALUES (%s, %s,%s)", (id, cur,5))
                cur=""
            else:
                cur=cur+recipelist[i]
            mysql.connection.commit()
        cursor.close()
        return redirect(url_for('search',email=email))
    return render_template("input.html",dishlist=dishlist )
    

@app.route("/success", methods =['GET', 'POST'])
def success():
    return render_template("success.html")
#endpoint for search
@app.route('/search/<email>', methods=['GET', 'POST'])
def search(email):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM new_ingredient")
    Category=cursor.fetchall()    
    if request.method == "POST":    
        RecipeCategory=request.form.getlist("id")
        dish = request.form['dish'] 
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        recipecat="SELECT * FROM dataset3"
        cursor.execute(recipecat)
        mysql.connection.commit()
        recipecat = cursor.fetchall()
        dataset3=pd.DataFrame(recipecat)
        recipelist=findbyingredient(RecipeCategory,dataset3)
        recipelist=tuple(recipelist)

        #dishl=[dish]
        #new_tup=tuple(dishl)
        numbing=("%s,"*len(recipelist))[:-1]
        where_in="("+numbing+")"
        #new_tup_n=new_tup+ingredients
        #print(new_tup_n)s
        if len(recipelist)>0 and len(dish)==0:
            cursor = mysql.connection.cursor()
            #selector='SELECT * from dataset WHERE Name LIKE "%'+dish+'%" AND RecipeCategory IN ('+ingredients+')'
            cursor.execute('SELECT * from dataset3 WHERE RecipeId IN' +where_in,recipelist)
            #selector='SELECT * from dataset WHERE Name LIKE "%%'+dish+'%%"'+'AND RecipeCategory IN' +where_in,ingredients
            #cursor.execute(selector)
        elif all(item == 38 for item in recipelist) and len(recipelist) > 2 and len(dish)!=0:
            cursor = mysql.connection.cursor()
            selector='SELECT * from dataset3 WHERE Name LIKE "%'+dish+'%" OR RecipeCategory LIKE "%%'+dish+'%%"'
            cursor.execute(selector)
        else:
            cursor = mysql.connection.cursor()
            selector='SELECT * from dataset3 WHERE (Name LIKE "%'+dish+'%" OR RecipeCategory LIKE "%%'+dish+'%%")'
            selector=selector + ' AND RecipeId IN'
            cursor.execute(selector+str(recipelist))
        mysql.connection.commit()
        data = cursor.fetchall()
        # all in the search box will return all the tuples
        if len(data) == 0 and dish == 'all': 
            cursor.execute("SELECT * from dataset3")
            mysql.connection.commit()
            data = cursor.fetchall()
        return render_template('testhome.html', data=data,dishlist=Category,email=email)
    return render_template('testhome.html',email=email,dishlist=Category)
@app.route('/recommend/<email>', methods=['GET', 'POST'])
def recommend(email):  
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        query="SELECT * FROM userdata WHERE email = '"+email+"'"
        cursor.execute(query)
        mysql.connection.commit()
        account = cursor.fetchone()
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        ratingdb="SELECT * FROM ratingdb"
        cursor.execute(ratingdb)
        mysql.connection.commit()
        ratingdb = cursor.fetchall()
        fdk=pd.DataFrame(ratingdb)
        #recipelist=recommendationfood(fdk, account["id"], numDish=20)
        recipelist=recommendationfood(fdk, 116, numDish=20)
        cursor = mysql.connection.cursor()
        recipelist=tuple(recipelist)
        numbing=("%s,"*len(recipelist))[:-1]
        where_in="("+numbing+")"
        cursor = mysql.connection.cursor()
        print(recipelist)
        cursor.execute('SELECT * from dataset3 WHERE RecipeId IN' +where_in,recipelist)
        mysql.connection.commit()
        data = cursor.fetchall()
        return render_template('justrecommend.html',email=email,data=data)
        #return redirect(url_for('recommendpage',email=email,recipelist=recipelist))
@app.route('/profile/<email>', methods=['GET', 'POST'])
def profile(email):  
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        query="SELECT * FROM userdata WHERE email = '"+email+"'"
        cursor.execute(query)
        mysql.connection.commit()
        account = cursor.fetchone()
        
        firstname=account["firstName"]
        lastname=account["lastName"]
        email=account["email"]
        cursor = mysql.connection.cursor()
        cursor.execute("select * from dataset3 where RecipeId in (SELECT dish_id from ratingdb where id=%s)",[id])
        mysql.connection.commit()
        data = cursor.fetchall()
        if request.method == "POST": 
            dish = request.form['dish']  
            cursor.execute('SELECT * from dataset3 WHERE  RecipeId in (SELECT dish_id from ratingdb where id=%s) and Name LIKE "%%'+dish+'%%"',[id])
            mysql.connection.commit()
            data = cursor.fetchall()
            return render_template('profile.html',data=data,firstname=firstname,lastname=lastname,email=email)
        return render_template('profile.html',data=data,userName=firstname,lastname=lastname,email=email)
@app.route('/rating/<email>/<itemid>/', methods=['GET', 'POST'])
def rating(email,itemid):
    if request.method == "POST": 
        rating = request.form['ratingrecipe']     
        cursor = mysql.connection.cursor()
        cursor.execute("select id from userdata where email = '"+email+"'")
        mysql.connection.commit()
        id_user = cursor.fetchone()
        cursor.execute("select * from ratingdb where id = %s and dish_id=%s",[id_user,itemid])
        mysql.connection.commit()
        myusers_recipeexist = cursor.fetchone()
        if myusers_recipeexist != None:
            cursor.execute("Update ratingdb set rating=%s",[rating])
            mysql.connection.commit()
        else:
             cursor.execute("INSERT INTO ratingdb(id, dish_id,rating) VALUES (%s, %s,%s)", (id_user, itemid,rating))
             mysql.connection.commit()
        return render_template('rating.html',email=email,itemid=itemid,rating=rating)
    return render_template('rating.html',email=email,itemid=itemid)


"""
@app.route('/recommendpage/<email>/<recipelist>/', methods=['GET', 'POST'])
def recommendpage(email,recipelist):
    if request.method == "POST": 
        cursor = mysql.connection.cursor()
        recipelist=tuple(recipelist)
        print(recipelist)
        numbing=("%s,"*len(recipelist))[:-1]
        where_in="("+numbing+")"
        cursor.execute('SELECT * from dataset WHERE RecipeId IN' +where_in,recipelist)
        mysql.connection.commit()
        data = cursor.fetchall()
        return render_template('justrecommend.html',email=email,data=data)
    return render_template('justrecommend.html')
"""
#python functionn fr recommending
def recommendationfood(ratingDb, targetUserId, numDish=20):
    recipeLst = []
    currentLst = list(ratingDb.dish_id[ratingDb["id"] == targetUserId])
    if len(currentLst)==0:
        if len(recipeLst)==0:
            for i in range(5):
                while True:
                    dish = np.random.choice(list(ratingDb.dish_id))
                    if dish not in recipeLst and dish not in currentLst:
                            recipeLst.append(dish)
                            break
        return recipeLst
    #userID,dishID,rating
    # Get the distance
    userId, distanceLst = getDistance(ratingDb, targetUserId)
    print(userId,distanceLst)
    # Get the ID of the top users
    topUserIds, smallestDistance = getTopUser(userId, distanceLst, numDish)
    print(topUserIds)
    # Get the recipes ID
    
    
    for i in range(len(topUserIds)):
        while True:
            dish = np.random.choice(list(ratingDb.dish_id[ratingDb["id"] == topUserIds[i]]))
            if dish not in recipeLst and dish not in currentLst:
                recipeLst.append(dish)
                break
    
    return recipeLst


def getTopUser(userId, distanceLst, numUser=20):
    nearestUser = []
    smallestDistance = []
    sortedIndex = np.argsort(distanceLst)
    i = 0
    while i < len(distanceLst) and len(nearestUser) < numUser:
        # Remove users that are identical
        if distanceLst[sortedIndex[i]] > 0:
            nearestUser.append(userId[sortedIndex[i]])
            smallestDistance.append(distanceLst[sortedIndex[i]])
        
        i += 1
    return nearestUser, smallestDistance


def getDistance(ratingDb, targetUser):
    userId = np.unique(ratingDb["id"])
    dishId = []
    rating = []
    distanceLst = [-1 for i in range(len(userId))]
    for i in range(len(userId) + 1):
        dishId.append(list(ratingDb.dish_id[ratingDb["id"] == i]))
        rating.append(list(ratingDb.rating[ratingDb["id"] == i]))
    # For each user, calculate the distance the target user
    for i in range(len(userId)):
        distance = 0
        if i != userId.index(targetUser):
            for j in range(len(dishId[userId.index(targetUser)])):
                if dishId[userId.index(targetUser)][j] in dishId[i]:
                    index = dishId[i].index(dishId[userId.index(targetUser)][j])
                    distance += abs(rating[userId.index(targetUser)][j] - rating[i][index])
            distanceLst[i] = distance
    return userId, distanceLst
def findbyingredient(userselect,dataset3):
    closest=[0 for i in range(len(dataset3))]
    closestindex=[]
    for i in range(len(dataset3)):
        for k in range(len(userselect)):
            if userselect[k] in dataset3.RecipeIngredientParts[i]:
                closest[i]+=1
    for i in range(10):
        closestindex.append(dataset3.RecipeId[closest.index(max(closest))])
        closest[closest.index(max(closest))]=0
    if len(closestindex)>20:
        return closestindex[0:20]
    else:
        return closestindex
def check(email):   
    regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'
    if(re.search(regex,email)):   
        return True 
    else:   
        return False
def validate(password):
    while True:
        if len(password) < 8:
            return("Make sure your password is at least 8 letters")
        elif re.search('[0-9]',password) is None:
            return("Make sure your password has a number in it")
        elif re.search('[A-Z]',password) is None: 
            return("Make sure your password has a capital letter in it")
        else:
            return("")
            break
if __name__ == '__main__':
    app.run()
