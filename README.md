# workmon

Work habits monitoring via Raspberry Pi + sensors

In the beginning of the [pandemic](https://en.wikipedia.org/wiki/COVID-19), the company offices went closed rather quickly and I found myself working with my laptop placed on a piano. The initial shock held for a long time, I spent couple of months working like that. This was not good for my posture at all.

Later on, I built a very nice setup around [motorized standing desk](https://www.fully.com/standing-desks.html) with all the bells and whistles (meticulous cable management, custom oak wooden top, BenQ LED light placed on external display, IKEA pegboard next to the table to hold the essentials like noise cancelling headphones, [Varmilo keyboard](https://en.varmilo.com/), [Govemade desk pad](https://grovemade.com/product/matte-desk-pad/?initial=533)), WiFi extender AP mounted underneath the desk, professionally framed pictures/drawings on the wall, etc.

Using this setup allowed me to be very productive, possibly more productive than in the office, to the point when I wanted to know more about how I work to make the increased productivity levels sustainable.

When shopping around for parts of another project on [Adafruit](https://adafruit.com), I remembered an interesting presentation from GrafanaCon 2021 [WFH habits during lockdown told by Grafana](https://grafana.com/go/grafanaconline/2021/grafana-wfh-habits/) where the presenter used sensor paired with Grafana to monitor her WFH behavior w.r.t. breaks etc. This made me throw some more stuff to the Adafruit order, scavenge some parts laying around and make my own version of work habits monitoring setup.

My goal is to provide the following functionality:
  - determine the hours I work (per day/week)
    - turn on a warning light that I should wrap for the day
    - send an alert if I have been working for too long in a given week (via Grafana + PagerDuty)
  - turn on a warning light if I spend too much configuous time sitting/standing
    - similarly (different light color) if I work for too long without a break

## Hardware

- [Raspberry Pi Zero 2 W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/) (side note: as of end of CY 2021 it is out of stock on Adafruit, can be ordered 1 piece per customer locally)
- [RPIZ CT3V1 HAT](http://lechacal.com/wiki/index.php?title=RPIZ_CT3V1) with Current sensors
  - to detect my presence in front of the computer. This works with sufficient degree of precision because my display has the saver set just to 3 minutes.
    - while the presence could be detected in software, I wanted to avoid any changes whatsover to the software of my company provided laptop. Other metrics such as light emitted by the display would not be as reliable.
- [US-100 Ultrasonic Distance Sensor](https://www.adafruit.com/product/4019)
  - to determine if the table is up/down
- [SCT013](https://www.poweruc.pl/products/split-core-current-transformer-sct013-rated-input-5a-100a?_pos=2&_sid=1684a3985&_ss=r) non invasive Current sensor
- [Tri-Color USB Controlled Hemisphere Alarm Light](https://www.adafruit.com/product/5127)
- [USB to TTL Serial Cable](https://www.adafruit.com/product/954)
- old iPhone 5C transparent plastic box (as a housing)
  - to be mounted underneath the table at the back, on one of the cable management boxes in order not to cause measurement interference with my legs etc.

## Setup

- enable serial port for the Current sensor:
  - run `sudo raspi-config`
    - go to 'Interfaces menu', select 'Serial port', choose the options so that it ends up like this:
```
The serial login shell is disabled
The serial interface is enabled
```
- disable Bluetooth:
```
echo "dtoverlay=disable-bt" | sudo tee -a /boot/config.txt
sudo systemctl disable hciuart
sudo reboot
```
- test the reading:
```
stty -echo -F /dev/ttyAMA0 raw speed 38400
cat /dev/ttyAMA0
```
