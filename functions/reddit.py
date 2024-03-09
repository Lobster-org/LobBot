import praw
from telebot import TeleBot

reddit = praw.Reddit(client_id = 'ERPYYCDwkoJMGL4jitEK2g',
                     client_secret = 'SNsXHBiEA-A3ikV3NgVaXSofAQZveQ',
                     user_agent = 'LobBot')
def get_posts(subreddit_name, keyword, limit = 5):
    posts = []
    subreddit = reddit.subreddit(subreddit_name)
    for submission in subreddit.search(keyword, limit = limit):
        posts.append({'title': submission.title, 'url':submission.url})
    return posts

def handle_lore_command(bot: TeleBot, message, subreddit_name = 'lore'):
    command_parts = message.text.split()
    if len(command_parts) < 2:
        bot.send_message(message.chat.id, "Please specify a keyword.")
        return

    keyword = ' '.join(command_parts[1:])
    posts = get_posts(subreddit_name, keyword)

    if posts:
        response = "\n".join([f"{post['title']}\n{post['url']}" for post in posts])
    else:
        response = f"No posts found in the '{subreddit_name}' subreddit containing the keyword '{keyword}'."

    bot.send_message(message.chat.id, response)