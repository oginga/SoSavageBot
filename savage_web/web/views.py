from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse,JsonResponse,HttpResponseRedirect,HttpResponseForbidden
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

import redis
# TODO: django-redis

#-------------INIT--------------
conn = redis.Redis(decode_responses=True)
pipeline=conn.pipeline()

# Create your views here.
def login_user(request):
    if request.POST:
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)
       
        if user is not None:
        	if user.is_active:
        		return HttpResponseRedirect('/dashboard')
    return HttpResponseRedirect('/login')


@login_required(login_url='/login')
def dashboard(request,mentionid=None):
    # Get data 
    mention_ids=conn.zrange('sav:mentions', 0, -1, withscores=True) #List of tuples
    context={'mentions':[]}

    if mentionid:
        print(f"GET RECEIVED {request.GET}")
        reply_author_id=conn.hget(f'sav:mentions:{mentionid}','reply_author_id')
        conn.hset(f'sav:mentions:{mentionid}','status',1)
        # Increase approved reply author's score
        conn.zincrby(f"sav:authors:scores",reply_author_id,1)

        messages.success(request,('Tweet reply approved successfully'))
        return HttpResponseRedirect('/dashboard')

    for m_id,m_score in mention_ids:
        print(f"mid sav:mentions:{m_id}")
        mention=conn.hgetall(f'sav:mentions:{m_id}')
        print(f"mention: {mention}")
        mention['id']=m_id
        context['mentions'].append(mention)

    print(context)

    template='dashboard.html'
    return render(request,template,context)

