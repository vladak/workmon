[![Python checks](https://github.com/vladak/workmon/actions/workflows/python-checks.yml/badge.svg)](https://github.com/vladak/workmon/actions/workflows/python-checks.yml)

# workmon

In the beginning of the [pandemic](https://en.wikipedia.org/wiki/COVID-19), the company offices went closed rather quickly and I found myself working with my laptop placed on a piano. The initial shock held for a long time, I spent couple of months working like that. This was not good for my posture at all.

Later on, I built a very nice setup around [motorized standing desk](https://www.fully.com/standing-desks.html) with all the bells and whistles (meticulous cable management, custom oak wooden top, BenQ LED light placed on external display, IKEA pegboard next to the table to hold the essentials (like noise cancelling headphones), [Varmilo keyboard](https://en.varmilo.com/), [Grovemade desk pad](https://grovemade.com/product/matte-desk-pad/?initial=533), WiFi extender AP mounted underneath the desk, professionally framed pictures/drawings on the wall, etc.

Using this setup allowed me to be very productive, possibly more productive than in the office, to the point when I wanted to know more about how I work to make the increased [productivity levels sustainable](https://drmaciver.substack.com/p/people-dont-work-as-much-as-you-think).

When shopping around for parts of another project on [Adafruit](https://adafruit.com), I remembered an interesting presentation from GrafanaCon 2021 [WFH habits during lockdown told by Grafana](https://grafana.com/go/grafanaconline/2021/grafana-wfh-habits/) where the presenter used sensor paired with Grafana to monitor her WFH behavior w.r.t. breaks etc. This made me throw some more stuff to the Adafruit order, scavenge some parts laying around and make my own version of work habits monitoring setup.

My goal is to provide the following functionality:
  - determine the hours I work (per day/week)
    - turn on a warning that I should wrap for the day
    - send an alert if I have been working for too long in a given week (via Grafana + PagerDuty)
  - warn if I spend too much configuous time sitting/standing
    - similarly warn if I work for too long without a break
  - monitor the working environment, esp. CO2 concentration, and alert if above given threshold

## Hardware

- [ReverseTFT Feather](https://www.adafruit.com/product/5691)
- TP-link P110 smart WiFi socket
  - to detect my presence in front of the computer. This works with sufficient degree of precision because my display has the saver set just to 3 minutes.
    - while the presence could be detected in software, I wanted to avoid any changes whatsoever to the software of my company provided laptop. Other metrics such as light emitted by the display would not be as reliable.
- [US-100 Ultrasonic Distance Sensor](https://www.adafruit.com/product/4019) connected directly (soldered) to the Feather
  - to determine if the table is up/down
- iPhone headphones transparent plastic box used as a housing for the distance sensor
  - to be mounted underneath the table at the back in order not to cause measurement interference with my legs/chair etc.
- QtPy with temperature/humidity and CO2 sensors
  - publishing messages with the metrics to a MQTT topic. The Feather will subscribe to the topic and handle the values.

## Features

- The CO2 metric displayed will turn red if the value is greater than a configured threshold.
- If the table is in the same position for too long (configurable), the image will be changed and the neopixel will start blinking.
- the display is on only during certain hours (configurable)
- if the display is off, pushing any D0/D1/D2 button will turn it on for a minute.
- the table state tracking depends on the power to be on

## Setup

### TP-link P110

Install the Tapo app on a mobile phone. Register new account, remember the user ID and password as these will be necessary.

Setup the plug so that it connects to dedicated (IoT) WiFi network.

### Feather

Solder the US-100 (in UART mode) per the US-100 guide.

### Metrics (prerequisites)

- The code assumes that environmental metrics are published to a certain MQTT topic.
  - For that I use https://github.com/vladak/shield with a QtPy.
- The code takes the power consumption value from MQTT.
  - https://github.com/vladak/plug2mqtt/ is used

### Prometheus

add this section under `scrape_configs` in `/etc/prometheus/prometheus.yml`:
```yml
  - job_name: workmon
    static_configs:
      - targets: ['workmon:8111']
```

### Grafana

Assumes the Prometheus data source is already set up.

Perform the following setup on the **Grafana server**:

- Use [dashboard provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards) with [work-dashboard.json](https://github.com/vladak/workmon/blob/main/work-dashboard.json)
- Set up the service to publish annotations using the instructions on https://github.com/vladak/mq2anno

The dashboard looks like this (the values are trimmed as I have just started recording the data recently):

![work dashboard in Grafana](/img/work-dashboard.png)

## Configure

The `secrets.py` should look like this:

```yaml
secrets = {
    "SSID": "FOO",
    "password": "XYZ",
    "broker": "172.40.0.3",
    "broker_port": 1883,
    "log_level": "info",
    "mqtt_topic_env": "devices/pracovna/qtpy",
    "mqtt_topic_power": "devices/plug/pracovna",
    "mqtt_topic_distance": "devices/pracovna/featherTFT",
    "distance_threshold": 90,
    "power_threshold_watts": 35,
    "co2_threshold": 1000,
    "last_update_threshold": 60,
    "icon_paths": [
        "/images/icons8-totoro-120.bmp",
        "/images/icons8-totoro-120-umbrella.bmp",
    ],
    "table_state_dur_threshold": 1800,
    "start_hr": 8,
    "end_hr": 23,
}
```

## Install

It assumes there are 2 images in the `images` directory. It will do fine without them, however the table position alerting will resort just to blinking the diode.

With [`circup`](https://github.com/adafruit/circup/) is installed:
```
circup install -r requirements.txt
cp -R images/ *.py settings.toml /media/$USER/CIRCUITPY/
```

## Guides:

- US-100: https://learn.adafruit.com/ultrasonic-sonar-distance-sensors/python-circuitpython

## Lessons learned

- so far, with the state of CircruitPython at lest, microcontroller based projects are all about tight loops, e.g. in order to sample button pressed events. There are some actions that might shed some time from that loop, e.g. the US-100 distance reading might require up to 0.4 seconds
- due to the very dynamic nature of the microcontroller ecosystem, the workarounds for various issues are omnipresent
- it is nice to have a friend with a Dremel
- it is nice to be able to 3-D print stuff on demand
