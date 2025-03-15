import time
import mqtt_simple


class MQTTClient(mqtt_simple.MQTTClient):
    DELAY = 2
    DEBUG = False

    def delay(self, i):
        time.sleep(self.DELAY)

    def log(self, in_reconnect, e):
        if self.DEBUG:
            if in_reconnect:
                print("mqtt reconnect: %r" % e)
            else:
                print("mqtt: %r" % e)

    def reconnect(self):
        # try to reconnect 1 time
        try:
            return super().connect(False)
        except OSError as e:
            self.log(True, e)
            self.delay(1)

    def publish(self, topic, msg, retain=False, qos=0):
        # try to publish 2 times
        for i in range(2):
            try:
                return super().publish(topic, msg, retain, qos)
            except OSError as e:
                self.log(False, e)
            self.reconnect()

    def wait_msg(self):
        while 1:
            try:
                return super().wait_msg()
            except OSError as e:
                self.log(False, e)
            self.reconnect()

    def check_msg(self, attempts=2):
        while attempts:
            self.sock.setblocking(False)
            try:
                return super().wait_msg()
            except OSError as e:
                self.log(False, e)
            self.reconnect()
            attempts -= 1