[![Python checks](https://github.com/vladak/workmon/actions/workflows/python-checks.yml/badge.svg)](https://github.com/vladak/workmon/actions/workflows/python-checks.yml)

# workmon

Work habits monitoring via Raspberry Pi + sensors

In the beginning of the [pandemic](https://en.wikipedia.org/wiki/COVID-19), the company offices went closed rather quickly and I found myself working with my laptop placed on a piano. The initial shock held for a long time, I spent couple of months working like that. This was not good for my posture at all.

Later on, I built a very nice setup around [motorized standing desk](https://www.fully.com/standing-desks.html) with all the bells and whistles (meticulous cable management, custom oak wooden top, BenQ LED light placed on external display, IKEA pegboard next to the table to hold the essentials (like noise cancelling headphones), [Varmilo keyboard](https://en.varmilo.com/), [Govemade desk pad](https://grovemade.com/product/matte-desk-pad/?initial=533), WiFi extender AP mounted underneath the desk, professionally framed pictures/drawings on the wall, etc.

Using this setup allowed me to be very productive, possibly more productive than in the office, to the point when I wanted to know more about how I work to make the increased [productivity levels sustainable](https://drmaciver.substack.com/p/people-dont-work-as-much-as-you-think).

When shopping around for parts of another project on [Adafruit](https://adafruit.com), I remembered an interesting presentation from GrafanaCon 2021 [WFH habits during lockdown told by Grafana](https://grafana.com/go/grafanaconline/2021/grafana-wfh-habits/) where the presenter used sensor paired with Grafana to monitor her WFH behavior w.r.t. breaks etc. This made me throw some more stuff to the Adafruit order, scavenge some parts laying around and make my own version of work habits monitoring setup.

My goal is to provide the following functionality:
  - determine the hours I work (per day/week)
    - turn on a warning light that I should wrap for the day (green)
    - send an alert if I have been working for too long in a given week (via Grafana + PagerDuty)
  - blink a warning light (orange) if I spend too much configuous time sitting/standing
    - similarly (different light color) if I work for too long without a break (red)

## Hardware

- [Raspberry Pi Zero 2 W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/) (side note: as of end of CY 2021 it is out of stock on Adafruit, can be ordered 1 piece per customer locally)
- TP-link P110 smart WiFi socket
  - to detect my presence in front of the computer. This works with sufficient degree of precision because my display has the saver set just to 3 minutes.
    - while the presence could be detected in software, I wanted to avoid any changes whatsoever to the software of my company provided laptop. Other metrics such as light emitted by the display would not be as reliable.
- [US-100 Ultrasonic Distance Sensor](https://www.adafruit.com/product/4019)
  - to determine if the table is up/down
- [Tri-Color USB Controlled Hemisphere Alarm Light](https://www.adafruit.com/product/5127) (no buzzer)
- [USB to TTL Serial Cable](https://www.adafruit.com/product/954) (for the distance sensor)
- [Waveshare 4 Port USB HUB HAT](https://www.waveshare.com/usb-hub-hat.htm)
- old iPhone 5C transparent plastic box (as a housing) with holes drilled for the distance sensor
  - to be mounted underneath the table at the back, on one of the [cable management boxes](https://www.fully.com/en-eu/accessories/wire-management/wiretamer.html) in order not to cause measurement interference with my legs etc.

## Setup

### TP-link P110

TBD

## Install

- pre-requisites:
```
sudo apt-get install -y python3-venv
sudo apt-get install -y python3-dev # for RPi.GPIO
```
- install:
```
sudo mkdir /srv
sudo apt-get install -y git
git clone https://github.com/vladak/workmon /srv/workmon
cd /srv/workmon
python3 -m venv env
. ./env/bin/activate
# workaround for RPi.GPIO install: https://raspberrypi.stackexchange.com/a/135463
export CFLAGS=-fcommon
pip install -r requirements.txt
```
- create `.env` file (make sure not to upload this folder or your `.env` file to a public repository) with `<username>` and `<password>` replaced by the actual values from the TP-link smart plug setup above:
```
USERNAME = "<username>"
PASSWORD = "<password>"
```
- configure the service: create `/srv/workmon/environment` and setup these environment variables:
  - `USERNAME`: TP-link username
  - `PASSWORD`: TP-link password
  - `ARGS`: additional `workmon.py` arguments
    - it will definitely need to contain `--hostname` with an argument (the TP-link hostname) which is required 
    - keep in mind that this is not a shell syntax so using double quotes will break argument passing
- setup the service (assumes the `pi` user)
```
  sudo cp /srv/workmon/workmon.service /etc/systemd/system/
  sudo systemctl enable workmon
  sudo systemctl daemon-reload  # in case the service file changed
  sudo systemctl start workmon
  sudo systemctl status workmon
```

## Guides:

- US-100: https://learn.adafruit.com/ultrasonic-sonar-distance-sensors/python-circuitpython
