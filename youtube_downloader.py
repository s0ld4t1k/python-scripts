import yt_dlp

def get_formats(url):
    ydl_opts={'listformats':True}
    with yt_dlp.YoutubeDL(ydl_opts)as ydl:
        ydl.extract_info(url,download=False)

def download(url,format_id):
    ydl_opts={'format':format_id}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

if __name__=='__main__':

    url=input("YouTube URL: ")

    print("\nGetting available formats...")
    get_formats(url)

    chosen_format=input("\nEnter the format id ex. 22, 137+140 or Enter for best: ").strip()
    if chosen_format=="":
        chosen_format="bestvideo+bestaudio/best"

    print("\nDownloading...")
    download(url,chosen_format)
    print("\nDownload completed!")
    
