"""X5h mini termal yazıcı için BLE sürücüsü.

Yazıcı BLE üzerinden "51 78 ..." paket protokolüyle konuşur.
Tüm Bluetooth işlemleri ayrı bir arka plan iş parçacığında (asyncio) çalışır;
arayüz sadece olay (event) kuyruğunu dinler.
"""
import asyncio
import sys
import threading
import time

from bleak import BleakClient, BleakScanner

DEFAULT_ADDRESS = "D6:A1:B3:7C:D1:DC"
NAME_PREFIX = "X5"
TX_CHAR = "0000ae01-0000-1000-8000-00805f9b34fb"
RX_CHAR = "0000ae02-0000-1000-8000-00805f9b34fb"

PRINT_WIDTH = 384
ROW_BYTES = PRINT_WIDTH // 8

HEARTBEAT_INTERVAL = 4.0   # sn: bu aralıkla durum sorgusu gönderilir
REPLY_TIMEOUT = 12.0       # sn: bu süre yanıt yoksa bağlantı "zayıf" sayılır

# Koyuluk seviyeleri (yazıcının ısıtma enerjisi)
ENERGY = {"Açık": 8000, "Normal": 12000, "Koyu": 18000, "Çok koyu": 26000}

LATTICE_START = bytes([0xAA, 0x55, 0x17, 0x38, 0x44, 0x5F, 0x5F, 0x5F, 0x44, 0x38, 0x2C])
LATTICE_END = bytes([0xAA, 0x55, 0x17, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x17])


def crc8(data):
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def packet(cmd, data=b""):
    data = bytes(data)
    n = len(data)
    return bytes([0x51, 0x78, cmd, 0x00, n & 0xFF, n >> 8]) + data + bytes([crc8(data), 0xFF])


class X5Printer:
    """Arka planda çalışan yazıcı bağlantısı.

    on_event(tuple) arka plan iş parçacığından çağrılır. Olaylar:
      ("state", durum, mesaj)  durum: disconnected|connecting|connected|weak|lost|error
      ("reply", zaman, hex)
      ("progress", 0..1)
    """

    def __init__(self, on_event):
        self._on_event = on_event
        self._client = None
        self._hb_task = None
        self._printing = False
        self._user_disconnect = False
        self._resume = None
        self.state = "disconnected"
        self.last_reply = 0.0
        self.address = None
        self._loop = asyncio.new_event_loop()
        ready = threading.Event()
        self._thread = threading.Thread(target=self._run, args=(ready,), daemon=True, name="ble")
        self._thread.start()
        ready.wait()

    # ---- iş parçacığı altyapısı ----
    def _run(self, ready):
        asyncio.set_event_loop(self._loop)
        self._resume = asyncio.Event()
        self._resume.set()
        ready.set()
        self._loop.run_forever()

    def _submit(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def _emit(self, *args):
        try:
            self._on_event(args)
        except Exception:
            pass

    def _set_state(self, state, msg=""):
        self.state = state
        self._emit("state", state, msg)

    # ---- dışarıya açık metotlar (arayüzden çağrılır, Future döner) ----
    @property
    def connected(self):
        return self._client is not None and self._client.is_connected

    def connect(self):
        return self._submit(self._connect())

    def disconnect(self):
        return self._submit(self._disconnect())

    def print_rows(self, rows, energy=ENERGY["Normal"], copies=1):
        return self._submit(self._print(rows, energy, copies))

    def feed(self, lines=80):
        return self._submit(self._feed(lines))

    def shutdown(self):
        try:
            self._submit(self._disconnect()).result(timeout=5)
        except Exception:
            pass
        self._loop.call_soon_threadsafe(self._loop.stop)

    # ---- bağlantı ----
    async def _connect(self):
        if self.connected:
            return
        self._user_disconnect = False
        self._set_state("connecting", "Yazıcı aranıyor...")
        try:
            device = await BleakScanner.find_device_by_filter(
                lambda d, ad: (d.name or ad.local_name or "").upper().startswith(NAME_PREFIX),
                timeout=8.0,
            )
        except Exception as e:
            self._set_state("error", f"Bluetooth taraması başarısız: {e}. Bluetooth açık mı?")
            return

        if device is None and sys.platform == "darwin":
            # macOS (CoreBluetooth) MAC adresi kullanmaz; cihaz taramada bulunmalı
            self._set_state("error", "Yazıcı bulunamadı: açık olduğundan, telefona bağlı olmadığından ve "
                                     "Bluetooth izni verildiğinden emin olun.")
            return
        target = device or DEFAULT_ADDRESS
        self._set_state("connecting", "Bağlanılıyor...")
        client = BleakClient(target, disconnected_callback=self._on_disconnected, timeout=20.0)
        try:
            await client.connect()
            await client.start_notify(RX_CHAR, self._on_notify)
        except Exception as e:
            try:
                await client.disconnect()
            except Exception:
                pass
            hint = "" if device else " Yazıcı bulunamadı: açık olduğundan ve telefona bağlı olmadığından emin olun."
            self._set_state("error", f"Bağlanamadı ({type(e).__name__}).{hint}")
            return

        self._client = client
        self.address = client.address
        self.last_reply = time.time()
        self._resume.set()
        self._set_state("connected", f"Bağlandı ({client.address})")
        await self._write(packet(0xA3, b"\x00"))
        self._hb_task = asyncio.create_task(self._heartbeat())

    async def _disconnect(self):
        self._user_disconnect = True
        if self._hb_task:
            self._hb_task.cancel()
            self._hb_task = None
        client, self._client = self._client, None
        if client is not None:
            try:
                await client.disconnect()
            except Exception:
                pass
        self._set_state("disconnected", "Bağlantı kesildi")

    def _on_disconnected(self, _client):
        if self._client is None and self._user_disconnect:
            return
        self._client = None
        self._resume.set()
        if self._hb_task:
            self._hb_task.cancel()
            self._hb_task = None
        if self._user_disconnect:
            self._set_state("disconnected", "Bağlantı kesildi")
        else:
            self._set_state("lost", "Bağlantı koptu! Yazıcı kapanmış veya uzaklaşmış olabilir.")

    def _on_notify(self, _char, data):
        data = bytes(data)
        self.last_reply = time.time()
        self._emit("reply", self.last_reply, data.hex(" "))
        # Akış kontrolü: yazıcı arabelleği dolunca 0xAE ile "dur" (0x10) / "devam" (0x00) der
        if len(data) >= 7 and data[0] == 0x51 and data[1] == 0x78 and data[2] == 0xAE:
            if data[6] == 0x10:
                self._resume.clear()
            else:
                self._resume.set()
        if self.state == "weak":
            self._set_state("connected", "Bağlantı yeniden sağlam")

    async def _heartbeat(self):
        try:
            while self.connected:
                if not self._printing:
                    try:
                        await self._write(packet(0xA3, b"\x00"))
                    except Exception:
                        pass
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if not self.connected or self._printing:
                    continue
                age = time.time() - self.last_reply
                if age > REPLY_TIMEOUT and self.state == "connected":
                    self._set_state("weak", "Bağlı görünüyor ama yazıcı yanıt vermiyor")
        except asyncio.CancelledError:
            pass

    # ---- baskı ----
    async def _write(self, data):
        if not self.connected:
            raise ConnectionError("Yazıcı bağlı değil")
        await self._client.write_gatt_char(TX_CHAR, data, response=False)

    async def _print(self, rows, energy, copies):
        if not self.connected:
            raise ConnectionError("Yazıcı bağlı değil. Önce 'Bağlan' tuşuna basın.")
        self._printing = True
        total = max(1, len(rows) * copies)
        done = 0
        try:
            for _ in range(copies):
                await self._write(packet(0xA4, b"\x33"))                        # kalite
                await self._write(packet(0xAF, int(energy).to_bytes(2, "little")))  # koyuluk
                await self._write(packet(0xBE, b"\x00"))                        # görüntü modu
                await self._write(packet(0xBD, b"\x23"))                        # hız
                await self._write(packet(0xA6, LATTICE_START))
                for row in rows:
                    if not self._resume.is_set():
                        try:
                            await asyncio.wait_for(self._resume.wait(), 10)
                        except asyncio.TimeoutError:
                            pass
                    await self._write(packet(0xA2, row))
                    done += 1
                    if done % 16 == 0:
                        self._emit("progress", done / total)
                    await asyncio.sleep(0.01)
                await self._write(packet(0xA1, (80).to_bytes(2, "little")))   # kağıdı ilerlet
                await self._write(packet(0xA6, LATTICE_END))
                await asyncio.sleep(0.8)
            self._emit("progress", 1.0)
        finally:
            self._printing = False
            self.last_reply = time.time()

    async def _feed(self, lines):
        if not self.connected:
            raise ConnectionError("Yazıcı bağlı değil. Önce 'Bağlan' tuşuna basın.")
        await self._write(packet(0xA1, int(lines).to_bytes(2, "little")))
