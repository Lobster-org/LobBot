import requests
from bs4 import BeautifulSoup
from telebot import TeleBot


def searchMovie(moive_name):
    url = f"https://myflixertv.to/search/{moive_name}"
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        movie_title = [title.text.strip() for title in soup.find_all('h2',class_='film-name')]
        top_5_movies = []
        for i in range(len(movie_title)):
            top_5_movies.append(f"{i+1}. {movie_title[i]}")
        
        print(top_5_movies)
        return top_5_movies
    else:
        return None


def send_movie(bot: TeleBot, message):
    if len(message.text.split()) == 1:
        bot.reply_to(message, "Please provide the name of the movie after /movie")
    else:
        movie_name = "-".join(message.text.split(" ")[1:])
        print(movie_name)
        movie_list = searchMovie(movie_name)
        if movie_list:
            response = "\n".join(movie_list)
            bot.reply_to(message,f"Existing shows from myflixertv.to for '{movie_name}:\n{response}'")
        else:
            bot.reply_to(message,f"No shows found for {movie_name} on myflixertv.to")
