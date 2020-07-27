from flask import Flask, jsonify
from operator import itemgetter
from flask_cors import CORS
import nltk
import pymongo
import math

from api.Trie import Trie

mongo_client = pymongo.MongoClient("mongodb://localhost:27017/", username='admin', password='WaSb%`L8TG2@HjV[')
mongo_db = mongo_client["SearchEngine"]
mongo_pages = mongo_db["pages"]
mongo_keys = mongo_db["keys"]
mongo_words = mongo_db["words"]
nltk.download('punkt')
nltk.download('stopwords')
stop_words=set(nltk.corpus.stopwords.words("english"))
tokenizer = nltk.tokenize.RegexpTokenizer(r'\w+')
stemmer = nltk.stem.PorterStemmer()
word_list =  mongo_words.find_one()['words']

def isEnglish(s):
    try:
        s.encode(encoding='utf-8').decode('ascii')
    except UnicodeDecodeError:
        return False
    else:
        return True

filtered_list = [word for word in word_list if not word.isnumeric() and isEnglish(word)]

def create_app(config=None):
    app = Flask(__name__)
    app.config.update(dict(DEBUG=True))
    app.config.update(config or {})
    CORS(app)

    @app.route("/autocomplete/<query>")
    def getAutoComplete(query):
        trie = Trie(filtered_list)
        return jsonify({'query':query,'results':trie.suggestions(query)})

    @app.route("/search/<query>")
    def searchEngine(query):
        try:
            tokenized_words = tokenizer.tokenize(query.lower())
            filtered_words = list(filter(lambda word: word not in stop_words, tokenized_words))
            stemmed_words = list(map(lambda word: stemmer.stem(word), filtered_words))
            N = mongo_pages.find().count()
            tfidf = []

            tf = mongo_keys.find_one({'_id': stemmed_words[0]})["stem_tf"]
            idf = math.log(N / len(tf))
            pages = {}
            for item in tf:
                for key, value in item.items():
                    pages[key] = value * idf
            tfidf.append(pages)

            for k,v in pages.items():
                v = 0.4*v + 0.6*mongo_pages.find_one({"_id":k})['pagerank']
            results = sorted(pages.items(), key=itemgetter(1), reverse=True)

            return jsonify({"query":filtered_words[0],"results":[x[0] for x in results]})
        except:
            return jsonify({"query": filtered_words[0], "results": ""})
    return app

if __name__ == "__main__":
    port = 80
    app = create_app()
    app.run(host="0.0.0.0", port=port)