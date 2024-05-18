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


def searchAnime(anime_name):
    url = f"https://www.crunchyroll.com/search?q={anime_name}"
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content,"html.parser")
        anime_title = [data_t.text.strip() for data_t in soup.findAll('h4',class_="text--gq6o- text--is-semibold--AHOYN text--is-l--iccTo search-show-card-hover__title--9ZRTG")]
        anime = []
        for i in range(len(anime_title)):
            anime.append(f"{i+1}.{anime_title[i]}")
        print(anime)
        return anime
    else:
        return None
    

def send_anime(bot:TeleBot,message):
    if len(message.text.split()) == 1:
        bot.reply_to(message,"Please provide the name of the anime after /anime")
    else:
        anime_name = "%20".join(message.text.split(" ")[1:])
        print(anime_name)
        anime_list = searchAnime(anime_name)
        if anime_list:
            respone = "\n".join(anime_list)
            bot.reply_to(message,f"Exisiting shows from crunchyroll.com '{anime_name}:\n{respone}'")
        else:
            bot.reply_to(message,f"No shows found for {anime_name} on crunchyroll.com :(")

