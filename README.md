
# CHIPUP XS7320

Based on findings about new IP Camera SOC from CHIPUP China company. 

1. [Basic datasheet about XS7320](xs7320.md)
2. [FDT Extracted from existing device](dtb-xs7320/xs7320.dts)

Header structure

| Offset | Byte count  | Info | More info |
| ------------- | ------------- | ------------- | ------------- |
| 0x0  | 4 | Header magic | 0x55AA00FF 
| 0x4  | 4 | CRC of Header  | CRC is from byte 8 to 128 |
| 0x8  | 2 | ????? | ???? |
| 0x10  | 2 | ????? | ???? |
| 0x12  | 2 | Image length | With RSA Signature (Signature is 521 bytes at tail of image) |
| 0x14  | 114 | TBD | TBD | 

Boot process:

Image base address is 0x00100000 for Mini Uboot. CPU has internal BootROM which loads from flash into RAM at boot time and checks Signature and boots or fails and resets CPU.

After desoldering NAND chip - it still tries to boot itself - of course it fails. But after failing it tries to send some garbake over UART over and over again which makes me think it has somehow a recovery method like in HiSilicon Chips (HiTool). Needs to be discovered further.

** Boot message after power UP ** 

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
