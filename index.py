#Import Statements
from flask import Flask,render_template
from pymongo import MongoClient #MongoClient for python
import json #For creating JSON
from objdict import ObjDict #For creating JSON
from flask import request #for handling GET and POST requests
from flask_login import LoginManager
from flask_wtf import Form
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired
from flask import request, redirect, render_template, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash
import jwt
import datetime
import requests
import ast
#from Encrypt import AESCipher
import ast

#Variable Declaration
app = Flask(__name__)
client = MongoClient('localhost',27017) #Client connection
medipass = client.medipass
meditrack = client.meditrack
emergency_db = meditrack.emergency_db
pl = medipass.prescription_list
cl = medipass.consultation
doctor = medipass.doctor
ud = meditrack.user_data
d_inbox = meditrack.d_inbox

#Login
app.config.from_object('config')
lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'

uid = "100"
did = "500"
#Class Definitions
class User():
    def __init__(self,username):
        self.username = username
        self.password = None

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.username

    @staticmethod
    def validate_login(password_hash, password):
        return check_password_hash(password_hash, password)

#Defining the LoginFousernameclass

class LoginForm(Form):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])#

#Application Endpoints
#Login
@app.route('/authenticate', methods=['POST'])
def authenticate():
    form = LoginForm()
    client = MongoClient('localhost', 27017)
    user = users_db.find_one({"username": request.form['username']})

    if user and User.validate_login(user['password'], request.form['password']):
        user_secret_key = jwt.encode({'status' : 'success' , 'date' : str(datetime.date.today())},app.config['AUTH_SECRET_KEY'],algorithm='HS256')
        return user_secret_key
    return 'Invalid Username or Password!'

@app.route('/authorize',methods = ['POST'])
def authorize():
    access_token = request.form['access_token']
    try:
        res = jwt.decode(access_token,app.config['AUTH_SECRET_KEY'],algorithm='HS256')
    except:
        return '0'

    if (res['status'] == 'success'):
        print (res['date'])
        return '1'
    return '0'


@app.route('/logout')
def logout():
    logout_user()
    return '1'

##
@app.route("/doc")
def doc_index():
    did={"lineChart":[[2015,10],[2016,8],[2017,11],[2018,6],[2019,10]],"appointments":10,"gaugeChart":{"year":2019,"number":10},"barChart":{"seriesKeys":['types', 'General',
         'Peadiatrics', 'Others' ],"seriesYears":[]},"pieChart":{"emergency":21,"normal":5,"unavailable":4}}
    did["d_inbox_count"]=str(meditrack["d_inbox"].find({}).count())
    did["d_inbox_patients"]=len(meditrack.d_inbox.distinct("patient_id"))

    return render_template("/doctor/index.html" , did = did)
@app.route("/patients")
def patients():
    doctorRecords=meditrack["d_inbox"].find({"doctor_id":"500"},{"patient_id":1})
    tableData={}
    for record in doctorRecords:
        results=emergency_db.find({"id":record["patient_id"]},{"name":1,"id":1})        
        for rec in results:
            tableData[rec["name"]]=rec["id"]
    did={"tableData":tableData}
    return render_template("/doctor/patientListing.html" , did = did)
@app.route("/reports/<id>")
def reports(id):
    cards={}
    response=requests.get("http://localhost:8000/data_access_history")
    print ("response status code  for data_access_history  is "+str(response.status_code))
    doctorRecords=meditrack["d_inbox"].find({"patient_id":id,"doctor_id":"500"},{"data_id":1})
    cardNum=[]
    for rec in doctorRecords:
        cardNum.append(rec["data_id"])
    for cardNo in cardNum:
        cardData=meditrack["user_data"].find_one({"data_id":cardNo,"user_id":id})
        print (type(eval(cardData["data"])))
        cards[cardData["data_name"]]={}
        temp=eval(cardData["data"])
        url = "http://localhost:8000/transactions/new"
        #json.dumps({"Operation":"opened / read patient ","doctorID":"500","dataCategory":cardNo,"patientID":id})
        payload = "Operation=opened&doctorID=500&dataCategory="+cardNo+"&patientID="+id
        headers = {
            'content-type': "application/x-www-form-urlencoded",
            'cache-control': "no-cache",
            'postman-token': "1d30fcc4-6847-9e2b-6c8e-f16da4bd91f8"
            }

        response = requests.request("POST", url, data=payload, headers=headers)
        print (response.status_code," req to blockchain")
        for i in temp:
            cards[cardData["data_name"]][i[0]]=i[1]
    emergencyDetails=emergency_db.find_one({"id":id})
    print (emergencyDetails)
    cards["Emergency Details"]=emergencyDetails
    
    name=emergencyDetails["name"]
    bloodPressure={"value":emergencyDetails["bp"],"status":"Good"}
    caseType=emergencyDetails["oc"]
    if emergencyDetails["oc"]=="None":
        caseType="Normal"
    sugarLevel=emergencyDetails["sugarLevel"]
    bodyTemperature=emergencyDetails["temperature"]
    cards["Emergency Details"].pop("bp",None)
    cards["Emergency Details"].pop("sugarLevel")
    cards["Emergency Details"].pop("temperature")
    cards["Emergency Details"].pop("oc")
    cards["Emergency Details"].pop("_id")
    cards["Emergency Details"].pop("id")
    
    
    return render_template("/doctor/reports.html",name=name.upper(),bloodPressure=bloodPressure,caseType=caseType,
    bodyTemperature=bodyTemperature,sugarLevel=sugarLevel,cards=cards)
@app.route("/d_cards",methods = ['GET'])
def data_card1():
    user_id = request.args['id']
    categ = ["Blood Information","Morphological Information", "ENT Information","Orthopediac Information","Cardial Information"]
    data_id = request.args['data_id']
    u_data = ud.find_one({"user_id" : str(user_id) , "data_id" : str(data_id) })
    u_data_container =  u_data['data_container']
    res = []
    u_data_keys = u_data_container.keys()

    for i in u_data_keys:
        data = {}
        data['attribute'] = str(i)
        data['value'] = u_data_container[i]
        data['normal_value'] = 1
        res.append(data)
    return render_template("/doctor/d_cards.html",title = categ[int(data_id)-1] , data = res  , data_id = data_id)

##
@app.route("/doc_qrcode")
def doc_qrcode():

    return render_template("/doctor/qrcode.html")
##
@app.route('/add_data_inbox')
def add_data_inbox():
    device_type_count = [2,2,2,2]
    doctor_id = request.args['doctor_id']
    patient_id = request.args['patient_id']
    data_id = request.args['data_id']
    d_inbox.insert({ "doctor_id" : doctor_id , "patient_id" : patient_id , "data_id" : data_id })
    return render_template("/customer/dashboard.html",device_type_count = device_type_count,uid = patient_id)
##
@app.route('/show_data_inbox')
def data_inbox():
    title = ["Blood Information","Morphological Information", "ENT Information","Orthopediac Information","Cardial Information"]
    res = []
    doctor_id = request.args['doctor_id']
    d_inbox_list = d_inbox.find({ "doctor_id" : doctor_id })

    for i in d_inbox_list:
        #print i['patient_id']
        p_details = emergency_db.find_one({"id" : str(i['patient_id'])})
        data = {}
        data['title'] = p_details['name']
        data['description'] = title [ int(i['data_id']) - 1]
        data['data_id'] = i['data_id']
        res.append(data)

    return render_template("/doctor/data_inbox.html",data = res , uid = uid, id = uid , did = did)
    #return '1'

@app.route("/")
def index():
    device_type_count = [2,2,2,2]
    #device_type_count.append(devices_db.find({"Type" : "Pixel"}).count())
    #device_type_count.append(devices_db.find({"Type" : "Samsung"}).count())
    #device_type_count.append(devices_db.find({"Type" : "Iphone"}).count())
    #device_type_count.append(devices_db.find({"Type" : "Ipad"}).count())
    return render_template("/customer/dashboard.html",device_type_count = device_type_count,uid = uid)

##
@app.route("/dashboard")
def dashboard():
    device_type_count = [2,2,2,2]
    #device_type_count.append(devices_db.find({"Type" : "Pixel"}).count())
    #device_type_count.append(devices_db.find({"Type" : "Samsung"}).count())
    #device_type_count.append(devices_db.find({"Type" : "Iphone"}).count())
    #device_type_count.append(devices_db.find({"Type" : "Ipad"}).count())
    return render_template("/customer/dashboard.html",device_type_count = device_type_count,uid = uid)

#This will list all the devices that are available in the database
@app.route("/test")
def test():
    return render_template("test.html")

##
#Endpoint to display details of a single device
@app.route("/emergency" , methods = ['GET'])
def emergency():
    user_id = request.args['id']
    print ("User id " + str(user_id))

    emergency_data = client.meditrack.emergency_db.find_one({"id" : str(user_id) })
    data = {}
    # for i in emergency_data:
    #     data['id'] = i['id']
    #     data['name'] = i['name']
    #     data['age'] = i['age']
    #     data['gender'] = i['gender']
    #     data['number'] = i['number']
    #     data['address'] = i['address']
    #     data['blood'] = i['blood']
    #     data['diabetic'] = i['diabetic']
    #     data['bp'] = i['bp']
    #     data['carcinogenic'] = i['carcinogenic']
    #     data['oc'] = i['oc']
    # print (data)
    return render_template("/customer/emergency_info.html",data= emergency_data)


##
@app.route("/consultation_list",methods= ['GET'])
def consultation_list():
    res = []
    user_id = request.args['id']
    cl_list = cl.find({ "patient_id" : str(user_id)})
    #consultation_list_data = pl.find({"id" : user_id})
    #for i in consultation_list_data:
    #    data = {}
    #    data['pid'] = i['pid']
    #    data['doctor'] = i['doctor']
    #    data['date'] = i['date']
    #    res.append(data)

    for i in cl_list:
        data = {}
        data['d_id'] = i['doctor_id']
        x = doctor.find_one({'id' : str(i['doctor_id']) })
        data['doctor'] = x['name']
        data['date'] = i['date']
        res.append(data)
    print (res)
    return render_template("/customer/consultation_list.html",info_list = res,uid = user_id)

@app.route("/prescription" , methods = ['GET'])
def prescription():
    p_id_key = request.args['p_id']
    d_id_key = request.args['d_id']
    cli = cl.find_one({ "patient_id" : str(p_id_key) , "doctor_id" : str(d_id_key) })
    cl_list = cli['prescription']

    comment = cli['comments']

    res = []
    for i in cl_list:
        data = {}
        data['drug'] = i['drug']
        data['conc'] = i['conc']
        data['days'] = i['days']
        data['pattern'] = i['pattern']
        res.append(data)
    x= doctor.find_one({'id' : str(d_id_key) })
    return render_template("/customer/prescription.html",dr_name =  x['name'], data = res ,comm = comment)

##
@app.route("/all_information" , methods = ['GET'])
def all_information():
    user_id = request.args['id']
    info_id = [1,2,3,4,5]
    title = ["Blood Information","Morphological Information", "ENT Information","Orthopediac Information","Cardial Information"]
    description = ["Contains Sugar level,RBC count,WBC count,etc","Contains height,weight,Flat foot info,etc","Contain eyesight,thyroid,sinus information etc","Contains calcium level,Bone density etc","contains sodium,pottasium,cholestrol,etc information"]
    res = []

    for i in range(0,len(title)):
        data = {}
        data['info_id'] = info_id[i]
        data['title'] = title[i]
        data['description'] = description[i]
        res.append(data)
    return render_template("/customer/all_information.html",info_list = res,uid = user_id)


@app.route("/data_card",methods = ['GET'])
def data_card():
    user_id = request.args['id']
    categ = ["Blood Information","Morphological Information", "ENT Information","Orthopediac Information","Cardial Information"]
    data_id = request.args['data_id']
    print (user_id)
    print (data_id)
    u_data = ud.find_one({"user_id" : str(user_id), "data_id" : str(data_id)})
    u_data = u_data["data"]
    u_data = eval(u_data)
    print (type(u_data))
    print (u_data)

    res = []
    #  u_data_keys = u_data_container.keys()

    for i in u_data:
        data = {}
        data['attribute'] = i[0]
        data['value'] = i[1]
        data['normal_value'] = i[2]
        res.append(data)
    return render_template("/customer/data_card.html",title = categ[int(data_id)-1] , data = res , uid = uid , data_id = data_id)    
    #return "null"

@app.route("/add_a_device",methods=['GET'])
def add_a_device():
    barcode_value = request.args['barcode']
    print (barcode_value)
    return render_template("add_a_device.html",barcode = barcode_value)

@app.route("/add_device_into_db",methods=['POST'])
def add_device_into_db():
    try:
        name = request.form['name']
        devices_db.insert({"id" : int(request.form['id']) , "Name" : request.form['name'] , "IMEI" : request.form['imei'] , "MacAddress" : request.form['mac_address'] , "Manufacturer" : request.form['manufacturer'] , "DateOfProcurement" : request.form['dop'] , "Type" : request.form['type'] })
        return '1'
    except:
        return '0'

@app.route("/data_access_history",methods=['GET'])
def data_access_history():
    title = ["Blood Information","Morphological Information", "ENT Information","Orthopediac Information","Cardial Information"]
    p_id = request.args['pid']
    request_res = requests.get('http://167.71.221.150:8000/data_access_history?pid=' + p_id)
    res =  ast.literal_eval(request_res.text)
    final_res = []
    for i in res:
    #    print (i)
         data = {}
         x = doctor.find_one({"id" : i['doctorID']})
         data['d_name'] = "Vipul Gupta"
         data['operation'] = i['Operation']
    
         data['time'] = i['Time']
         final_res.append(data)
     
     
    print (res)
    return render_template("/customer/data_access_card.html", data = final_res)


if __name__ == '__main__':
    app.run('0.0.0.0',5000,debug = True)
