#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Wang Shaohua'

from models import User
from transwarp import db


db.create_engine(user='wshh08', password='2910', database='awesome')


u = User(name='Test', email='test@putixu.com', password='1234567890', image='about:blank')


u.insert()


print 'new user id:', u.id


u1 = User.find_first('where email=?', 'test@putixu.com')
print 'find user\'s name:', u1.name


# u1.delete()


u2 = User.find_first('where email=?', 'test@putixu.com')
print 'find user:', u2
