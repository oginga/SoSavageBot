

# SoSavageBot

SoSavageBot is  twitter bot that auto-retweets a tweet's reply when mentioned.Mention me in any tweet's savage reply and I'll share the blunt with a wider twitter community.

<img src="img/mention.jpg" alt="mentions">
<hr>
<img src="img/retweeted.jpg" alt="retweeted">

## Getting Started
### Prerequisites

What things you need to install the software and how to install them

* Redis
* Python3
* Twitter developer account

## Installing

```bash
$ git clone https://github.com/oginga/SoSavageBot.git

$ cd sosavagebot
$ #Create a virtual env
$ pip3 install -r requirements.txt

```

y## Usage
The below assume a working redis installation with a running redis server ,default ports.
You can setup an auto-retweet or retweet on approval with the ```python AUTO_RETWEET=True``` flag in **savageBot.py**.
Approvals are done via the **savage_web** django app

#### 1. Add Your twitter developer API keys and tokens

```bash

$ nano /etc/environment

# ----- Add the various keys as below ------
#SAV_API_KEY='<key>'
#SAV_API_SECRET_KEY='<key>'
#SAV_ACCESS_TOKEN='<key>'
#SAV_ACCESS_TOKEN_SECRET='<key>'
#SAV_BOT_DEBUG="True"
#SAV_WEB_SECRET_KEY='<key>'
#SAV_WEB_DEBUG="True"

# -------------------------------------------
```

#### 2. Create a cron job to be fetching,processing and retweeting mentions

```bash
# Debian
$ sudo crontab -e

#Add the below line 
# */2 * * * * cd /<path to repo>/sosavagebot && /<path to virtual-env>/.virtualenvs/SS/bin/python3 /<path to repo>/savageBot.py -f

```
#### 3. Run standalone

```bash
$ python3 savageBot.py -f

# Flags
# -f -> Fetch and Retweet
# -m -> send tweet replys to mentions
# -r -> retweet approved mentions

```

## License

``` 
Copyright 2020 Oginga Steven.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License. 
```



