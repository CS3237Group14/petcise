import asyncio
import time
from bleak import BleakClient
import struct
from datetime import datetime
import numpy as np

import pyrebase

import tensorflow as tf
from tensorflow.python.keras.backend import set_session
from keras.models import load_model
from collections import deque

task_queue = deque()
ones = np.ones((20, 12))
segment = np.asarray(np.ones((20, 12)), dtype= np.float32).reshape(-1, 240)
task_queue.append(segment)

config = {
  "apiKey": "AIzaSyAVL9OlUxeg4ACKJS3l-i-qY6aJ-Bkee_4",
  "authDomain": "cs3237-motion-detection.firebaseapp.com",
  "databaseURL": "https://cs3237-motion-detection-default-rtdb.asia-southeast1.firebasedatabase.app/",
  "storageBucket": "cs3237-motion-detection.appspot.com"
}

email = "nguyen2001ag2@gmail.com"
password = "nguyen752001"

print("I reached here")
firebase = pyrebase.initialize_app(config)
print("I have initilized the app")
MODEL_FILE = "best_model.48-0.94.h5"

data_jen = []
temp_data = [30, 31]
sensor1_data = [0, 0, 0, 0, 0, 0]
sensor2_data = [0, 0, 0, 0, 0, 0]
        
class Service:
    """
    Here is a good documentation about the concepts in ble;
    https://learn.adafruit.com/introduction-to-bluetooth-low-energy/gatt

    In TI SensorTag there is a control characteristic and a data characteristic which define a service or sensor
    like the Light Sensor, Humidity Sensor etc

    Please take a look at the official TI user guide as well at
    https://processors.wiki.ti.com/index.php/CC2650_SensorTag_User's_Guide
    """

    def __init__(self):
        self.data_uuid = None
        self.ctrl_uuid = None


class Sensor(Service):

    def callback(self, sender: int, data: bytearray):
        raise NotImplementedError()

    async def start_listener(self, client, *args):
        # start the sensor on the device
        write_value = bytearray([0x01])
        await client.write_gatt_char(self.ctrl_uuid, write_value)

        # listen using the handler
        await client.start_notify(self.data_uuid, self.callback)


class MovementSensorMPU9250SubService:

    def __init__(self):
        self.bits = 0
        self.address = 0

    def enable_bits(self):
        return self.bits

    def cb_sensor(self, data):
        raise NotImplementedError


class MovementSensorMPU9250(Sensor):
    GYRO_XYZ = 7
    ACCEL_XYZ = 7 << 3
    MAG_XYZ = 1 << 6
    ACCEL_RANGE_2G  = 0 << 8
    ACCEL_RANGE_4G  = 1 << 8
    ACCEL_RANGE_8G  = 2 << 8
    ACCEL_RANGE_16G = 3 << 8

    def __init__(self, address):
        super().__init__()
        self.data_uuid = "f000aa81-0451-4000-b000-000000000000"
        self.ctrl_uuid = "f000aa82-0451-4000-b000-000000000000"
        self.period_uuid = "f000aa83-0451-4000-b000-000000000000"
        self.ctrlBits = 0
        self.address = address

        self.sub_callbacks = []

    def register(self, cls_obj: MovementSensorMPU9250SubService):
        self.ctrlBits |= cls_obj.enable_bits()
        
        # append cb_sensor callback to the callback array
        self.sub_callbacks.append(cls_obj.cb_sensor)

    async def start_listener(self, client, *args):
        # start the sensor on the device
        await client.write_gatt_char(self.ctrl_uuid, struct.pack("<H", self.ctrlBits))

        # set the period
        write_value = bytearray([0x0A])
        await client.write_gatt_char(self.period_uuid, write_value)

        # listen using the handler
        await client.start_notify(self.data_uuid, self.callback)

    def callback(self, sender: int, data: bytearray):
        gyro_scale = 500.0/65536.0
        acc_scale = 8.0/32768.0
        
        print(self.address)
        unpacked_data = struct.unpack("<hhhhhhhhh", data)
#        for cb in self.sub_callbacks:
#            cb(unpacked_data)
        milliseconds = int(round(time.time() * 1000))
        
        if (self.address == "6B61D247-965C-4AB4-A067-4152836B9E4C"):
            sensor1_data[0:6] = list(tuple([ v for v in data[0:6] ]))
            # sensor1_data.append(temp_data[0])
        else:
            sensor2_data = list(tuple([ v for v in data[0:6] ]))
            # sensor1_data.append(temp_data[0])
            sensor_data = sensor2_data + sensor1_data
            sensor_data.append(milliseconds)
        
            data_jen.append(sensor_data)
            
            data_np = np.array(data_jen)
            print("sensor data shape: ", data_np.shape)
            if data_np.shape[0] % 20 == 0 and data_np.shape[0] != 0:
                print("Append")
                segments = data_np[-20, :12]
                reshaped_segments = np.asarray(ones, dtype=np.float32).reshape(-1, 240)
                task_queue.append(reshaped_segments)
        

class AccelerometerSensorMovementSensorMPU9250(MovementSensorMPU9250SubService):
    def __init__(self):
        super().__init__()
        self.bits = MovementSensorMPU9250.ACCEL_XYZ | MovementSensorMPU9250.ACCEL_RANGE_4G
        self.scale = 8.0/32768.0 # TODO: why not 4.0, as documented? @Ashwin Need to verify


    def cb_sensor(self, data):
        '''Returns (x_accel, y_accel, z_accel) in units of g'''
        rawVals = data[3:6]
        now = datetime.now()
        #current_time = now.strftime("%H:%M:%S:%f")
        print("Current Time =", now)
        print("[MovementSensor] Accelerometer:", tuple([ v*self.scale for v in rawVals ]))



class MagnetometerSensorMovementSensorMPU9250(MovementSensorMPU9250SubService):
    def __init__(self):
        super().__init__()
        self.bits = MovementSensorMPU9250.MAG_XYZ
        self.scale = 4912.0 / 32760
        # Reference: MPU-9250 register map v1.4

    def cb_sensor(self, data):
        '''Returns (x_mag, y_mag, z_mag) in units of uT'''
        rawVals = data[6:9]
        print("[MovementSensor] Magnetometer:", tuple([ v*self.scale for v in rawVals ]))

class GyroscopeSensorMovementSensorMPU9250(MovementSensorMPU9250SubService):
    def __init__(self):
        super().__init__()
        self.bits = MovementSensorMPU9250.GYRO_XYZ
        self.scale = 500.0/65536.0

    def cb_sensor(self, data):
        '''Returns (x_gyro, y_gyro, z_gyro) in units of degrees/sec'''
        rawVals = data[0:3]
        print(time.time())
        print("[MovementSensor] Gyroscope:", tuple([ v*self.scale for v in rawVals ]))
        

#class BarometerSensor(Sensor):
#    def __init__(self):
#        super().__init__()
#        self.data_uuid = "f000aa41-0451-4000-b000-000000000000"
#        self.ctrl_uuid = "f000aa42-0451-4000-b000-000000000000"
#
#    def callback(self, sender: int, data: bytearray):
#        (tL, tM, tH, pL, pM, pH) = struct.unpack('<BBBBBB', data)
#        temp = (tH*65536 + tM*256 + tL) / 100.0
#        press = (pH*65536 + pM*256 + pL) / 100.0
#        print(f"[BarometerSensor] Ambient temp: {temp}; Pressure Millibars: {press}")
#        temp_data[0] = temp
        
# temperatureUUID = "45366e80-cf3a-11e1-9ab4-0002a5d5c51b"
# ecgUUID = "46366e80-cf3a-11e1-9ab4-0002a5d5c51b"

# notify_uuid = "f000aa81-0451-4000-b000-000000000000"


# def callback(sender, data):
#     print(sender, data)


# async def connect_to_device(address):
#     print("starting", address, "loop")
#     async with BleakCliexnt(address, timeout=5.0) as client:

#         print("connect to", address)
#         try:
#             await client.start_notify(notify_uuid, callback)
#             await asyncio.sleep(10.0)
#             await client.stop_notify(notify_uuid)
#         except Exception as e:
#             print(e)

#     print("disconnect from", address)


# def main(addresses):
#     return asyncio.gather(*(connect_to_device(address) for address in addresses))


# if __name__ == "__main__":
#     asyncio.run(
#         main(
#             [
#                 "54:6C:0E:53:37:87",
#                 "FEA6CD43-DB35-4D1D-9CE1-5FD332231D00",
#             ]
#         )
#     )

temperatureUUID = "45366e80-cf3a-11e1-9ab4-0002a5d5c51b"
ecgUUID = "f000aa81-0451-4000-b000-000000000000"


def run(addresses):
    with session.graph.as_default():
        set_session(session)
        model = load_model(MODEL_FILE)
        print("Done loading model")
    loop = asyncio.get_event_loop()

    for address in addresses:
        print("enter loop")
        loop.create_task(connect_to_device(address, loop))
    
    # asyncio.sleep(30)
    loop.run_until_complete(dummy_function())
    
    data_np = np.array(data_jen)
    np.savetxt('jumping_shreya.csv', data_np, delimiter=',')

async def dummy_function():
    db = firebase.database()
    with session.graph.as_default():
        set_session(session)
        model = load_model(MODEL_FILE)
        print("Done loading model")
    
    while True:
        # When predicting
        with session.graph.as_default():
            set_session(session)
            while task_queue:
                recv_dict = task_queue[0]
                result = classify_flower(model, recv_dict)
                task_queue.popleft()
                print("Result", result)
                data = { "name": result }
                results = db.child("users").push(data)
                print("Finish publishing");
        await asyncio.sleep(2)
                
 
def classify_flower(model, data):
    print("Start classifying")
    result = model.predict(data)
    themax = int(np.argmax(result))
    print("Done.")
    return themax
        
async def connect_to_device(address, loop):
    print("Connect to device")

    async with BleakClient(address, loop=loop) as client:

        print("connect to ", address)

        acc_sensor = AccelerometerSensorMovementSensorMPU9250()
        gyro_sensor = GyroscopeSensorMovementSensorMPU9250()

        movement_sensor = MovementSensorMPU9250(address)
        movement_sensor.register(acc_sensor)
        movement_sensor.register(gyro_sensor)

        await movement_sensor.start_listener(client, address)
        while True:
            await asyncio.sleep(0.05, loop=loop)


if __name__ == "__main__":
    session = tf.compat.v1.Session(graph = tf.compat.v1.Graph())
    run([ "6B61D247-965C-4AB4-A067-4152836B9E4C", "FEA6CD43-DB35-4D1D-9CE1-5FD332231D00"])
