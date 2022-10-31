from PIL import Image
from brother_ql.conversion import convert
from brother_ql.backends.helpers import send
from brother_ql.raster import BrotherQLRaster
from database import CursorFromConnectionPool
from database import Database

import qrcode
import cv2
import urllib
import numpy as np
import psycopg2
import datetime

connection = psycopg2.connect(database='DTLSQLV2', user='postgres', password='4321', host='172.31.1.163')
cursor=connection.cursor()
Database.initialise(database="DTLSQLV2", user="postgres", password="4321", host='172.31.1.163')

# -----------------------QR code related functions--------------------------

# generate and save a QRcode by input filamentID
def gen_QRcode(filamentid):
    img = qrcode.make(filamentid)
    type(img)
    return img

# read QR code by img
def read_QRcode(img):
    try:
        detect = cv2.QRCodeDetector()
        value, points, straight_qrcode = detect.detectAndDecode(img)
        return value
    except:
        return
    
# read QR code from a octopi camera
# Keep reading until detect QRcode
def scan_QRcode_by_printer(printerid):
    W = True
    while W:
        req = urllib.request.urlopen("http://172.31.1.22"+str(printerid+4)+":8080/?action=snapshot")#
        arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
        img = cv2.imdecode(arr, -1)
        result = read_QRcode(img)
        if result != '':
            W = False
            return result

# -------------------LabelMaker related functions-----------------------------

# generate a picture with QR code on left and information on right
def generate_label(filamentid, colour, filament_diameter, material, today, price):
    qr = gen_QRcode(str(filamentid))
    ones = np.ones([290, 500])
    font = cv2.FONT_HERSHEY_SIMPLEX
    fontScale = 1.15
    thickness = 2

#     now = datetime.datetime.now().strftime("%Y-%m-%d")
    ones = cv2.putText(ones, 'Filament ID : %s' %str(filamentid), (0, 70), font, 
                       fontScale, 0, thickness, cv2.LINE_AA)
    ones = cv2.putText(ones, '%s         %s' %(colour, material), (0, 125), font, 
                       fontScale, 0, thickness, cv2.LINE_AA)
    ones = cv2.putText(ones, '%s%s      %s%s' %(filament_diameter, 'mm', '$', price), (0, 180), font, 
                       fontScale, 0, thickness, cv2.LINE_AA)
    ones = cv2.putText(ones, 'Open Date: %s' %today, (0, 235), font, 
                       fontScale, 0, thickness, cv2.LINE_AA)
    pic = np.concatenate([qr, ones], axis=1)
    return pic*255

# Original code from brother_ql
def send_to_labelmaker(im):
    im = Image.fromarray(im)
    backend = 'pyusb'    # 'pyusb', 'linux_kernal', 'network'
    model = 'QL-700' # your printer model.
    printer = 'usb://0x04f9:0x2042'  # Get these values from the Windows usb driver filter.  Linux/Raspberry Pi uses '/dev/usb/lp0'.
    qlr = BrotherQLRaster(model)
    qlr.exception_on_warning = True

    instructions = convert(
            qlr=qlr, 
            images=[im],    #  Takes a list of file names or PIL objects.
            label='62', 
            rotate='0',    # 'Auto', '0', '90', '270'
            threshold=70.0,    # Black and white threshold in percent.
            dither=False, 
            compress=False, 
            red=False,    # Only True if using Red/Black 62 mm label tape.
            dpi_600=False, 
            hq=True,    # False for low quality.
            cut=True

    )

    send(instructions=instructions, printer_identifier=printer, backend_identifier=backend, blocking=True)

# -------------------Filament related functions-----------------------------
# no filamentID required for input, generate automatically when input new filament info
class Filament:
    def __init__(self, material, colour, filament_diameter, current_loc, price, open_date, brand, left_weight):
        self.material = material
        self.colour = colour
        self.filament_diameter = filament_diameter
        self.current_loc = current_loc
        self.price = price
        self.open_date = open_date
        self.brand = brand
        self.left_weight = left_weight
    
    @classmethod
    # when take a filament off from the printer and update its weight to database
    # should scan the QR code first to get the filament id
    def update_filament_weight(cls, filamentid, new_weight):
        with CursorFromConnectionPool() as cursor:
            cursor.execute('UPDATE filament SET left_weight=%s WHERE filamentid=%s;', (new_weight, filamentid,))
    @classmethod
    # when take a filament off from the printer and update its weight to database
    # should scan the QR code first to get the filament id
    def update_filament_loc(cls, filamentid, new_loc):
        with CursorFromConnectionPool() as cursor:
            cursor.execute('UPDATE filament SET current_loc=%s WHERE filamentid=%s;', (new_loc, filamentid,))
    @classmethod
    # add a new roll of filament to database, price, open_data, brand, left_weight can be '-'
    # automatically print QR code from labelmaker
    def add_new_filament(cls, material, colour, filament_diameter, current_loc, price, open_date, brand, left_weight): 
        # make commend line first
        inputs = [material, colour, filament_diameter, current_loc]
        sub_inputs = [price, open_date, brand, left_weight]
        names_col = ['price', 'open_date', 'brand', 'left_weight']
        cmd = 'INSERT INTO filament (material, colour, filament_diameter, current_loc'
        'price, open_date, brand, left_weight) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)'
        cmd_end = ') VALUES (%s, %s, %s, %s'
        empty_inputs = [i for i, x in enumerate(sub_inputs) if x == "-"]
        for i in range(len(sub_inputs)):
            if i in empty_inputs:
                pass
            else:
                cmd = cmd + ', ' + names_col[i]
                cmd_end = cmd_end + ', %s'
                inputs = inputs + [sub_inputs[i]]
        cmd = cmd + cmd_end + ')'
        # finished making commend line
        
        if open_date == 'today':
            open_data = datetime.datetime.now().strftime("%Y-%m-%d")
        with CursorFromConnectionPool() as cursor:
            cursor.execute(cmd, inputs)
            cursor.execute('SELECT filamentid FROM filament ORDER BY filamentid DESC')
            filamentid = cursor.fetchone()[0]
            im = generate_label(filamentid, colour, filament_diameter, material, open_date, price)
            send_to_labelmaker(im)
    @classmethod
    # 新增一个filament 随便写来不trigger label maker用python自动生成虚假数据的
    def add_new_filament_no_label(cls, material, colour, filament_diameter, current_loc, price, date, brand, left_weight): 
        with CursorFromConnectionPool() as cursor:
            cursor.execute('INSERT INTO filament (material, colour, filament_diameter, current_loc, \
            price, open_date, brand, left_weight) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                            (material, colour, filament_diameter, current_loc, price, date, brand, left_weight,))

# -------------------Printer related functions-----------------------------
class Printer:
    def __init__(self, printerid, status, start_time, filamentid):
        self.printerid = printerid
        self.status = status
        self.start_time = start_time
        self.filamentid = filamentid
    @classmethod
    # 加入一个新的printer
    def add_new_printer(cls, printerid, status, filamentid): 
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with CursorFromConnectionPool() as cursor:
            cursor.execute('INSERT INTO printer_tracking (printerid, status, start_time, filamentid) \
            VALUES (%s, %s, %s, %s)', (printerid, status, now, filamentid))
    @classmethod
    # 已经有了最初的信息要更新printer的状态 只需要输入printerid和新的状态 时间自动抓取现在 filament自动抓取当前的filament
    def update_status_by_printer(cls, printerid, status): 
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with CursorFromConnectionPool() as cursor:
            cursor.execute('SELECT filamentid FROM printer_tracking WHERE printerid=%s ORDER BY start_time DESC;', \
                           (printerid,))
            filamentid = cursor.fetchone()
            cursor.execute('INSERT INTO printer_tracking (printerid, status, start_time, filamentid) \
            VALUES (%s, %s, %s, %s)', (printerid, status, now, filamentid))
    @classmethod
    # 更改filament 这里不需要check状态是maintaning check maintaning的步骤从OPCUA层面实现
    # 没有filament的时候filamentid的位置输入None
    def load_filamentid_by_printer(cls, printerid, filamentid):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with CursorFromConnectionPool() as cursor:
            cursor.execute('SELECT status FROM printer_tracking WHERE printerid=%s ORDER BY start_time DESC;', \
                           (printerid,))
            status = cursor.fetchone()
            cursor.execute('INSERT INTO printer_tracking (printerid, status, start_time, filamentid) \
            VALUES (%s, %s, %s, %s)', (printerid, status, now, filamentid))

# -------------------Printing Job related functions-----------------------------
class Printing:
    def __init__(self, assigned_printerid, start_time, finish_time, snapshot_path, print_result):
        self.assigned_printerid = assigned_printerid
        self.start_time = start_time
        self.finish_time = finish_time
        self.snapshot_path = snapshot_path
        self.print_result = print_result
    @classmethod
    # 开始一个print job 自动发一个partid，记录part_name
    def start_part_by_printerid(cls, printerid, part_name): 
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with CursorFromConnectionPool() as cursor:
            cursor.execute('INSERT INTO printing (assigned_printerid, start_time, part_name) VALUES (%s, %s, %s)',
                            (printerid, now, part_name,))
    @classmethod
    def snapshot_by_printer(cls, printerid):
        req = urllib.request.urlopen("http://172.31.1.22"+str(int(printerid)+4)+":8080/?action=snapshot")
        arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
        img = cv2.imdecode(arr, -1)
        return img
    @classmethod
    # 结束一个print job 只给定printerid 程序自己找该printer现在在print哪个partid
    def finish_part_by_printerid(cls, printerid):
        with CursorFromConnectionPool() as cursor:
            cursor.execute('SELECT partid FROM printing WHERE assigned_printerid=%s AND finish_time IS NULL ORDER BY start_time DESC;', 
                           (printerid,))
            if cursor.fetchone() == None:
                print('Printer'+str(printerid)+' does not have unfinished work')
            else:
                now = datetime.datetime.now()
                img = Printing.snapshot_by_printer(printerid)
                path = 'snapshots/Printer'+str(printerid)+'_'+str(now.strftime("%Y-%m-%d_%H-%M-%S"))+'.png'
                cv2.imwrite(path, img)
                now = now.strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute('SELECT partid FROM printing WHERE assigned_printerid=%s AND finish_time IS NULL ORDER BY start_time DESC;', 
                           (printerid,))
                partid = cursor.fetchone()[0]
                cursor.execute('UPDATE printing SET finish_time=%s, snapshot_path=%s, print_result=%s WHERE partid=%s;', 
                               (now, path, 'finished', partid,))
    @classmethod
    # 取消一个print job 只给定printerid 程序自己找该printer现在在print哪个partid
    def cancel_part_by_printerid(cls, printerid):
        with CursorFromConnectionPool() as cursor:
            cursor.execute('SELECT partid FROM printing WHERE assigned_printerid=%s AND finish_time IS NULL ORDER BY start_time DESC;', 
                           (printerid,))
            if cursor.fetchone() == None:
                print('Printer'+str(printerid)+' does not have unfinished work')
            else:
                now = datetime.datetime.now()
                img = Printing.snapshot_by_printer(printerid)
                path = 'snapshots/Printer'+str(printerid)+'_'+str(now.strftime("%Y-%m-%d_%H-%M-%S"))+'.png'
                cv2.imwrite(path, img)
                now = now.strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute('SELECT partid FROM printing WHERE assigned_printerid=%s AND finish_time IS NULL ORDER BY start_time DESC;', 
                           (printerid,))
                partid = cursor.fetchone()[0]
                cursor.execute('UPDATE printing SET finish_time=%s, snapshot_path=%s, print_result=%s WHERE partid=%s;', 
                               (now, path, 'cancelled', partid,))




