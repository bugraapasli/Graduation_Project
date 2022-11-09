import time
import wiringpi
import cv2
import _thread
import numpy as np
from gpiozero import LED

lazer = LED(17) # Lazeri açıp kapatacağımız pin GPIO 17
lazer.off() #Lazeri sıfırladık

buzzer= LED(27) # Buzzeri açıp kapatacağımız pin GPIO 17
buzzer.off() #Buzzeri sıfırladık




wiringpi.wiringPiSetupGpio()
pin = 13 # Yatay eksende kontrol yapacağımız servo GPIO 13' e bağlanacak
wiringpi.pinMode(pin, wiringpi.GPIO.PWM_OUTPUT)# GPIO 13 çıkış olarak ayarlandı
wiringpi.pwmSetMode(wiringpi.GPIO.PWM_MODE_MS)# GPIO 13' ü kontrol edeceğimiz pwm sinyalin ms hassaslığında olacak şekilde ayarladık
wiringpi.pwmSetClock(192)#clock 192
wiringpi.pwmSetRange(2000)# Range 2000
vid = cv2.VideoCapture(0)# sürekli görüntü olabilmek için kamera nesnesi oluşturduk
medium_x = 0# Görüş alanına giren cismin x eksenindeki konumu. (0 -300 arası)
medium_y = 0# Görüş alanına giren cismin y eksenindeki konumu. (0 -300 arası)

blue_lower = np.array([75,201,49], np.uint8)   # Hue Low = 75 , Saturation Low = 201 , Value Low = 49
blue_upper = np.array([129,255,255], np.uint8) # Hue High = 129 , Saturation High = 255 , Value High = 255

YATAY_EKSEN_DUR = 0
sensivity = 40
Roleyi_ac = 0# Role_ac = 1 olursa lazer ve buzzer açılır 0 ise kapanır
pos_step = 1# Her döngüde motor 1 adım hareket edecek
angle = 140 # angle = 40 ise motor en sola, angle = 140 ise motor ortaya , angle = 240 ise motor en sağa dönecek

def Lazer():
    global Roleyi_ac
    while True:
        if(Roleyi_ac == 1): # bu koşula girirse buzzer ve lazer açılacak yani cisim tespit edilmiştir
            lazer.on()
            buzzer.on()
        else: # Cisim tespit edilmediği zaman lazer ve buzzer kapalı halde olacak
            lazer.off()
            buzzer.off()
def bekle():
    global pos_step
    global YATAY_EKSEN_DUR
    global medium_y
    global medium_x
    global Roleyi_ac
    global angle
    while(YATAY_EKSEN_DUR):# Cisim tespit edildiğinde bu koşula girecek ve motorlar cismi tespit edecek şekilde hareket edecek
        if medium_x > 150 + sensivity: # cisim ekranın sağındaysa motor sağa doğru dönecek
            Roleyi_ac = 0#cisim tespit edildi ama hale ateş edebileceğimiz aralıkta olmadığı için röle kapalı olacak
            angle -= pos_step# her adımda açıyı azaltacak
            if(angle < 40):# verdiğimiz pwm sinyal 0.4 ms den küçük olamaz
                angle = 40              
        elif medium_x < 150 - sensivity: # cisim ekranın solundaysa motor sala doğru dönecek
            Roleyi_ac = 0#cisim tespit edildi ama hale ateş edebileceğimiz aralıkta olmadığı için röle kapalı olacak
            angle += pos_step
            if(angle > 240):# verdiğimiz pwm sinyal 2.4 ms den büyük olamaz
                angle = 240                  
        else:
            Roleyi_ac = 1# Cisim tespit edilmiş ve tam ortalanmış ise roleyi aç lazer ve buzzer açılsın
        wiringpi.pwmWrite(pin, angle)
        #print("Coordinates: ",str(medium_x),"-",str(medium_y))
    Roleyi_ac = 0
    
    
def yatay_eksen_motor_control(): # herhangi bir cisim tespit edilmediği sırada turret sağa ve sola bu fonksiyon sayesinde dönecek
    global angle
    while True:
        while(angle<240):
            angle += 1
            bekle()# cisim tespit edildiğinde bekle fonksiyonunun içindeki while döngüsüne girer ve cismi takip etmeye başlar eğer cisim tam ortalanmışsa lazer ve buzzer çalışır
            wiringpi.pwmWrite(pin, angle)
            time.sleep(0.05) # Aşırı hızlı dönmesi sistemimizin kararsız hareket etmesine sebep olur bundan dolayı sistemi biraz yavaşlatıyoruz
            
        while(angle>40):
            angle -= 1
            bekle()
            wiringpi.pwmWrite(pin, angle)
            time.sleep(0.05)
             

print("DO NOT FORGET RUN CODE WITH SUDO")

try:
    _thread.start_new_thread( yatay_eksen_motor_control, () ) # Servonun kontrolleri bu threadde kontrol ediliyor
    _thread.start_new_thread( Lazer, () ) # Lazer ve buzzer bu threadde kontrol ediliyor
    
except: # threadlerden herhangibiri çalışmadıysa bu duruma girecek
    print ("Error : Thread Do Not Work")
    quit()




while True:
    _, frame = vid.read() # frame objesine kameradan aldığımız frame' i atadık
    frame = cv2.resize(frame, (300, 300))# aldığımız frami 300x300 boyutlarına çevirdik
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)# frami bgr den hsv moduna geçirdik
    mask = cv2.inRange(hsv, blue_lower, blue_upper)# Cismin negatif görüntüsünü bulduk
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE) # cismin kenarlarını bulduk
    
    if not contours: # eğer ekranda cisim yoksa kenarda yoktur
        YATAY_EKSEN_DUR = 0
    else:# cisim tespit edildi şimdi cismin kordinatlarını bulacağız
        contours = sorted(contours,key=lambda x:cv2.contourArea(x),reverse=True)
        for cnt in contours:
            if cv2.contourArea(cnt) > 10:# kenarın alanı 10' dan büyük ise koşula gir
                YATAY_EKSEN_DUR = 1# bekle fonksiyonu çalışmaya başlayacak motorlar cisimi takip edecek
                (x, y, w, h) = cv2.boundingRect(cnt)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)# cisimin etrafına dikdörtgen çiziliyor
                medium_x = int((x + x+w)/2)# cismin kartezyen kordinattaki x ekseni bulundu (biz yatay eksende işlem yapacağımız için bu değeri kullanacağız)
                medium_y = int((y + y+h)/2)# cismin kartezyen kordinattaki y ekseni bulundu
                break
            else:
                YATAY_EKSEN_DUR = 0# Cismin alanı 10 dan küçükse işlem yapma
                break

    cv2.imshow("frame",frame)# kameradan alınan görüntüyü ekrana göster
    key = cv2.waitKey(1)
    if key ==27:
        break
vid.release()# kakmerayı servest bırak
cv2.destroyAllWindows()# tüm pencereleri yoket
