#!/usr/bin/env python
# -*- coding: utf-8 -*-

from transwarp.web import get, view, post
from models import User, Blog
from apis import api, Page, APIError, APIValueError
from transwarp.web import ctx, interceptor
import re
import time
import hashlib
import logging
from config import configs

_COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secrect
_RE_MD5 = re.compile(r'^[0-9a-f]{32}$')
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')


def _get_page_index():
    page_index = 1
    try:
        page_index = int(ctx.request.get('page', '1'))
    except ValueError:
        pass
    return page_index


def _get_blogs_by_page():
    total = Blog.count_all()
    page = Page(total, _get_page_index())
    blogs = Blog.find_by('order by created_at desc limit ?,?', page.offset, page.limit)
    return blogs, page


def make_signed_cookie(id, password, max_age):
    expires = str(int(time.time() + max_age or 86400))
    L = [id, expires, hashlib.md5('%s-%s-%s-%s' % (id, password, expires, _COOKIE_KEY)).hexdigest()]
    return '-'.join(L)


def parse_signed_cookie(cookie_str):
    try:
        L = cookie_str.split('-')
        # print ('cookie_str: %s' % cookie_str)
        # print ('L splited from cookie_str is %s' % L)
        if len(L) != 3:
            return None
        id, expires, md5 = L
        if int(expires) < time.time():
            return None
        user = User.get(id)
        if user is None:
            return None
        if md5 != hashlib.md5('%s-%s-%s-%s' % (id, user.password, expires, _COOKIE_KEY)).hexdigest():
            return None
        return user
    except:
        return None


@interceptor('/')
def user_interceptor(next):
    logging.info('try to bind user from session cookie...')
    user = None
    cookie = ctx.request.cookies.get(_COOKIE_NAME)
    # print ("cookies from ctx.request.cookies is %s" % ctx.request.cookies)
    # print ("cookie from browser is %s" % cookie)
    if cookie:
        logging.info('parse session cookie...')
        user = parse_signed_cookie(cookie)
        # print ("user from cookie is %s" % user)
        if user:
            logging.info('bind user <%s> to session...' % user.email)
    ctx.request.user = user
    return next()


@view('blogs.html')
@get('/')
def index():
    blogs, page = _get_blogs_by_page()
    # print ctx.request
    return dict(page=page, blogs=blogs, user=ctx.request.user)


@view('register.html')
@get('/register')
def register():
    return dict()


@view('signin.html')
@get('/signin')
def signin():
    return dict()


@api
@get('/api/users')
def api_get_users():
    users = User.find_by('order by created_at desc')
    # hide the password
    for u in users:
        u.password = '******'
    return dict(users=users)


@api
@post('/api/users')
def register_users():
    i = ctx.request.input(name='', email='', password='')
    name = i.name.strip()
    email = i.email.strip().lower()
    password = i.password
    if not name:
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
#    if not password or not _RE_MD5.match('password'):  多了个引号，你个都比。。。。
    if not password or not _RE_MD5.match(password):
        # print _RE_MD5.match('password')
        raise APIValueError('password', 'Password Wrong')
    user = User.find_first('where email=?', email)
    if user:
        raise APIError('register:failed', 'email', 'Email is already in use.')
    user = User(name=name, email=email, password=password, image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email).hexdigest())
    user.insert()
    return user


@api
@post('/api/authenticate')
def authenticate():
    i = ctx.request.input()
    email = i.email.strip().lower()
    password = i.password
    user = User.find_first('where email=?', email)
    if user is None:
        raise APIError('auth:failed', 'email', 'Invalid email.')
    elif user.password != password:
        raise APIError('auth:faild', 'password', 'Invalid password.')
    max_age = 604800
    cookie = make_signed_cookie(user.id, user.password, max_age)
    # print ("make signed cookie: %s" % cookie)
    ctx.response.set_cookie(_COOKIE_NAME, cookie, max_age=max_age)
    user.password = '******'
    return user


@api
@post('/api/blogs')
def api_create_blog():
    i = ctx.request.input(name='', summary='', content='')
    name = i.name.strip()
    summary = i.summary.strip()
    content = i.content.strip()
    if not name:
        raise APIValueError('name', 'name cannot be empty.')
    if not summary:
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content:
        raise APIValueError('content', 'content cannot be empty.')
    user = ctx.request.user
    blog = Blog(user_id=user.id, user_name=user.name, name=name, summary=summary, content=content)
    blog.insert()
    return blog


@view('manage_blog_edit.html')
@get('/manage/blogs/create')
def manage_blogs():
    return dict(id=None, action='/api/blogs', redirect='/manage/blogs', user=ctx.request.user)


@view('test_users.html')
@get('/test/users')
def test_users():
    users = User.find_by('order by created_at desc')
    # hide the password
    for u in users:
        u.password = '******'
    return dict(users=users)
