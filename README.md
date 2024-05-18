# Project-LOB-STER
## Prerequistes
1. Python 3.12
2. A telegram bot token

## How to obtain bot token
1. Follow the instructions found in the following link: https://smartbotsland.com/create-edit-bot/get-token-botfather-telegram/
## How to run:
1. Clone the repo
2. Open terminal
3. Go to project directory: cd ```C:\Users\username\Documents\GitHub\LobBot>```
4. Now inside the project directory run the following command: ``` pip install -r requirements.txt ```
5. Open your prefered IDE(VSCode,PyCharm)
6. create a ```.env``` file inside your project directory
     - inside that file put the following line: ```TOKEN = "Your telegram bot token that you obtained from botfather"```
8. Run mainBot.py


# For devs only:
1. Make sure to run ```pip freeze > requirements.txt``` if you happen to add new packages to the project.
2. If you get an error with imports make sure to run ```pip install -r requirements.txt``` again to install all the packages.

