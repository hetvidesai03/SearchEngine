# -*- coding: utf-8 -*-
import traceback
import urllib.parse
import requests
import nltk
import pymongo
import time
from bs4 import BeautifulSoup
from bs4.element import Comment

nltk.download('punkt')
nltk.download('stopwords')
stop_words=set(nltk.corpus.stopwords.words("english"))
tokenizer = nltk.tokenize.RegexpTokenizer(r'\w+')
stemmer = nltk.stem.PorterStemmer()

mongo_client = pymongo.MongoClient("mongodb://localhost:27017/",username='admin', password ='WaSb%`L8TG2@HjV[')
mongo_db = mongo_client["SearchEngine"]
mongo_pages = mongo_db["pages"]
mongo_keys = mongo_db["keys"]
mongo_words = mongo_db["words"]
word_list = set()
crawled_links = []
links_queue = ['https://uwindsor.ca/']

def saveToDB(url,link_list,key_list):
    page  = {"_id":url, "links":link_list,"pagerank":1,"time":time.time()}
    pg = mongo_pages.insert_one(page)
    for key,val in key_list.items():
        try:
            mongo_keys.update_one({"_id":key},{ "$addToSet": { "stem_tf": {url:val} }},upsert=True)
        except:
            pass

def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True
def parse(url):
    global links_queue
    global crawled_links
    global word_list
    print("Handling: " + url)
    crawled_links.append(url)
    headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=(5, 10))
    except Exception as e:
        print("Crawl Error "+url)
        return False

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'lxml')
        links = list(dict.fromkeys([urllib.parse.urljoin(url, link.get('href')) for link in soup.find_all('a')]))
        links = list(filter(lambda ele:ele[:4] in ['http','ftp:'],links))
        links_queue = links_queue + links
        visible_text_lines = filter(tag_visible, soup.findAll(text=True))
        text = u" ".join(t.strip() for t in visible_text_lines)
        tokenized_words=tokenizer.tokenize(text.lower())

        filtered_words = list(filter(lambda word: word not in stop_words, tokenized_words))
        stemmed_words = list(map(lambda word: stemmer.stem(word),filtered_words))
        freq_dist = nltk.probability.FreqDist(stemmed_words)
        word_list.update(filtered_words)
        total_words = len(stemmed_words)
        tf = {k:v/total_words for k,v in freq_dist.items()}
        saveToDB(url,links,tf)

while links_queue:
    link = links_queue.pop(0)
    if len(word_list) >= 5000:
        try:
            mongo_words.update_one({"_id":"wordlist"},{ "$addToSet": { "words": {"$each":list(word_list)} }},upsert=True)
            word_list.clear()
        except Exception:
            print("word write error")
            print(traceback.format_exc())
    if link not in crawled_links and not link.endswith(".pdf"):
        try:
            parse(link)
        except Exception:
            print("page parse error")
            print(traceback.format_exc())