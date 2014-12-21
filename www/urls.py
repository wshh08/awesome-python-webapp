#!/usr/bin/env python
# -*- coding: utf-8 -*-

from transwarp.web import get, view
from models import User, Blog


@view('blogs.html')
@get('/')
def index():
    blogs = Blog.find_all()
    user = User.find_first('where email=?', 'test@putixu.com')
    return dict(blogs=blogs, user=user)
