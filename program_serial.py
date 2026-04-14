"""
Uart programmer for ChipUP XS7320
a) 1st Stage (Vendor BOOTROM)
	1. After power-up camera, CPU boots from Internat Bootrom stored at 0x0, Internal RAM is 64k in size.
	2. At this stage it tries to load 256 bytes from every device it supports until it finds a magic header
	3. Order of devices is SPINAND, SPINOR, eMMC.
	4. It searches for Magic 0xff00AA55 bytes and then checks RSA signature of this image
	5. Then it is loaded to internat RAM at 0x100000 and then Jumps there.
	6. At this level Nand Flash starts at 0x40000000
2) 2nd Stage (Vendor)
	1. It starts at addres 0x100000 and initializes DDR, serial, and IRQ
	2. Then remaps NAND to 0x0 and disables internat bootrom and SRAM
	3. Memory is mapped at 0x10000000 and limited to 256Mbytes
	4. It searches for 3td stage (Uboot in my situation) and loads it at 0x12000000
	5. It jumps there
3) 3rd Stage 
	1. It starts Uboot at 0x12000000 and contoinues from there
	
	
UART recovery procedure
1. At power ON it sends magic packet 0x02140003 and waits for 100ms for a response packet 0x02240003 to enter Factory Mode.
2. After it recieves this packets, it enters Factory Mode and stays there waiting for special 4-byte commands.
3. Commands are:
	0x18 - Upload data to specified address in memory
	0x19 - Set memory at address to specified 4-byte value
	0x1A - Dump memory at address with n-count 4-byte data
	0x45 - Erase Flash (Supports NAND, SPI and eMMC)
	0x1D - Program Flash at specified addres by page-size at a time
4. Structure of commands:

"""
import serial
import sys
import os
import time
import binascii
import collections
q = collections.deque(maxlen=4)

ser = serial.Serial()
ser.baudrate = 115200
ser.port = 'COM4'
ser.open()

#Temp buffer for Uart data 4-bytes
uart_buff = bytearray([0x00,0x00,0x00,0x00])
q.append(0x0)
q.append(0x0)
q.append(0x0)
q.append(0x0)

TEST_BAUD = bytearray([0x02,0x5a,0x00,0x03])
TEST_230400 = bytearray([0x02,0xda,0x00,0x03])
FALIED = bytearray([0x69,0x65,0x64,0x21]) #na koncu wysyla FALIED (celowy blad) po nim leca dane, uzyjemy do przelczenia na hexy
DEBUG_ENABLE = bytearray([0x02,0x14,0x00,0x03])
OK = bytearray([0x02,0x05,0x00,0x03])
ERROR = bytearray([0x02,0x0A,0x00,0x03])
magic = bytearray([0x02,0x24,0x00,0x03])
isHex = True

def dq2buf():
	for x in range(0,4): 
		uart_buff[x] = q[x]
	
def is_ascii(s):
	c=s
	
	if (c>31 and c<128 and c!=0x24): #taki hack na znak dolara
		return True
	if (c==12 or c==14 or c == 0x0d or c == 0x0a): #new line
		return True
	return False
    

def senddata(bytes,output):
	if (output==True):
		sys.stdout.write("TX: 0x");
		print(bytes) # + " ("+str(time.time())+")")
	b = bytearray()
	ser.write(b.fromhex(bytes))
	
def calcChksum(data,start):
	b = bytearray()
	x = sum(b.fromhex(data),start) & 0xFF 
	return x
	
def readdata(length,output):
	line = ser.read(length)
	
	if (output==True):
		int_val = int(line.encode('hex'), 16)
		if (is_ascii(int_val) and isHex == False): #is printable
			sys.stdout.write(line)
		else:
			sys.stdout.write("RX: 0x" + line.encode('hex') + "\n")
		
			
	b = bytearray()
	b.extend(line)
	for x in range(0,length): 
		q.append(b[x])
	dq2buf()
	return b
	
def dumpmem(addr,ile): 
	#Zrzuca pamiec pod adresem addr, i ile DWRODOW (4bajty) ma zrzucic
	x = calcChksum("{:08x}".format(addr),0) #Adres pamieci
	x = calcChksum("{:08x}".format(ile),x) #ilosc 4 bajtowych blokow do odczytania
	senddata("021A{:02x}03".format(x),False) 
	senddata("{:08x}".format(addr),False)
	senddata("{:08x}".format(ile),False)
	l = readdata(4,False) #odpowiedz 021AXX03 - gdzie XX to CRC
	for x in range(ile):
		sys.stdout.write("A: {:08x} ".format(addr+4*x))
		l = readdata(4,True) #odpowiedz 021AXX03 - gdzie XX to CRC
		t = l
	l = readdata(4,False) #odpowiedz 021AXX03 - gdzie XX to CRC
	return t
	
def dumpmemone(addr): 
	ile = 1
	#Zrzuca pamiec pod adresem addr, i ile DWRODOW (4bajty) ma zrzucic
	x = calcChksum(addr,0) #Adres pamieci
	x = calcChksum("{:08x}".format(ile),x) #ilosc 4 bajtowych blokow do odczytania
	senddata("021A{:02x}03".format(x),False) 
	senddata(addr,False)
	senddata("{:08x}".format(ile),False)
	l = readdata(4,False) #odpowiedz 021AXX03 - gdzie XX to CRC
	#sys.stdout.write("A: {:08x} ".format(addr+4*x))
	l = readdata(4,True) #odpowiedz 021AXX03 - gdzie XX to CRC
	t = l
	l = readdata(4,False) #odpowiedz 021AXX03 - gdzie XX to CRC
	#l = readdata(4) #odpowiedz 021AXX03 - gdzie XX to CRC
	return t

def setmemory(addr,value):
	#Ustawia wartosc pod adresem addr na value (DWORD
	x = calcChksum("{:08x}".format(addr),0) #Adres pamieci
	x = calcChksum("{:08x}".format(value),x) #ilosc 4 bajtowych blokow do zapisania
	senddata("0219{:02x}03".format(x),False) #zapisuje pod adresem cmd1, wartosc z pakietu cmd2
	senddata("{:08x}".format(addr),False)
	senddata("{:08x}".format(value),False)
	l = readdata(4,False) # odpowiedz w postaci OK
	
	#15-07-1986
def eraseblock(offset):
	#TODO - dorobic prawidlowo offset
	#0x45 - erase block
	# parametr 1 to offset np 0x40040000
	#parametr 2 to ilosc blokow po 0x20000 to do wyczysczenia
	offset_base=0x40000000
	offset=offset_base+(0x20000*offset)
	# kasuje caly erase block 0x20000 czyli 131072 bajty!!!!
	x = calcChksum("{:08x}".format(offset),0) #Adres pamieci
	x = calcChksum("00000001",x) #ilosc 4 bajtowych blokow do zapisania
	senddata("0245{:02x}03".format(x),False) #zapisuje pod adresem cmd1, wartosc z pakietu cmd2
	senddata("{:08x}".format(offset),False)
	senddata("00000001",False)
	l = readdata(4,False) # odpowiedz w postaci OK
	if (l!=OK):
		raise Exception("eraseblock response error")
		exit(1)
	
def bootfromaddr(addr):
	#Dziala, done
	x = calcChksum("{:08x}".format(addr),0)
	senddata("021B{:02x}03".format(x),False) #zapisuje pod adresem cmd1, wartosc z pakietu cmd2
	senddata("{:08x}".format(addr),False)
		
def memoryboot(filename,offset):
	#Dziala, done x adresu 0x100000
	buffer_addr=offset
	file_stats = os.stat(filename)
	size = file_stats.st_size;
	if (size == 0):
		print("Filesize is zero!!!!")
		exit()
	
	f = open(filename, "rb")
	packcount=4 #how much 4-bytes packets to program at once
	total = 0
	i=0
	crc=0
	w = open("boot.uart.cpy2", "wb")
	while (total != size):
		crc = 0
		i=0
		while (i < packcount):
			byte = f.read(4)
			crc = calcChksum(byte.encode('hex'),crc)
			i+=1
		#Mamy zliczone CRC 4 bajtow
		#Dodajemy CRC parametrow
		crc = calcChksum("{:08x}".format(buffer_addr),crc)
		crc = calcChksum("{:08x}".format(packcount),crc)
		
		#Wysylamy dane
		senddata("0218{:02x}03".format(crc),False) #zapisuje pod adresem cmd1, wartosc z pakietu cmd2
		senddata("{:08x}".format(buffer_addr),False)
		senddata("{:08x}".format(packcount),False)
		i=0
		f.seek(total)
		while (i < packcount):
			byte = f.read(4)
			w.write(byte)
			senddata(byte.encode('hex'),False)
			i+=1
		
		l = readdata(4,False)
		if (l!=OK):
			raise Exception("program address {:08x} response error".format(x))
			exit(1)
		buffer_addr+=packcount*4
		
		total+=(packcount*4)
		#if (total > 0x800): #Mozna programowac strone po 2048 bajtow, potem trzeba podniesc indeks strony na kolejny
		#	dumpmem(0x400000e0,64)
		#	exit()
		


def programfilev2_sendpack(buf,page,flashoffset):
	
	baseoffset=0x40000000
	size=len(buf)
	packidx=0
	idx=0
	if (len(buf) < 2048):
		#pad to 2048 bytes using zeros
		#print("pad to 2048");
		buf=buf.ljust(2048,chr(0x00))
		size=len(buf)
	
	#Teraz podzielmy to na 4x64 paczki i wio	
	while (idx != size):
		byte256 = buf[idx:idx+256]
		programfilev2_transmitpack(idx,byte256)
		idx+=256
	#Wyslane do RAMu cale 2048 bajtow
	addr=baseoffset+flashoffset+(page*0x800) #offset w pamieci wewnetrznej, 0x200000 to bedzie 0x40200000 itd
	x = calcChksum("{:08x}".format(addr),0) #Adres pamieci
	x = calcChksum("{:08x}".format(2048),x) #ilosc 4 bajtowych blokow do zapisania
		
	senddata("021D{:02x}03".format(x),False) #zapisuje pod adresem cmd1, ilosc danych podanych przez cmd2
	senddata("{:08x}".format(addr),False)
	senddata("{:08x}".format(2048),False)
	l = readdata(4,False) # odpowiedz w postaci OK
	if (l!=OK):
		raise Exception("programfilev2_sendpack {:08x} response error".format(addr))
		exit(1)
		
def programfilev2_transmitpack(offset,buf):

	buffer_addr=0x10D004
	#Inkrementujemy adres w pamieci od ilosc 256 bajtowych blokow

	buffer_addr=buffer_addr+(offset)
	crc = 0
	crc = calcChksum("{:08x}".format(buffer_addr),crc)
	crc = calcChksum("{:08x}".format(64),crc)
	crc = calcChksum(buf.encode('hex'),crc)
		
	#Wysylamy dane
	senddata("0218{:02x}03".format(crc),False) #zapisuje pod adresem cmd1, wartosc z pakietu cmd2
	senddata("{:08x}".format(buffer_addr),False)
	senddata("{:08x}".format(64),False)
	idx=0
	while (idx < 256):
		byte = buf[idx:idx+4]
		senddata(byte.encode('hex'),False)
		idx+=4
		
	l = readdata(4,False)

	if (l!=OK):
		raise Exception("program loaddata {:08x} response error".format(buffer_addr))
		exit(1)
			
	

		
def programfilev2(filename,flashoffset):
	
	
	file_stats = os.stat(filename)
	size = file_stats.st_size;
	if (size == 0):
		print("Filesize is zero!!!!")
		exit()
	#trzeba sprawdzic jeszcze offset aby wyczyscic pamiec
	#eraseblock dziala na stronach po 0x20000 bajtow
	#liczymy start
	eraseblock_start=flashoffset / 0x20000
	eraseblock_count=(size / 131072) + 1 # + 1 because we need to erase next block also if not full programm for this block
	eraseblock_end = eraseblock_start + eraseblock_count
	if (eraseblock_count == 0):
		print("Eraseblock count is zero!. Exiting.")
		exit()
	#Erasing flash to make place for data
	for n in range(eraseblock_start,eraseblock_end):
		print("Erasing block {0:n}".format(n))
		eraseblock(n)
		
	
	f = open(filename, "rb")
	total = 0
	page=0
	pagesize=2048
	while (total != size):
		buffer = f.read(2048)
		readlen = len(buffer)
		programfilev2_sendpack(buffer,page,flashoffset)
		total = total + readlen
		sys.stdout.write("\rProgramowanie: {0:n} z {1:n} bajtow".format(total,size)) 
		page+=1
		
		
UARTneg = False	
#Glowna petla
while True:
		l = readdata(1,False)
		t = ''.join('{:02X}'.format(x) for x in uart_buff)
		
		
		if (t == "025A0003"):
			print("Wynegocjonwany Baudrate 375K!");
			senddata("02A50003",True)
			
			
			
		
		if (uart_buff == magic):
			isHex = False
			sys.stdout.write("Odebrano pakiet DEBUG. Jedziemy...")
			senddata("02140003",False) #Wysylamy pakiet Startowy
			l = readdata(4,True)
			#eraseblock(0)
			#exit()
			#dumpmem(0x10A0000,16)
			programfilev2("boot.1st.bin",0x0)
			programfilev2("boot.2nd.bin",0x100000)
			programfilev2("kernel.img.bin",0x6600000)
			print("Zakonczono. Odepnij serial i rebotnij kamere. Reszta przez TFTP.")
			exit()
			#setmemory(0x10A0000,0x0e)
			#setmemory(0x10A0004,0x0)
			#setmemory(0x10A000C,0x3)
			
		
		if (uart_buff == FALIED):
			
			print("Rozpoczeto negocjacje predkosci");
			#UARTneg = True
			#while True:
			#	l = readdata(4,False)
				#print("{:08x}".format(uart_buff))
			"""
			if (l!=OK):
				raise Exception("Odebrany pakiet DEBUG jest nieprawidlowy")
				exit()
			"""
			#eraseblock(0)
			#exit()
			
				
			#programfilev2("smc.bin",0x200000)
			#programfilev2("kernel.img.new.source",0x6600000)
			
			
			#testy czyszczenia pamieci
			
			#eraseblock(0)
			#0x40100000 zwroci dane z offsetu 100000 ale 0x40200000 juz nie, co jest kurwa
			#dumpmem(0x40000003,64)
			#programfilev2("bootloader.newhead",0x100000)
			
			#dumpmem(0x40000001,64)
			#dumpmem(0x40000002,64)
			#exit()
			#programfile("boot.uart",0x0)
			
			
			#Bootowanie z pamieci - dziala
			"""
			memoryboot("boot.uart",0x100000)
			bootfromaddr(0x100000)
			"""
			#if (uart_buff == FALIED):
			#	isHex = True
		
		#ser.close()

exit()
#Komendy bajt0 i bajt3 zawsze 0x02 i 0x03
#bajt 1 to komenda 
#bajt 2 - to komenda (suma kontrolna??)
#02 14 00 03 - pakiet init odsyla wtedy 02 05 00 03
#02 0a 00 03 - error
#02 65 00 03 - wychodzi z bootwania przez uart i kontunnuje botowanie

#bajt 0 zawsze 02 i ostatni 03
#bajt 1 to komenda
#bajt 2 to co????
