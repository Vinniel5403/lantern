# Lantern — Phase 6: LCD I2C Display & Command Confirmation

## 1. สรุปผล

สถานะรวม Phase 6: **PARTIAL**

สถานะด้าน software: **PASS** และผู้ใช้รายงานว่า LCD 16x2 แสดงผลจริงแล้วด้วย diagnostic firmware ที่ address `0x27` การยืนยันโดย agent ยังจำกัดอยู่ที่ source audit, automated tests และ firmware build

เพิ่ม LCD controller แบบแยกโมดูล, I2C address scanner, display state model และการแสดงผลตาม pipeline โดยไม่เพิ่ม external LCD library และไม่เปลี่ยน GPIO เดิมของ INMP441, diagnostic LED หรือ relay

สถานะการยืนยัน hardware: **USER-REPORTED PASS / electrical details PARTIAL**

ผู้ใช้รายงาน log ต่อไปนี้จากบอร์ดจริง:

```text
LCD I2C scan: SDA=18 SCL=19 preferred=0x27
LCD I2C device found at 0x27
LCD selected at I2C address 0x27 (preferred)
LCD text line1=LANTERN TEST line2=LCD READY
LCD READY address=0x27
```

หลักฐานนี้ยืนยันการแสดงผล diagnostic ตาม user report แต่ยังไม่ยืนยัน voltage ของ backpack/pull-up และไม่ใช่หลักฐานความปลอดภัยของ relay หรือวงจร mains

Phase 7 ยังไม่เริ่ม

## 2. Architecture

โครงสร้างปัจจุบัน:

```text
INMP441/I2S
  -> VAD + utterance segmentation
  -> Wi-Fi HTTP WAV upload
  -> FastAPI + Typhoon ASR
  -> Wake Word + Intent
  -> CommandHandler
  -> RelayController / Diagnostic LED
  -> LcdController status display
```

`LcdController` แยกจาก `RelayController`, `CommandHandler` และ audio pipeline โดยรับเพียง state/event ที่ `main.cpp` ส่งให้ ไม่เรียก ASR, ไม่สั่ง relay และไม่ทำให้ voice pipeline หยุดเมื่อ LCD ไม่พร้อม

ใช้ `Wire` ที่มากับ Arduino-ESP32 แทนไลบรารี `LiquidCrystal_I2C` ภายนอก เพราะ PlatformIO ตรวจพบ built-in dependency `Wire @ 3.3.12` และไม่ต้องเสี่ยงกับ mapping ของ library ที่ไม่ยืนยันกับ backpack รุ่นจริง

## 3. LCD Module Configuration

ค่าจาก `Embedded System/include/lantern_config.h`:

| รายการ | ค่า |
| --- | --- |
| Columns/rows | 16x2 |
| Preferred I2C address | `0x27` |
| SDA | GPIO18 |
| SCL | GPIO19 |
| Driver | Arduino `Wire` + PCF8574-compatible backpack |
| Address scan | preferred address ก่อน แล้ว scan `0x20–0x27` และ `0x38–0x3F` |

ถ้าพบ `0x27` จะเลือก address นี้ ถ้าไม่พบจะเลือก device แรกในช่วง backpack ที่ scanner พบ ถ้าไม่พบอุปกรณ์ใดเลยจะ log `LCD unavailable` และระบบ voice/relay ทำงานต่อ

การ scan ถูกเรียกใน `LcdController::begin()` และผลจะปรากฏใน Serial Monitor เช่น:

```text
LCD I2C scan: SDA=18 SCL=19 preferred=0x27
LCD I2C device found at 0x27
LCD selected at I2C address 0x27 (preferred)
```

ผู้ใช้ยืนยันข้อความดังกล่าวจาก physical board แล้ว จึงจัด address และ diagnostic display เป็น **USER-REPORTED PASS**

## 4. GPIO Mapping และ Conflict Audit

| อุปกรณ์ | GPIO | สถานะ |
| --- | ---: | --- |
| Diagnostic LED | 17 | คงเดิม |
| INMP441 BCLK/SCK | 26 | คงเดิม |
| INMP441 WS/LRCLK | 25 | คงเดิม |
| INMP441 SD/DOUT | 33 | คงเดิม |
| Relay signal `S` | 23 | คงเดิม, active-low |
| LCD SDA | 18 | เพิ่มใน Phase 6 |
| LCD SCL | 19 | เพิ่มใน Phase 6 |

จาก source audit GPIO18 และ GPIO19 ไม่ซ้ำกับ GPIO17, GPIO23, GPIO25, GPIO26 หรือ GPIO33 ที่ใช้อยู่ในปัจจุบัน จึงไม่พบ software GPIO conflict

## 5. Electrical Compatibility Requirements

ต้องตรวจจาก LCD backpack จริงก่อนต่อเข้าบอร์ด:

1. ตรวจว่า backpack ใช้แรงดัน logic เท่าใด และ pull-up ของ SDA/SCL ต่อไปที่แรงดันใด
2. ESP32 GPIO18/GPIO19 เป็น logic 3.3V และห้ามรับ pull-up 5V โดยตรง
3. หาก backpack ต้องใช้ 5V และมี pull-up ไป 5V ต้องใช้ level shifter ที่เหมาะสม หรือปรับวงจร pull-up ตาม datasheet โดยผู้ที่ตรวจสอบวงจรได้
4. ห้ามสมมติว่า VCC ของ backpack ใช้กับ 3.3V ได้ เพียงเพราะ address เป็น `0x27`
5. หากยังยืนยัน voltage/pull-up ไม่ได้ ให้ยังไม่ต่อ SDA/SCL และยังไม่ flash เพื่อ physical LCD validation

Software driver ไม่สามารถป้องกันความเสียหายจากการต่อ 5V เข้าขา ESP32 ได้

## 6. Display State Machine

`DisplayState` อยู่ใน `Embedded System/include/lcd_controller.h` และมี state ดังนี้:

| State | บรรทัดหลัก | บรรทัดรอง |
| --- | --- | --- |
| `BOOTING` | `LANTERN BOOTING` | `STARTING` / `LCD ONLINE` |
| `IDLE` | `READY` | `SAY TEE` |
| `LISTENING` | `LISTENING` | `WAITING SPEECH` |
| `RECORDING` | `RECORDING` | `CAPTURING` |
| `PROCESSING` | `PROCESSING` | `ASR + INTENT` |
| `COMMAND_ACCEPTED` | `COMMAND OK` | `ACCEPTED` |
| `COMMAND_REJECTED` | `COMMAND NO` | `REJECTED` |
| `LIGHT_ON` | `LIGHT ON` | `GPIO CMD SENT` |
| `LIGHT_OFF` | `LIGHT OFF` | `GPIO CMD SENT` |
| `WIFI_DISCONNECTED` | `WIFI OFFLINE` | `RECONNECTING` |
| `BACKEND_ERROR` | `BACKEND ERROR` | error detail |

ข้อความใช้ English ทั้งหมดเพื่อหลีกเลี่ยงการแสดงผลภาษาไทยที่ไม่รองรับบน standard HD44780 character LCD

`setState()` จะ render เฉพาะเมื่อข้อความเปลี่ยน และ `renderLine()` เขียนข้อความ 16 ตัวอักษรโดยเติมช่องว่างส่วนที่เหลือ จึงไม่เรียก `lcd.clear()` ใน main loop และลด flicker

ข้อความผลลัพธ์สำคัญใช้ temporary hold แบบ non-blocking ผ่าน `tick()` โดยไม่ใช้ `delay()` ระหว่าง audio capture

`COMMAND_ACCEPTED` มีอยู่ใน state model และ message map แต่ production flow แสดงผล accepted command เป็น `LIGHT_ON` หรือ `LIGHT_OFF` โดยตรง เพื่อยืนยันผลลัพธ์ที่จะถูก dispatch ไปยัง GPIO ไม่ได้แสดง `COMMAND_ACCEPTED` เป็นหน้าจอแยกต่างหาก

## 7. LCD Message Mapping และ Command Confirmation

| เหตุการณ์จริงใน pipeline | LCD state/message | ความหมาย |
| --- | --- | --- |
| เริ่มระบบ | `BOOTING` | กำลัง initialize |
| รอเสียง | `LISTENING` | microphone loop ทำงาน |
| VAD เริ่ม segment | `RECORDING` | กำลังเก็บเสียง |
| segment จบและส่ง backend | `PROCESSING` | รอ ASR/intent/response |
| Backend accepted `LIGHT_ON` | `LIGHT_ON / GPIO CMD SENT` | ESP32 dispatch GPIO command |
| Backend accepted `LIGHT_OFF` | `LIGHT_OFF / GPIO CMD SENT` | ESP32 dispatch GPIO command |
| missing wake word/rejected intent | `COMMAND_REJECTED` | ไม่เปลี่ยน relay/LED |
| invalid JSON/หลาย intent | `COMMAND_REJECTED / INVALID RESPONSE` | ไม่ execute |
| Wi-Fi หลุด | `WIFI OFFLINE / RECONNECTING` | transport จะ retry ตาม policy เดิม |
| HTTP timeout | `BACKEND ERROR / HTTP TIMEOUT` | ไม่ยืนยันคำสั่งสำเร็จ |
| ASR provider 503 | `BACKEND ERROR / ASR FAILED` | backend แจ้ง ASR failure |
| error อื่น | `BACKEND ERROR / HTTP/ASR FAIL` | backend/transport error |

`GPIO CMD SENT` หมายถึง firmware เรียก `RelayController` และเขียน GPIO ตาม state ที่ต้องการเท่านั้น ไม่ใช่หลักฐานว่าหน้าสัมผัส relay เปลี่ยนจริง การยืนยัน physical contact ต้องใช้ sensing/instrumentation แยกต่างหาก

## 8. Reliability และ Non-blocking Behavior

- LCD ไม่พร้อมใช้งาน: `begin()` คืนค่า false และ pipeline เดินต่อ
- LCD หลุดหลัง initialize: I2C write failure ทำให้ controller disable การเขียนต่อและ log error หนึ่งครั้ง
- repeated state: ไม่เขียนจอซ้ำถ้าข้อความสองบรรทัดไม่เปลี่ยน
- normal loop: ไม่มี `lcd.clear()` และไม่มี delay สำหรับการ refresh
- audio capture/VAD/HTTP retry/request deduplication/relay polarity ยังคงใช้ implementation Phase 5
- transport เพิ่ม `FailureReason` เพื่อแยก `wifi_disconnected`, `http_timeout`, `asr_failure`, `backend_error` และ error ประเภทอื่นสำหรับการแสดงผล

## 8.1 Phase 6 State Transition Bug Fix

พบ root cause จากการตรวจ event flow ใน `main.cpp`:

- `main()` refresh `LISTENING` ทุก loop เมื่อไม่มี temporary hold จึงเขียนทับ `RECORDING` ใน frame ถัดไป แม้ `UtteranceSegmenter::active()` ยังเป็นจริง
- `BackendTransport::ensureWiFi()` retry แบบ blocking โดยไม่มี event callback ทำให้ LCD ไม่ได้รับสถานะ disconnect ระหว่าง reconnect ทันที

การแก้ไข:

- normal display refresh ตรวจ Wi-Fi ก่อน แล้วตรวจ `segmenter.active()` เพื่อให้ `WIFI OFFLINE` เป็น critical priority และ `RECORDING` ไม่ถูก `LISTENING` ทับเมื่อ Wi-Fi ปกติ
- เพิ่ม `BackendTransport::ConnectionStatusCallback` แจ้ง `[WiFi] Disconnected` และ `[WiFi] Connected` ให้ `main.cpp`
- `LcdController::tick()` ไม่เปลี่ยน `WIFI_DISCONNECTED` เป็น `IDLE` หากยังไม่มีการ reconnect
- เพิ่ม `[LCD] previous -> next` transition logs โดยไม่เพิ่ม `delay()` ใน audio path
- เพิ่ม `lcd_state_test` สำหรับ cycle `LISTENING`, `RECORDING`, `PROCESSING`, `WIFI OFFLINE`, `LIGHT ON`, `LIGHT OFF` โดยไม่ initialize relay, I2S, Wi-Fi หรือ backend

## 9. Changed Files

ไฟล์ที่เพิ่ม:

- `Embedded System/include/lcd_controller.h`
- `Embedded System/src/lcd_controller.cpp`
- `Embedded System/src/lcd_test_main.cpp` — standalone scanner/diagnostic firmware
- `Embedded System/tests/test_lcd_state.py`
- `docs/phase-6.md`

ไฟล์ที่แก้:

- `Embedded System/include/lantern_config.h` — เพิ่ม address และ SDA/SCL configuration
- `Embedded System/include/transport.h` — เพิ่ม failure reason API
- `Embedded System/src/transport.cpp` — จำแนก failure reason สำหรับ LCD/error reporting
- `Embedded System/include/command_handler.h` — เพิ่ม `CommandResult`
- `Embedded System/src/command_handler.cpp` — คืนผล accepted/rejected/invalid/light state
- `Embedded System/src/main.cpp` — integrate LCD state กับ actual pipeline transitions
- `Embedded System/include/transport.h` — เพิ่ม connection status callback interface
- `Embedded System/src/transport.cpp` — แจ้ง Wi-Fi state transitions ระหว่าง bounded reconnect
- `Embedded System/src/lcd_controller.cpp` — รักษา WIFI OFFLINE state และเพิ่ม transition logs
- `Embedded System/platformio.ini` — แยก `lcd_test` จาก production `esp32dev` และกัน diagnostic `setup()/loop()` ไม่ให้ถูก link ร่วมกัน
- `Embedded System/src/lcd_state_test_main.cpp` — standalone LCD state-cycle diagnostic
- `Embedded System/tests/test_lcd_state.py` — เพิ่ม priority และ transition regression tests
- `Embedded System/upload_monitor.py` — upload/monitor helper ผ่าน Python
- `Embedded System/upload-monitor.ps1` — upload/monitor helper ผ่าน PowerShell
- `Embedded System/upload-monitor.sh` — upload/monitor helper ผ่าน Bash/Git Bash

แก้เฉพาะ LCD pin configuration เป็น SDA GPIO18 และ SCL GPIO19 ตาม hardware mapping ล่าสุด ไม่ได้แก้ relay GPIO23, relay polarity, INMP441 pins, backend API contract, Typhoon provider หรือ mains wiring

## 10. Firmware Build Results

คำสั่งที่รัน:

```powershell
cd "D:\lantern\Embedded System"
$env:PLATFORMIO_CORE_DIR = 'D:\lantern\.pio-core'
& "$env:USERPROFILE\.platformio\penv\Scripts\platformio.exe" run -e esp32dev
& "$env:USERPROFILE\.platformio\penv\Scripts\platformio.exe" run -e relay_test
& "$env:USERPROFILE\.platformio\penv\Scripts\platformio.exe" run -e lcd_test
```

ผล:

| Environment | ผล | RAM | Flash |
| --- | --- | ---: | ---: |
| `esp32dev` | **PASS** | 18.1% (59248/327680) | 82.6% (1082876/1310720) |
| `relay_test` | **PASS** | 6.7% (22116/327680) | 22.3% (292816/1310720) |
| `lcd_test` | **PASS** | 7.2% (23556/327680) | 25.5% (333756/1310720) |
| `lcd_state_test` | **PASS** | 7.2% (23564/327680) | 25.4% (333296/1310720) |

PlatformIO ตรวจพบ built-in `Wire @ 3.3.12` และ compile `lcd_controller.cpp` สำเร็จ จึงยืนยัน compatibility ระดับ compile กับ Arduino-ESP32 ที่ใช้อยู่

Warnings ที่ยังมีอยู่เป็น `CORE_DEBUG_LEVEL` ถูก define ซ้ำ และ legacy I2S API deprecation เดิม ไม่ใช่ LCD compile failure

## 11. Automated Test Results

| Test | ผล |
| --- | --- |
| Backend pytest | **PASS — 50 passed, 1 warning** |
| Backend compileall | **PASS** |
| LCD state host simulation | **PASS — 5 tests** |
| Relay host simulation | **PASS — 10 tests** |
| Transport policy tests | **PASS — 3 tests** |
| PlatformIO `esp32dev` | **PASS** |
| PlatformIO `relay_test` | **PASS** |
| PlatformIO `lcd_test` | **PASS** |
| PlatformIO `lcd_state_test` | **PASS** |
| Physical LCD I2C scan | **USER-REPORTED PASS — address 0x27** |
| Physical LCD display refresh | **USER-REPORTED PASS — LANTERN TEST / LCD READY** |

pytest warning เป็น `StarletteDeprecationWarning` จาก TestClient/httpx และไม่มี test failure

## 12. Physical Hardware Verification Checklist

ทำเฉพาะ low-voltage และหลังยืนยัน backpack voltage/pull-up แล้ว:

1. ระบุ VCC/GND/SDA/SCL จาก label และ datasheet ของ backpack จริง
2. ยืนยันว่า SDA/SCL ไม่ถูก pull-up ไป 5V หรือใช้ level shifter ที่เหมาะสม
3. ต่อ SDA ไป GPIO18 และ SCL ไป GPIO19 ตาม mapping ที่ตรวจแล้ว
4. เปิด Serial Monitor 115200 และตรวจผล I2C scan
5. ยืนยันว่า address ที่พบเป็น `0x27` หรือ address อื่นที่ scanner เลือก
6. ตรวจข้อความ `LCD selected` และ state `READY`
7. พูดคำสั่งจนเกิด `RECORDING`, `PROCESSING`, `LIGHT ON/OFF`
8. ทดสอบ missing wake word, unsupported command, ASR error, HTTP timeout และ Wi-Fi reconnect
9. ตรวจว่า LCD ไม่ทำให้ INMP441/VAD/HTTP upload หยุด
10. ตรวจ relay ด้วย low-voltage load เท่านั้น

ห้ามต่อหรือทดสอบ exposed 220V wiring และห้ามใช้ผลจาก LCD เป็นหลักฐานว่า relay contact หรือวงจรไฟฟ้าปลอดภัย

## 13. Remaining Safety Limitations

- ผู้ใช้ยืนยัน LCD I2C address `0x27` และข้อความ diagnostic แล้ว แต่ยังไม่ยืนยัน LCD backpack logic voltage และ pull-up voltage ด้วยการตรวจวงจร/เครื่องมือวัด
- Software ไม่สามารถรับประกัน relay OFF ระหว่าง ESP32 reset, ROM bootloader, brownout หรือไฟเลี้ยงไม่เสถียร
- ปัญหา relay activation/floating GPIO/chatter ที่เคยพบยังถือว่า unresolved จนกว่าจะตรวจด้วย hardware ที่เหมาะสม
- `GPIO CMD SENT` ไม่ได้แปลว่า contact เปลี่ยนจริง
- LCD I2C bus อาจมี pull-up ซ้ำหรือแรงดันไม่ compatible ต้องตรวจวงจรก่อนใช้งานจริง

## 14. Phase 7 Readiness

สถานะ: **NOT READY**

Software LCD integration, regression checks, I2C address และ diagnostic display พร้อมตามหลักฐานที่มี แต่ยังต้องยืนยัน electrical compatibility, production voice-state transitions, Wi-Fi/backend error messages และ relay safety ก่อนเริ่ม Phase 7

Phase 7 ยังไม่ถูกเริ่ม และงานนี้ไม่ได้เพิ่ม LLM, agent, mains control หรือการเปลี่ยน architecture เดิม

## 15. Standalone LCD Diagnostic

เพิ่ม PlatformIO environment ชื่อ `lcd_test` ซึ่ง compile เฉพาะ `lcd_controller.cpp` และ `lcd_test_main.cpp` ไม่ initialize relay, I2S, Wi-Fi, HTTP, ASR หรือ voice pipeline

Build:

```powershell
cd "D:\lantern\Embedded System"
$env:PLATFORMIO_CORE_DIR = 'D:\lantern\.pio-core'
& "$env:USERPROFILE\.platformio\penv\Scripts\platformio.exe" run -e lcd_test
```

Upload และเปิด monitor โดยเปลี่ยน `COM5` เป็น COM port จริง:

```powershell
& "$env:USERPROFILE\.platformio\penv\Scripts\platformio.exe" run -e lcd_test -t upload --upload-port COM5
& "$env:USERPROFILE\.platformio\penv\Scripts\platformio.exe" device monitor -e lcd_test -b 115200 --port COM5
```

ผลที่คาดหวัง:

```text
LCD I2C scan: SDA=18 SCL=19 preferred=0x27
LCD I2C device found at 0x27
LCD selected at I2C address 0x27 (preferred)
LCD text line1=LANTERN TEST line2=LCD READY
```

ถ้า Serial แสดง `LCD INIT ERROR` หรือไม่พบ address ให้ตรวจ VCC/GND, SDA/SCL, voltage ของ pull-up และหมุน potentiometer contrast ทีละน้อย โดยยังไม่สรุปว่า LCD เสียจนกว่าจะยืนยัน wiring และ logic voltage แล้ว

State-cycle diagnostic สำหรับตรวจเฉพาะการแสดงผล:

```powershell
cd "D:\lantern\Embedded System"
python upload_monitor.py --environment lcd_state_test --port COM7 --mode both
```

โหมดนี้จะวน `LISTENING`, `RECORDING`, `PROCESSING`, `WIFI OFFLINE`, `LIGHT ON` และ `LIGHT OFF` ทุกประมาณ 1.5 วินาที โดยไม่ initialize relay, I2S, Wi-Fi, HTTP หรือ ASR และไม่ใช่หลักฐานว่าอุปกรณ์จริงถูกสั่งงาน
