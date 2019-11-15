from django.shortcuts import render,redirect
from django.contrib import sessions
import copy
import boto3
from boto3.dynamodb.conditions import Key, Attr
import random
from urllib import parse
from django.http import HttpResponse, JsonResponse
import json
from django.views.decorators.csrf import requires_csrf_token

#For sending activation function
from django.http import HttpResponse
from django.contrib.auth import login, authenticate
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from .tokens import account_activation_token
from django.contrib.auth.models import User
from django.core.mail import EmailMessage

from django.contrib import messages

import datetime

#For generating password
import random
import string

#Hashing password
import hashlib



# Create your views here.
def dashboard(request,j):

    present=0 #User already present in organisation

    org_id=j
    dynamodb=boto3.resource('dynamodb')
    table=dynamodb.Table('employees')
    departments_table=dynamodb.Table('departments')

    dep_response=departments_table.scan()
    response2=table.scan()
    #Getting departments from departments table
    dep=[]

    name=[]
    department=[]
    hierarchy=[]
    no_complaints=[]
    emp_id=[]

    for de in dep_response['Items']:
        if(de['organization_id']==org_id):
            dep.append(de['department_name'])

    for dic in response2['Items']:
        if dic['active']==True and dic['org_id']==int(org_id):
            name.append(dic['emp_name'])
            department.append(dic['department'])
            hierarchy.append(dic['hierarchy'])
            no_complaints.append(dic['no_complaints'])
            emp_id.append(dic['emp_id'])

    info_list=zip(name,department,hierarchy,no_complaints,emp_id)

    context={
        'info_list':info_list,
        'org_id':org_id,
        'dep':dep,
        'present':present
    }

    if request.method=='POST':
        name=request.POST.get('emp_name')
        department=request.POST.get('department')
        hierarchy=request.POST.get('hierarchy')
        no_comp=request.POST.get('no_complaints')
        email=request.POST.get('emp_email')

        print(department)

        dynamodb=boto3.resource('dynamodb')
        table=dynamodb.Table('employees')
        email_present_table=dynamodb.Table('users')

        #Checking if user is already registered user or not
        email_present=email_present_table.scan(
            ProjectionExpression="email",
        )

        check=0
        for em in email_present['Items']:
            if(em['email']==email):
                check=1
        #End of user checking

        #Incrementing the primary key
        response = table.scan(
                    ProjectionExpression="emp_id",
                )

        #Checking if person with entered email already present in organisation or not
        for dic in response2['Items']:
            if(dic['user_email']==email) and (dic['org_id']==org_id):
                present=1
                context['present']=present
                return render(request, 'dashboard/index.html',context)

        emp_id=len(response['Items'])+1

        #Randomly generating password
        letters=string.ascii_letters
        password_gen=''.join(random.choice(letters) for i in range(8))

        token=''.join(random.choice(letters) for i in range(10))

        #Checking if the user admin entered is regestered user or a new user
        #Below if new user is added
        if (check==0):

            table.put_item(
            Item={
                'org_id':org_id,
                'emp_id':len(response['Items'])+1,
                'emp_name':name,
                'user_email':email,
                'department':department,
                'hierarchy':hierarchy,
                'no_complaints':no_comp,
                'active':False,
                'token':token
             }
            )

            current_site = get_current_site(request)
            mail_subject = 'Click the link to join the organisation.'
            message = render_to_string('dashboard/acc_active_email.html', {
                'user': name,
                'user_id':emp_id,
                'user_email':email,
                'password':password_gen,
                'domain': current_site.domain,
                'uid':urlsafe_base64_encode(force_bytes(emp_id)),
                'token':token,
                'org_id':org_id
            })
            to_email = email
            email = EmailMessage(
                        mail_subject, message, to=[to_email]
            )
            email.send()

            return render(request, 'dashboard/index.html',context)



        #If user already registered is in added to organisation
        elif(check==1):
            table.put_item(
            Item={
                'org_id':org_id,
                'emp_id':len(response['Items'])+1,
                'emp_name':name,
                'user_email':email,
                'department':department,
                'hierarchy':hierarchy,
                'no_complaints':no_comp,
                'active':True,
                'token':token
             }
            )

            current_site = get_current_site(request)
            mail_subject = 'Joined organisation login with your old credentials.'
            message = render_to_string('dashboard/old_credentials_email.html', {
                'user': name,
                'user_id':emp_id,
                'user_email':email,
                'password':password_gen,
                'domain': current_site.domain,
                'uid':urlsafe_base64_encode(force_bytes(emp_id)),
                'token':token,
                'org_id':org_id
            })
            to_email = email
            email = EmailMessage(
                        mail_subject, message, to=[to_email]
            )
            email.send()

            #Database call for getting updated table(After registered user is added)
            table2=dynamodb.Table('employees')
            user_table=dynamodb.Table('users')

            user_response=user_table.scan()
            response3=table2.scan()

            for user in user_response['Items']:
                if(user['email']==email):
                    org_joined=user['organizations_joined']
                    org_joined.append(org_id)

                    user_table.update_item(
                        Key={
                            'user_email':dic['user_email']
                        },
                        UpdateExpression="set organizations_joined = :r",
                        ExpressionAttributeValues={
                        ':r':org_joined
                        }
                    )


            name=[]
            department=[]
            hierarchy=[]
            no_complaints=[]
            emp_id=[]

            for dic in response3['Items']:
                if dic['active']==True and dic['org_id']==int(org_id):
                    name.append(dic['emp_name'])
                    department.append(dic['department'])
                    hierarchy.append(dic['hierarchy'])
                    no_complaints.append(dic['no_complaints'])
                    emp_id.append(dic['emp_id'])

            info_list=zip(name,department,hierarchy,no_complaints,emp_id)
            print(name)

            context={
                'info_list':info_list,
                'org_id':org_id,
                'dep':dep,
                'present':present
            }

            return render(request, 'dashboard/index.html',context)

    return render(request, 'dashboard/index.html',context)



def activate(request, uidb64, token, user_id, password,org_id):
    dynamodb=boto3.resource('dynamodb')
    table=dynamodb.Table('employees')
    users_table=dynamodb.Table('users')

    response=table.scan()

    #Checking for activation True is in Employee table

    for dic in response['Items']:
        if (dic['emp_id']==int(user_id)) and (dic['token']==str(token)) and (dic['org_id']==int(org_id)):
            table.update_item(
                Key={
                    'emp_id':dic['emp_id']
                },
                UpdateExpression="set active = :r",
                ExpressionAttributeValues={
                    ':r':True
                }
            )

            password=hashlib.shaw256(password.encode())
            password=password.hexdigest()
            
            users_table.put_item(
            Item={
                'username':dic['emp_name'],
                'email':dic['user_email'],
                'password':password,
                'organizations_created':[],
                'organizations_joined':[org_id],
                'active':True
                }
            )


    return redirect('../../../../../../../')


def delete_employee(request,org_id,emp_id):
    dynamodb=boto3.resource('dynamodb')
    emp_table=dynamodb.Table('employees')

    response=emp_table.scan()

    for emp in response['Items']:
        if(emp['emp_id']==emp_id) and (emp['org_id']==org_id):
            url="../../dashboard/"+str(org_id)
            return redirect(url)

#------------------------------------------------------------------------------------------------------------#
#------------------------------------------------------------------------------------------------------------#
#------------------------------------------------------------------------------------------------------------#

def create(request):
    email=request.session['email']

    dynamoDB=boto3.resource('dynamodb')
    dynamoTable=dynamoDB.Table('users')

    response = dynamoTable.scan(
        ProjectionExpression="organizations_created,organizations_joined",
        FilterExpression=Attr('email').eq(email)
    )

    # print(response)
    # print('\n**\n')

    organizations_created=response['Items'][0]['organizations_created']
    total_org_ids=copy.deepcopy(organizations_created)
    organizations_joined=response['Items'][0]['organizations_joined']
    for i in organizations_joined:
        total_org_ids.append(i)
        # topics=[]
        # print(codes)
        # dynamoTable=dynamoDB.Table('topics')
        # for index in range(0,len(codes)):
        #     response=dynamoTable.get_item(
        #     Key={
        #     'code':codes[index],
        #     }
        #     )
        #     print(response['Item']['topic'])
        #     topics+=[response['Item']['topic']]
        # print(topics)
    # print(total_org_ids)
    for i in range(0,len(response['Items'][0]['organizations_joined'])):
        response['Items'][0]['organizations_joined'][i] = int(response['Items'][0]['organizations_joined'][i])
    org_join_id=response['Items'][0]['organizations_joined']


    org_names=[]
    dynamoTable=dynamoDB.Table('organization')
    for i in total_org_ids:
        # print(type(int(i)))
        response = dynamoTable.scan(
            ProjectionExpression="organization_name",
            FilterExpression=Attr('org_id').eq(int(i))
        )
        # print(response['Items'])
        org_names.append(response['Items'][0]['organization_name'])
    # print(email)
    # print(org_names)
    organizations_created_names=[]
    organizations_joined_names=[]
    count=0
    for i in org_names:
        if(count>=len(organizations_created)):
            organizations_joined_names.append(i)
        else:
            organizations_created_names.append(i)
        count=count+1
    # print(organizations_joined_names)
    # print(organizations_created_names)


    # dynamoDB=boto3.resource('dynamodb')
    # dynamoTable=dynamoDB.Table('topics')
    # response=dynamoTable.scan(
    # )
    # # print(response)
    # # print("\n\n\n\n")
    # # print(response['Items'])
    # topics_created=[]
    # codes_created=[]
    # for index in response['Items']:
    #     # print(index['name'])
    #     # print(request.user.username)
    #     if(index['name']==request.user.username):
    #         topics_created+=[index['topic']]
    #         codes_created+=[index['code']]
    #
    # print(codes_created)
    # print(organizations_created)
    # print("######################")
    ids=str(organizations_created)
    print(ids)
    list1=[]
    list1.append(ids.split("'"))
    # print(list1[0][3])
    list2=[]
    # print(len(list1[0]))
    for i in range(0,len(list1[0])):
        if i%2 != 0:
            list2.append(int(list1[0][i]))
    # print(type(list2[0]))
    # print(org_join_id)
    # print("****************")
    #print(ids.split("'"))
    # for i in range ids.split("'"):
    #     list1.append
    extra = (len(organizations_created)%4)-1
    data = {'topics' : zip(organizations_created_names,list2), 'topics_created' : zip(organizations_joined_names,org_join_id), 'topics_size' : len(organizations_created), 'topics_created_size' : len(organizations_joined), 'extra_grid' : extra,}



    return render(request, 'orgadmin/dummy.html', data)


def created(request):
    organization_name = request.POST.get('name')
    code=request.POST.get('code')
    #print("name:"+ organization_name + "code:" + code)

    if (organization_name!='' and code!='' ):
            dynamodb = boto3.resource('dynamodb')
            table = dynamodb.Table('organization')
            response_sno=table.scan(
                ProjectionExpression="org_id",
             )
            response = table.scan(
                ProjectionExpression="organization_name,code",
                FilterExpression=Attr('organization_name').eq(organization_name) | Attr('code').eq(code)
            )

            if(len(response['Items'])==0):
                ID=len(response_sno['Items'])+101
                response = table.put_item(
                   Item={
                    'org_id': len(response_sno['Items'])+101,
                    'organization_name': organization_name,
                    'code':code,
                    }
                )
                email=request.session['email']
                # print(response_sno)
                # print("####################")

                # sno=response_sno['Items'][0]['org_id']
                # print(sno)
                request.session['org_created']=request.session['org_created']+[ID]
                org_created = request.session['org_created']
                # print(org_created)
                # print(ID)
                # print(request.session['org_created'])
                # print('\n\n\n')
                # # request.session['org_created'].append(ID)
                org_joined = request.session['org_joined']

                dynamoDB=boto3.resource('dynamodb')
                table=dynamoDB.Table('users')
                # print("\n\n\n")
                # print(org_created)
                # print("\n\n\n")
                # print(request.session['org_created'])
                response = table.update_item(
                    Key={
                        'email':email
                    },
                    UpdateExpression="set organizations_created = :r",
                    ExpressionAttributeValues={
                        ':r': org_created,

                    },
                    ReturnValues="UPDATED_NEW"
                )


                response1 = table.scan(
                    ProjectionExpression="organizations_created,organizations_joined",
                    FilterExpression=Attr('email').eq(email)
                )


                #print(response1)
                #print('\n**\n')

                organizations_created=response1['Items'][0]['organizations_created']
                organizations_joined=response1['Items'][0]['organizations_joined']
                # print(organizations_created)
                # print(organizations_joined)
                total_org_ids=copy.deepcopy(organizations_created)
                for i in organizations_joined:
                    total_org_ids.append(i)
                for i in range(0,len(response1['Items'][0]['organizations_joined'])):
                    response1['Items'][0]['organizations_joined'][i] = int(response1['Items'][0]['organizations_joined'][i])
                    org_join_id=response1['Items'][0]['organizations_joined']


                org_names=[]
                dynamoTable=dynamoDB.Table('organization')
                for i in total_org_ids:
                    #print(type(int(i)))
                    response1 = dynamoTable.scan(
                        ProjectionExpression="organization_name",
                        FilterExpression=Attr('org_id').eq(int(i))
                    )
                    org_names.append(response1['Items'][0]['organization_name'])
                    #print(org_names)
                    organizations_created_names=[]
                    organizations_joined_names=[]
                    count=0
                    for i in org_names:
                        if(count>=len(organizations_created)):
                            organizations_joined_names.append(i)
                        else:
                            organizations_created_names.append(i)
                        count=count+1
                # print('a')
                # print(organizations_joined_names)
                # print('b')
                # print(organizations_created_names)
                # print('c')
                # print(organizations_created)
                # print('d')
                # print(organizations_joined)



                extra = (len(organizations_created)%4)-1
                data = {'topics' : zip(organizations_created_names,organizations_created), 'topics_created' : zip(organizations_joined_names,organizations_joined), 'topics_size' : len(organizations_created), 'topics_created_size' : len(organizations_joined), 'extra_grid' : extra,}
                # print(request.session['org_created'])
                return render(request, 'orgadmin/dummy.html', data)



            else:
                # print(request.session['org_created'])
                #print('abc')
                #print(request.session['email'])
                email=request.session['email']

                dynamoDB=boto3.resource('dynamodb')
                dynamoTable=dynamoDB.Table('users')


                response = dynamoTable.scan(
                    ProjectionExpression="organizations_created,organizations_joined",
                    FilterExpression=Attr('email').eq(email)
                )

                # print(response)
                # print('\n**\n')

                organizations_created=response['Items'][0]['organizations_created']
                total_org_ids=copy.deepcopy(organizations_created)
                organizations_joined=response['Items'][0]['organizations_joined']
                for i in organizations_joined:
                    total_org_ids.append(i)

                # print(total_org_ids)
                for i in range(0,len(response['Items'][0]['organizations_joined'])):
                    response['Items'][0]['organizations_joined'][i] = int(response['Items'][0]['organizations_joined'][i])
                org_join_id=response['Items'][0]['organizations_joined']


                org_names=[]
                dynamoTable=dynamoDB.Table('organization')
                for i in total_org_ids:
                    print(type(int(i)))
                    response = dynamoTable.scan(
                        ProjectionExpression="organization_name",
                        FilterExpression=Attr('org_id').eq(int(i))
                    )
                    print(response['Items'])
                    org_names.append(response['Items'][0]['organization_name'])

                organizations_created_names=[]
                organizations_joined_names=[]
                count=0
                for i in org_names:
                    if(count>=len(organizations_created)):
                        organizations_joined_names.append(i)
                    else:
                        organizations_created_names.append(i)
                    count=count+1
                #print(organizations_joined_names)
                #print(organizations_created_names)

                extra = (len(organizations_created)%4)-1
                data = {'topics' : zip(organizations_created_names,organizations_created), 'topics_created' : zip(organizations_joined_names,org_join_id), 'topics_size' : len(organizations_created), 'topics_created_size' : len(organizations_joined), 'extra_grid' : extra,}
                # print('a')
                # print(organizations_joined_names)
                # print('b')
                # print(organizations_created_names)
                # print('c')
                # print(organizations_created)
                # print('d')
                # print(organizations_joined)




                return render(request, 'orgadmin/dummy.html', data)


def join(request):
    code=request.POST.get('join_code')
    #print("code:" + code)

    if (code!='' ):
            dynamodb = boto3.resource('dynamodb')
            table = dynamodb.Table('organization')


            response_join = table.scan(
                ProjectionExpression="code,org_id",
                FilterExpression=Attr('code').eq(code)
            )
            print("********************")
            print(response_join)
            print("#####################")

            #request.session['org_created']=request.session['org_created']+[ID]
            org_joined = request.session['org_joined']
            print(org_joined)
            print(response_join['Items'][0]['org_id'])
            if (response_join['Items'][0]['org_id'] not in org_joined):
                org_joined.append(int(response_join['Items'][0]['org_id']))
                print(org_joined)
                print("@@@@")
            email=request.session['email']
            print(org_joined)
            print(email)

            dynamoDB=boto3.resource('dynamodb')
            table=dynamoDB.Table('users')
            response_joined = table.update_item(
                Key={
                    'email':email
                },
                UpdateExpression="set organizations_joined = :r",
                ExpressionAttributeValues={
                    ':r': org_joined,

                },
                ReturnValues="UPDATED_NEW"
            )
            return redirect('../create')
















def createform(request):
    return render(request,'orgadmin/createform.html')


def departments(request):

    organization_id = 105
    request.session['org_id'] = organization_id
    dynamoDB=boto3.resource('dynamodb')
    dynamoTable=dynamoDB.Table('departments')

    response = dynamoTable.scan(
        ProjectionExpression="department_name,department_id",
        FilterExpression=Attr('organization_id').eq(organization_id)
    )
    departments = []
    dep_id=[]
    if(len(response['Items'])==0):
        departments=[]
        dep_id=[]
    else:
        for i in response['Items']:
            departments.append(i['department_name'])
            dep_id.append(i['department_id'])
        print(departments)

    return render(request,'orgadmin/org_departments.html',{'dep':zip(departments,dep_id),'topics_size':len(departments),'uname':request.session['username']})


def hierarchy(request):
    res = request.POST.get('dep')
    print(res)
    data=res.split('_')
    dep_id=data[0]
    dep_name=data[1]
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('hierarchy')
    response = table.scan(
        ProjectionExpression="hierarchy",
        FilterExpression=Attr('dep_id').eq(int(dep_id))
    )

    if(len(response['Items'])==0):
        node=[{"id":1,"hierarchy":dep_name}]

    else:
        node = response['Items'][0]['hierarchy']
    # node='[{"id":1,"hierarchy":"a"},{"id":2,"pid":1,"hierarchy":"b"},{"id":3,"pid":1,"hierarchy":"c"},{"id":4,"pid":3,"hierarchy":"d"}]'
    # print(type(node))
    return render(request,'orgadmin/depart.html',{'node':node,'dep_name':dep_name,'dep_id':dep_id})


# @requires_csrf_token
def departments_hierarchy_update(request):
    # print(type(hierarchy))
    # print(hierarchy)
    # nodes = request.POST['tasks']
    print(request.POST)
    data = request.POST
    print('\n')
    print(data)
    print('\n')
    print(data['tasks'])
    print('\n')
    print(data['dep_id'])
    id=int(data['dep_id'])
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('hierarchy')
    response = table.scan(
        ProjectionExpression="dep_id",
        FilterExpression=Attr('dep_id').eq(id)
    )

    if(len(response['Items'])==0):
        response = table.put_item(
           Item={
            'dep_id': int(data['dep_id']),
            'hierarchy': data['tasks']
            }
        )
    else:
        response = table.update_item(
            Key={
                'dep_id':id
            },
            UpdateExpression="set hierarchy = :r",
            ExpressionAttributeValues={
                ':r': data['tasks'],

            },
            ReturnValues="UPDATED_NEW"
        )



    # print(request.POST['nodes'])
    # value = parse.parse_qs(request.POST.get('hierarchy'))
    # organization_id = 105
    # dynamoDB=boto3.resource('dynamodb')
    # dynamoTable=dynamoDB.Table('departments')
    #
    # response = dynamoTable.scan(
    #     ProjectionExpression="department_name,department_id",
    #     FilterExpression=Attr('organization_id').eq(organization_id)
    # )
    # departments = []
    # dep_id=[]
    # for i in response['Items']:
    #     departments.append(i['department_name'])
    #     dep_id.append(i['department_id'])
    # print(departments)


    # return render(request,'orgadmin/org_departments.html',{'dep':zip(departments,dep_id)})
    return redirect('../departments')


def orgadmin_page(request):
    email=request.session['email']

    dynamoDB=boto3.resource('dynamodb')
    dynamoTable=dynamoDB.Table('users')

    response = dynamoTable.scan(
        ProjectionExpression="organizations_created,organizations_joined",
        FilterExpression=Attr('email').eq(email)
    )



    organizations_created=response['Items'][0]['organizations_created']
    total_org_ids=copy.deepcopy(organizations_created)
    organizations_joined=response['Items'][0]['organizations_joined']
    for i in organizations_joined:
        total_org_ids.append(i)

    for i in range(0,len(response['Items'][0]['organizations_joined'])):
        response['Items'][0]['organizations_joined'][i] = int(response['Items'][0]['organizations_joined'][i])
    org_join_id=response['Items'][0]['organizations_joined']


    org_names=[]
    dynamoTable=dynamoDB.Table('organization')
    for i in total_org_ids:
        # print(type(int(i)))
        response = dynamoTable.scan(
            ProjectionExpression="organization_name",
            FilterExpression=Attr('org_id').eq(int(i))
        )
        # print(response['Items'])
        org_names.append(response['Items'][0]['organization_name'])

    organizations_created_names=[]
    organizations_joined_names=[]
    count=0
    for i in org_names:
        if(count>=len(organizations_created)):
            organizations_joined_names.append(i)
        else:
            organizations_created_names.append(i)
        count=count+1
    extra = (len(organizations_created)%4)-1
    data = {'topics' : zip(organizations_created_names,organizations_created), 'topics_created' : zip(organizations_joined_names,org_join_id), 'topics_size' : len(organizations_created), 'topics_created_size' : len(organizations_joined), 'extra_grid' : extra,}



    return render(request, 'orgadmin/dummy.html', data)


def index(request):
    response_rest=json.dumps([{}])
    return HttpResponse(response_rest,content_type='text/json')

def complaint_rest(request):
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('complaint')
        response_complaint = table.scan(
        ProjectionExpression="complaint",

        )

        complaint_list=[]
        # print(response_complaint['Items'][0])
        for i in range(0,len(response_complaint['Items'])):
            complaint_list.append(response_complaint['Items'][i]['complaint'])

        print(complaint_list)
        # print(len(complaint_list))

        if request.method=='GET':
            try:
                complaint=complaint_list
                response_rest=json.dumps([{'complaint':complaint}])
            except:
                print("something went wrong")

        return render(request, 'orgadmin/createform.html')
def create_department(request):
    depname = request.POST.get('depname')
    print(depname)
    dynamoDB=boto3.resource('dynamodb')
    dynamoTable=dynamoDB.Table('departments')
    print(type(request.session['org_id']))
    x=request.session['org_id']
    response1 = dynamoTable.scan(ProjectionExpression="department_id")
    response = dynamoTable.scan(
        ProjectionExpression="department_name",
        FilterExpression=Attr('organization_id').eq(int(x)) & Attr('department_name').eq(depname)
    )
    print(response1['Items'])
    lengt=0
    for i in response1['Items']:
        if lengt< int(i['department_id']):
            lengt = int(i['department_id'])
        else:
            continue

    print(lengt)
    if(len(response['Items'])==0):
        response = dynamoTable.put_item(
           Item={
            'department_id':lengt+1,
            'department_name':depname,
            'organization_id':x
            }
        )
        messages.success(request, 'The new department has been created successfully.')
    else:
        messages.success(request, 'Please check again as a department with the same name is already created for your organization.')
    return redirect('../departments')
