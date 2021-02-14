<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
        <li><a href="#run">Run</a></li>
      </ul>
    </li>
    <li><a href="#Design">Design</a>
      <ul>
        <li><a href="#RFAB-V1">RFAB V1</a></li>
        <li><a href="#RFAB-V2">RFAB V2</a></li>
        <li><a href="#ACO">ACO</a></li>
      </ul>
    </li>
    <li><a href="#Operation-Report">Operation Report</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>




<!-- ABOUT THE PROJECT -->
## About The Project

Cryptocurrency Arbitrage Bot is a python-based trading system that collects real-time market data from various sets of cryptocurrency exchanges in Korea.

The bot analyzes spreads and condition of arbitrage oppotunities using its own algorithms like `basic arbitrage strategy`, `RFAB v1`, `RFAB v2`, and `ACO`.
These are further enhanced using stat analyzer that acts as a middleware between the raw data coming in and the decision tree made by algorithms that leads to actual execution of trades. 

The bot is designed in **multi-threading architecture** and **asynchronous programming** to boost up computation and the network I/O for collecting market data.


<!-- GETTING STARTED -->
## Getting Started

To get a local copy up and running follow these simple steps.

### Prerequisites

* credentials
  Before commencing, make sure you have proper API secrets for each trading exchanges that has full access to execution of trades and accounot transfer.
  Save them in file named `conf_user.ini`. Below is a demonstration of how you should align secrets in this file.
```
[KORBIT]
client_id = <client_id>
client_secret = <client_secret>
username = chungjin93@gmail.com
password = <password>

[COINONE]
access_token = <access_token>
secret_key = <secret_key>

[GOPAX]
access_token = <access_token>
secret_key = <secret_key>
```

* virtualenv for Python3.7

### Installation

* Install dependencies
   ```sh
   pip install -r requirements.txt
   ```
   
### Run
* Run RFAB Streamer
   ```sh
   python -m ./run_trade_streamer_v2.py
   ```
* Run RFAB Trader
   ```sh
   python -m ./run_risk_free_arb_bot_v4.py
   ```


<!-- USAGE EXAMPLES -->
## Design

Currently Arbitrage Bot is run with combination of RFAB V2 augemented with ACO. 
Also RFAB Streamer is added to inject real-time market data to the execution bot.



### [RFAB V1](https://drive.google.com/file/d/1YJuU0EiBG0kJD0eA1BW5LVsdTxsuxArl/view?usp=sharing)

This is the very first version of Arbitrage Strategy applied to the bot. 

Following is the lists of what has been included as a part of algorithms.

* Repetitive trading with reverse set of **arbitrage spreads**
* Decide where to pin **entry point and secondary point** as exit plan
* **Calibration** when market variation is high
* Make use of **Bollinger band** to determine extreme point

<p align="center">
  <img src="https://github.com/JinJis/arbitrage-bot/blob/master/rfab_v1_photo.png" width="350" title="hover text">
</p>

### [RFAB V2](https://drive.google.com/file/d/1Nh_9iAocirJ2eWBpoN2p3k16iius6aZ2/view?usp=sharing)

This is the next generation trading algorithm that improves performance and yields of RFAB V1 better.
Limitation found in V1 was that there were huge discrepency between the volume of target currency on other side of trading exchange.
In order to resolve few features were added,

* **Optimized Traded Spread (OTS)**
* **Individual Combination Optimization (ICO)**
* **3D Portfolio Optimization (3D PO)**

These new features allowed the bot to broaden oppotunity of trading by maxmizing unit spread and its threshold of settings dynamically.
As a result, the bot was able to execute trade on even smaller volumes of currency while maximizing profit.

<p align="center">
  <img src="https://github.com/JinJis/arbitrage-bot/blob/master/rfab_v2_photo.png" width="550" title="hover text">
</p>

### [ACO](https://drive.google.com/file/d/1UGUAO8pydmXChAib3ugcDScHtQn7QAv5/view?usp=sharing)

This is the profit optimizer whose foundation lies into backtesting of past trades. Previsouly, every trades were dependant on the static settings meaning the bot was not capable of changing its strategy of allocating assets and volumes dynamically.

With this ACO backtester, it consistently analyzes the past traded spreads and market condition and make change on settings like threshold, division, depth, min_trading_coin etc.

* **ISO (Initial Setting Optimizer)**
* **IBO (Initial Balance Optimizer)**
* **OTC (Opportunity Time Collector)**
* **IYO (Integrated Yield Optimizer)**

<p align="center">
  <img src="https://github.com/JinJis/arbitrage-bot/blob/master/aco_photo.png" width="550" title="hover text">
</p>

<!-- ROADMAP -->
## Operation Report

This is an actual operation report of Arbitrage Bot. The sample linked covers 7days of trading.
* [Report sample](https://drive.google.com/file/d/1xjSYOW4p8lAwalMFN2DVf5I_Fsfe-IyC/view?usp=sharing)

<!-- CONTACT -->
## Contact

developer: david.jeong0724@gmail.com
