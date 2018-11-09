from pcars.packet import Packet
from io import BytesIO
from threading import Thread
import socket
import struct


_MCAST_ANY = "224.0.0.1"
local_ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1][0]

class PCarsStreamReceiver(Thread):

    def __init__(self, port=5606):
        super(PCarsStreamReceiver, self).__init__()
        self.port = port
        self.setDaemon(True)
        self.listeners = []

    def addListener(self, listener):
        self.listeners.append(listener)

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Bind to the server address
        sock.bind(("", self.port))
        group = socket.inet_aton(_MCAST_ANY)
        mreq = struct.pack("4sL", group, socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        while True:
            try:
                data, addr = sock.recvfrom(1400)
                # print("Source:", addr[0])
                if addr[0] == local_ip:
                    packet = Packet.readFrom(BytesIO(data))
                    for listener in self.listeners:
                        listener.handlePacket(packet)
            except Exception as ex:
                print("Error in stream.py : ",ex)