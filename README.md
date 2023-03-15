
# CHIPUP XS7320

Based on findings about new IP Camera SOC from CHIPUP China company. 

1. [Basic datasheet about XS7320](xs7320.md)
2. [FDT Extracted from existing device](dtb-xs7320/xs7320.dts)
3. [Header Structure](#header-structure)
4. [Boot process](#boot-process)
5. [Boot log of MiniBoot](#boot-message-after-power-up)
6. [Boot after NAND desoldered](#boot-after-nand-desoldered)
7. [FACTORY_MODE - you can flash whole NAND, modify MEMORY and boot from RAM](#tbd)

### Header structure ###

| Offset | Byte count  | Info | More info |
| ------------- | ------------- | ------------- | ------------- |
| 0x0  | 4 | Header magic | 0x55AA00FF  or 0x27051956 (Uboot)
| 0x4  | 4 | CRC of Header  | CRC is from byte 8 to 128 |
| 0x8  | 2 | ????? | ???? |
| 0x0C  | 4 | Payloadsize  | In hex Big Endian, it later adds 776 bytes extra to this value and loads into memory |
| 0x10  | 2 | Load from address (in device) | Address in source device to load from (adds to it offset of heeader 0x80) |
| 0x14  | 4 | Load Address | 0x100000 Big Endian |
| 0x18  | 4 | Data CRC | Used when RSA check is not enabled | 
| 0x20  | 4 | Offset of next boot image in flash | It will try to skip there if loading fails |
| 0x40  | 4 | Loader Type | 0x4 - means SPINAND, 0x2 - SPINOR, 0x8 - EMMC |
| 0x44  | 4 | Sign Type | 0x02 means CRC check, 0x03 means RSA check with Sign at the end of image |

### Boot process ###

Image base address is 0x00100000 for Mini Uboot. CPU has internal BootROM which loads from flash into RAM at boot time and checks Signature and boots or fails and resets CPU.

After desoldering NAND chip - it still tries to boot itself - of course it fails. But after failing it tries to send some garbake over UART over and over again.

### Serial speed negotiation

At the end of fail boot we can see a garbage over serial line. This is not garbage. BootROM tries to change baudrate starting from 750k through 500k, 375k and lower ones and sends magic packet at selected speed 0x0
This is a serial speed negotiation which SOC tries to do to put FACTORY_MODE speed at higher baud rate than default 115200k

Scenario is as follows:
Set UART speed to 750k, send bytes 0x025A0003 and waits for 100ms for response 0x02A50003. If it recicves, this bytes, it will setup this baudrate and try to boot again using FACTORY_MODE. This mode will be written later. If it not recives magic bytes, it lowers speed, send again and wait for answer. If no answer is recived, it stays at 115200k and tries to boot FACTORY_MODE again.

### Boot process from power-on

*1st Stage (CPU BOOTROM)*
1. After power-up camera, CPU boots from Internat Bootrom stored at 0x0, Internal RAM is 64k in size.
2. At this stage it tries to load 256 bytes from every device it supports until it finds a magic header
3. Order of devices is SPINAND, SPINOR, eMMC.
4. It searches for Magic 0xff00AA55 bytes and then checks RSA signature of this image
5. Then it is loaded to internat RAM at 0x100000 and then Jumps there.
6. At this level Nand Flash starts at 0x40000000

*2nd Stage (Vendor)*
1. It starts at addres 0x100000 and initializes DDR, serial, and IRQ
2. Then remaps NAND to 0x0 and disables internat bootrom and SRAM
3. Memory is mapped at 0x10000000 and limited to 256Mbytes
4. It searches for 3rd stage (Uboot in my situation) and loads it at 0x12000000
5. It jumps there

*3rd Stage* 
1. It starts Uboot at 0x12000000 and continues from there


### FACTORY MODE ###

Device has internal, BOOTROM recovery procedure like in HiSilicon SoC. It uses UART as a debug interface to modify memory in-place or flash NAND/NOR/eMMC memory without having working bootloader. It uses pack of hex commands to do the job. Using UART speed negtiation, you can negotiate faster speeds instead of 115200 kbits to gain speed in flashing big images (like Kernel).

Mechanism works as follows (all data are hex-bytes).

1. At power ON it sends magic packet `0x02140003` and waits for 100ms for a response packet `0x02240003` to enter Factory Mode. If no packet is recived, it starts normal BOOTROM 1st stage boot process.

2. After it recieves this packets, it enters Factory Mode and stays there waiting for special 4-byte commands.
3. Commands are:

    `0x18` - Upload data to specified address in memory
  
    `0x19` - Set memory at address to specified 4-byte value
  
    `0x1A` - Dump memory at address with n-count 4-byte data
  
    `0x45` - Erase Flash (Supports NAND, SPI and eMMC)
  
    `0x1D` - Program Flash at specified addres by page-size at a time
  
4. Structure of commands:


### Boot message after power UP ###

```
$Tch SpiNand
Load 0x00000080 to 0x00100000,size=30332
Key hash pass!
Imgsign pass
Jmp 0x00100000

Info: write leveling start
Info: write leveling done

Info: dqs gating start
Info: dqs gating done

Info: read train start
Info: bypass read train done

Info: write train start
ddr init done

simple ddr test
swap
ddr_clk: 599500
cpu_clk: 1000000
enc_clk: 400000

DDR32bit done!

B: Apr 21 2022 21:22:02
chip id is 0x0x7FB3804C
mac io keep 3.3v 
PreImgHeaderBase = 0x0010FE78
SpiNand : Scan Uimg @0x00100000
use 2 plane to read
Load 0x00100040 to 0x12000000,size=220208
rdbuf 131072 131072
SMC_loadPartition ReadPage ret 0
SMC_init crc done, start_addr 0x00200000 size 0x0000159C crc 0xE0132685
SmcReadNandID id = 0x142C142C
SMC_nandInit set MICRON F50L1G41XA, id 0x0000002C 0x00000014
SMC_init done
Jmp 0x12000000
```

### Boot after NAND desoldered ###
```
Tch SpiNand
Tch SpiNor
dwmci_send_cmd: Timeout.
Mmc:Init failed!
DScan SpiNand
scan blk : 64
Image flag error! read=0x00000000
scan blk : 128
Image flag error! read=0x00000000
scan blk : 192
Image flag error! read=0x00000000
scan blk : 256
Image flag error! read=0x00000000
scan blk : 320
Image flag error! read=0x00000000
scan blk : 384
Image flag error! read=0x00000000
scan blk : 448
Image flag error! read=0x00000000
scan blk : 512
Image flag error! read=0x00000000
scan blk : 576
Image flag error! read=0x00000000
scan blk : 640
Image flag error! read=0x00000000
scan blk : 704
Image flag error! read=0x00000000
scan blk : 768
Image flag error! read=0x00000000
scan blk : 832
Image flag error! read=0x00000000
scan blk : 896
Image flag error! read=0x00000000
scan blk : 960
Image flag error! read=0x00000000
scan blk : 1024
Image flag error! read=0x00000000
DScan fail!
DScan SpiNor
Image flag error! read=0xFFFFFFFF
DScan fail!
DScan Mmc
DScan fail!
Load image header falied!
(Serial Negotiation bytes - check Serial Negotiation topic)
```
