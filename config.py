from pymongo import MongoClient


WTF_CSRF_ENABLED = True
SECRET_KEY = 'QW$%JKNVJK0967JJGKJK1JOO7'
AUTH_SECRET_KEY = 'HVUI$I%I897V8VG9IJ89Q1'

DB_NAME = 'hydroid'

DATABASE = MongoClient()[DB_NAME]
USERS_COLLECTION = DATABASE.users
DEBUG = True
