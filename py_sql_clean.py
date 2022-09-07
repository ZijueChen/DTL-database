import psycopg2
import datetime
from database import CursorFromConnectionPool
from database import Database

connection = psycopg2.connect(database='Developer', user='postgres', password='4321', host='localhost')
cursor=connection.cursor()
Database.initialise(database="Developer", user="postgres", password="4321", host="localhost")

class Print:
    def __init__(self, status, assigned_printerid, start_time, finish_time, filamentid, used_filament):
        self.status = status
        self.assigned_printerid = assigned_printerid
        self.start_time = start_time
        self.finish_time = finish_time
        self.filamentid = filamentid
        self.used_filament = used_filament
    
    def save_to_db(self):
        with CursorFromConnectionPool() as cursor:
            cursor.execute('INSERT INTO printing (status, assigned_printerid, start_time, finish_time, filamentid, used_filament) VALUES (%s, %s, %s, %s, %s, %s)',
                            (self.status, self.assigned_printerid, self.start_time, self.finish_time, self.filamentid, self.used_filament))
    @classmethod
    def load_from_db_by_part(cls, partid):
        with CursorFromConnectionPool() as cursor:
            cursor.execute('SELECT * FROM printing WHERE partid=%s', (partid,))
            print_data = cursor.fetchone()
            return cls(status=print_data[1], assigned_printerid=print_data[2], start_time=print_data[3], 
                       finish_time=print_data[4], filamentid=print_data[5], used_filament=print_data[6])
    @classmethod
    # when status change from operational --> heating
    def assign_part_to_printerid(cls, printerid, status='waiting'): 
        with CursorFromConnectionPool() as cursor:
            cursor.execute('INSERT INTO printing (status, assigned_printerid, start_time, finish_time, filamentid, used_filament) VALUES (%s, %s, %s, %s, %s, %s)',
                            (status, printerid, None, None, None, None))
    @classmethod
    # get current print job on printerX. either waiting or printing. Each printer can have only one job at a time
    def get_current_partid_by_printer(cls, printerid):
        with CursorFromConnectionPool() as cursor:
            # Note the (email,) to make it a tuple!
            cursor.execute('SELECT partid FROM printing WHERE assigned_printerid=%s AND (status=%s OR status=%s)', (printerid, 'waiting','printing',))
            return cursor.fetchone()[0]
    @classmethod
    # when status change from heating --> printing
    def start_print_by_printer(cls, printerid):
        partid = Print.get_current_partid_by_printer(printerid)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with CursorFromConnectionPool() as cursor:
            cursor.execute('UPDATE printing SET start_time=%s WHERE partid=%s;', (now, partid,))
            cursor.execute('UPDATE printing SET status=%s WHERE partid=%s;', ('printing', partid,))
    @classmethod
    # when status change from printing --> cancelling
    def cancel_print_by_printer(cls, printerid):
        partid = Print.get_current_partid_by_printer(printerid)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with CursorFromConnectionPool() as cursor:
            cursor.execute('UPDATE printing SET finish_time=%s WHERE partid=%s;', (now, partid,))
            cursor.execute('UPDATE printing SET status=%s WHERE partid=%s;', ('cancelled', partid,))
    @classmethod
    # when status change from printing --> cooldown
    def finish_print_by_printer(cls, printerid):
        partid = Print.get_current_partid_by_printer(printerid)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with CursorFromConnectionPool() as cursor:
            cursor.execute('UPDATE printing SET finish_time=%s WHERE partid=%s;', (now, partid,))
            cursor.execute('UPDATE printing SET status=%s WHERE partid=%s;', ('finished', partid,))
            

