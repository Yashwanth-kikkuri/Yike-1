from django.shortcuts import render
import boto3
from boto3.dynamodb.conditions import Key, Attr
from django.contrib import sessions
from django.http import HttpResponseRedirect,HttpResponse
from django.conf import settings
from django.core.files.storage import default_storage
from datetime import datetime
from .forms import msgForm
import collections
import operator

def msg00(req):
    if 'email' in req.session:
        req.session["rec"]="yashukikkuri@gmail.com"
        for i in range (3 ,10) :
            send(req.session['email'],"yashukikkuri@gmail.com","This is a dummy message" + str(i))    
    return HttpResponse("<h1>Message has been sent</h1>")

# Create your views here.



def con(request):
    if request.method=='POST':
        request.session['rec']=request.POST.get('rec','')
        return HttpResponseRedirect('/chat/chat/')
    if ('email' in request.session):
        email=request.session['email']
        if(userisvalid(email)):
            username = getUserName(email)
            contacts = getContacts(email)
            contactsdetails = getContactdetails(contacts)
            return render(request,'Chatbox/ChatContant.html',{'user_data':username,'doctor_list':contactsdetails})
        else:
            del request.session['email']
            return  HttpResponseRedirect('login/')
    return  HttpResponseRedirect('login/')

def chat(request):
    if ('email' in request.session):
        email=request.session['email']
        if(userisvalid(email)):
            if 'rec' in request.session:
                rec = request.session['rec']
                if(userisvalid):
                    username = getUserName(email)
                    if request.method=='POST':
                        form=msgForm(request.POST)
                        if form.is_valid():
                            if (form.cleaned_data['msg'] is not None) | (form.cleaned_data['img'] is not None):
                                msg=form.cleaned_data['msg']
                                if msg != "" : 
                                    send(email,rec,msg)
                    form=msgForm()
                    return render(request,'Chatbox/chat.html',{'user_data':username,'form':form})
                else:
                    del request.session['rec']
            return HttpResponseRedirect('/chat/chatbox/')
    return HttpResponseRedirect('login/')

def msg(request):
    if ('email' in request.session):
        email=request.session['email']
        if(userisvalid(email)):
            if 'rec' in request.session :
                rec = request.session['rec']
                msg_list = getMessageList(email,rec)
                return render(request,'Chatbox/msg.html',{'msg_list':msg_list,'uid':email})
            else:
                del request.method['rec']
            return HttpResponseRedirect('/chat/chatbox/')
    return HttpResponseRedirect('/login/login/')

def userisvalid(email):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('users')
    response = table.scan(
        FilterExpression=Attr('email').eq(email)
    )
    if(len(response['Items'])==1):
        return True
    
    return False
    
def getUserName(email):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('users')
    response = table.scan(
        FilterExpression=Attr('email').eq(email)
    )
    if response["Count"] > 0:
        return response['Items'][0]['username']
    return "Yike User"

def getContacts(email):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('lastmessage')
    response = table.scan(
        ProjectionExpression="sender,reciver",
        FilterExpression=Attr('sender').eq(email) | Attr('reciver').eq(email)
    )
    data = response['Items']
    contacts= []
    for datum in data:
        if datum['sender']==email:
            contacts.append(datum['reciver'])
        else:
            contacts.append(datum['sender'])
    return contacts

def getReciver(email):
    contacts = getContacts(email)
    if len(contacts)>0 :
        return contacts[0]
    return 0

def send(sender,reciver,msg):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('message')
    date00=datetime.now()
    date0 = int(date00.strftime("%Y%m%d%H%M%S"))
    date1 = date00.strftime("%b %d\t|\t%H:%M")
    response1 = table.scan()
    u_id=len(response1['Items'])+1
    table.put_item(
        Item={
            'msg_id': u_id,
            'sort_key':date0,
            'sender': sender,
            'reciver': reciver,
            'messages': msg,
            'date_time':date1,
        }
    )
    table=dynamodb.Table('lastmessage')
    response = table.scan(
        ProjectionExpression="msg_id,sender,reciver",
        FilterExpression=Attr('sender').eq(sender) or Attr('sender').eq(sender)
    )
    msg_id =0
    if(response['Count']==1):
        msg_id=response['Items'][0]['msg_id']
        table.delete_item(
            Key={ 'msg_id' : msg_id },
        )
    else :
        response = table.scan()
        msg_id =response['Count']

    table.put_item(
        Item={
            'msg_id': msg_id ,
            'sender' : sender,
            'reciver': reciver,
            'date_time': date0,
            'messages': msg,
        }
    )
    
def getContactdetails(contacts):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('users')
    if(len(contacts)>0):
        response  = table.scan(
            ProjectionExpression="username,email",
            FilterExpression=Attr('email').is_in(contacts)
        )
        return response['Items'] 
    return contacts

def preview(req):
    email = req.session['email']
    if req.method=='POST':
        form=msgForm(req.POST)
        if form.is_valid():
            print("dil")
            if (form.cleaned_data['msg'] is not None) | (form.cleaned_data['img'] is not None):
                msg=form.cleaned_data['msg']
                if msg != "" : 
                    send(email,rec,msg)
        else : 
            print("ummmmmmmm")
    if "rec" not in req.session :
        re0 = getReciver(email) 
        if re0 != 0 :
            req.session['rec'] = re0
    if "rec" in req.session:
        rec = getUserName(req.session['rec'])
    else:
        rec = " "
    return render(req,'Chatbox/chatui.html',{ 'rec' : rec})


def recents(req):
    contactsdetails=[]
    messages = []
    if ('email' in req.session):
        email=req.session['email']
        if(userisvalid(email)):
            username = getUserName(email)
            contacts = getContacts(email)
            messages = getLastMessageList(email,contacts)
            contactsdetails = getContactdetails(contacts)
            j=0
            recents=[]
            for contact in contactsdetails : 
                recents.append([contact,messages[j]])
                j+=1
            return render(req,'Chatbox/recentchatui.html',{'recents':recents,'rec':req.session['rec']})
        return HttpResponseRedirect('/login/')
    return HttpResponseRedirect('/login/')

def mesgs(req):
    email =  req.session['email']
    reciver = req.session['rec']
    mesgs = getMessageList(email, reciver )
    print(mesgs)
    return render(req,'Chatbox/mesgs.html',{
        'mesgs'  : mesgs , 
         'rec' : reciver ,
    })

def getMessageList(email,person):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('message')
    response = table.scan(
        FilterExpression = (Attr('sender').eq(email) & Attr('reciver').eq(person)) | (Attr('reciver').eq(email) & Attr('sender').eq(person)),
        
    )
    print(response)
    return response['Items']



def getLastMessageList(email,person):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('lastmessage')
    if len(person) > 0 :
        response = table.scan(
            FilterExpression = (Attr('sender').eq(email) & Attr('reciver').is_in(person)) | (Attr('reciver').eq(email) & Attr('sender').is_in(person))
        )
        mesgs = response['Items']
        for msg in mesgs:
            if len(msg['messages']) > 110 : 
                msg['messages'] = msg['messages'][:105]+"....."
        return mesgs
    return []

