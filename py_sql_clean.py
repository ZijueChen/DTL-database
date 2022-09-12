#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import psycopg2
import datetime
import cv2
import urllib
import numpy as np
from database import CursorFromConnectionPool
from database import Database

connection = psycopg2.connect(database='Developer', user='postgres', password='4321', host='localhost')
cursor=connection.cursor()
Database.initialise(database="Developer", user="postgres", password="4321", host="localhost")

class Print:
    def __init__(self, status, assigned_printerid, initiate_time, start_time, finish_time, cooldown_time, pickup_time, cleanup_time, snapshot_path, filamentid, used_filament):
        self.status = status
        self.assigned_printerid = assigned_printerid
        self.start_time = start_time
        self.initiate_time = initiate_time
        self.finish_time = finish_time
        self.cooldown_time = cooldown_time
        self.pickup_time = pickup_time
        self.cleanup_time = cleanup_time
        self.snapshot_path = snapshot_path
        self.filamentid = filamentid
        self.used_filament = used_filament
    
#     def save_to_db(self):
#         with CursorFromConnectionPool() as cursor:
#             cursor.execute('INSERT INTO printing (status, assigned_printerid, start_time, finish_time, filamentid, used_filament) VALUES (%s, %s, %s, %s, %s, %s)',
#                             (self.status, self.assigned_printerid, self.start_time, self.finish_time, self.filamentid, self.used_filament))
    @classmethod
    def load_from_db_by_part(cls, partid):
        with CursorFromConnectionPool() as cursor:
            cursor.execute('SELECT * FROM printing WHERE partid=%s', (partid,))
            print_data = cursor.fetchone()
            return cls(status=print_data[1], assigned_printerid=print_data[2], initiate_time=print_data[3], 
                       start_time=print_data[4], finish_time=print_data[5], cooldown_time=print_data[6],
                       pickup_time=print_data[7], cleanup_time=print_data[8], snapshot_path=print_data[9],
                       filamentid=print_data[10], used_filament=print_data[11],)
    
    @classmethod
    # get current print job on printerX. either waiting or printing. Each printer can have only one job at a time
    def get_current_partid_by_printer(cls, printerid):
        with CursorFromConnectionPool() as cursor:
            cursor.execute('SELECT partid FROM printing WHERE assigned_printerid=%s AND (status=%s OR status=%s\
             OR status=%s OR status=%s)', (printerid, 'waiting','printing', 'cooling', 'onbed',))
            return cursor.fetchone()[0]
    @classmethod
    # operational --> heating
    def initiate_part_to_printerid(cls, printerid): 
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with CursorFromConnectionPool() as cursor:
            cursor.execute('INSERT INTO printing (status, assigned_printerid, initiate_time) VALUES (%s, %s, %s)',
                            ('waiting', printerid, now,))
    @classmethod
    # heating --> printing
    def print_part_by_printer(cls, printerid):
        partid = Print.get_current_partid_by_printer(printerid)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with CursorFromConnectionPool() as cursor:
            cursor.execute('UPDATE printing SET start_time=%s WHERE partid=%s;', (now, partid,))
            cursor.execute('UPDATE printing SET status=%s WHERE partid=%s;', ('printing', partid,))
    @classmethod
    # printing --> cooldown
    # cancelling --> cooldown
    def cooldown_print_by_printer(cls, printerid):
        partid = Print.get_current_partid_by_printer(printerid)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with CursorFromConnectionPool() as cursor:
            cursor.execute('UPDATE printing SET finish_time=%s WHERE partid=%s;', (now, partid,))
            cursor.execute('UPDATE printing SET status=%s WHERE partid=%s;', ('cooling', partid,))
    @classmethod
    # printing cancelled from partonbed --> cleanup
    def pickup_cancel_print_by_printer(cls, printerid):
        partid = Print.get_current_partid_by_printer(printerid)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with CursorFromConnectionPool() as cursor:
            cursor.execute('UPDATE printing SET pickup_time=%s WHERE partid=%s;', (now, partid,))
            cursor.execute('UPDATE printing SET status=%s WHERE partid=%s;', ('cancelled', partid,))
    @classmethod
    # printing finished from partonbed --> cleanup
    def pickup_finish_print_by_printer(cls, printerid):
        partid = Print.get_current_partid_by_printer(printerid)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with CursorFromConnectionPool() as cursor:
            cursor.execute('UPDATE printing SET pickup_time=%s WHERE partid=%s;', (now, partid,))
            cursor.execute('UPDATE printing SET status=%s WHERE partid=%s;', ('finished', partid,))
    @classmethod
    # cleaning --> operational
    def cleanedup_by_printer(cls, printerid):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with CursorFromConnectionPool() as cursor:
            cursor.execute('SELECT partid FROM printing WHERE assigned_printerid=%s AND cleanup_time IS NULL ORDER BY pickup_time DESC;', (printerid,))
            partid = cursor.fetchone()[0]
            cursor.execute('UPDATE printing SET cleanup_time=%s WHERE partid=%s;', (now, partid,))
    @classmethod
    def snapshot_by_printer(cls, printerid):
        partid = Print.get_current_partid_by_printer(printerid)
        req = urllib.request.urlopen("http://octopi"+str(printerid)+":8080/?action=snapshot")
        arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
        img = cv2.imdecode(arr, -1)
        return img
    @classmethod
    # cooldown --> partonbed
    # save a snapshot and also save path to SQL database
    def onbed_by_printer(cls, printerid):
        partid = Print.get_current_partid_by_printer(printerid)
        now = datetime.datetime.now()
        img = Print.snapshot_by_printer(printerid)
        path = 'snapshots/Printer'+str(printerid)+'_'+str(now.strftime("%Y-%m-%d_%H-%M-%S"))+'.png'
        cv2.imwrite(path, img)
        with CursorFromConnectionPool() as cursor:
            cursor.execute('UPDATE printing SET cooldown_time=%s WHERE partid=%s;', (now.strftime("%Y-%m-%d %H:%M:%S"), partid,))
            cursor.execute('UPDATE printing SET status=%s WHERE partid=%s;', ('onbed', partid,))
            cursor.execute('UPDATE printing SET snapshot_path=%s WHERE partid=%s;', (path, partid,))

