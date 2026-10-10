import yt_dlp

url=input("YouTube URL: ")

yt_dlp.YoutubeDL({"format":"bestvideo+bestaudio/best"}).download([url])