import pandas as pd
import time
import redis
from flask import current_app
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


def simkey(p):
    return 'p:smlr:%s' % p


def info(msg):
    current_app.logger.info(msg)


def get_redis():
    return redis.StrictRedis.from_url(current_app.config['REDIS_URL'])


class ContentEngine(object):

    def __init__(self):
        self.__r = None
        self.__pipe = None

    @property
    def _r(self):
        if not self.__r:
            self.__r = get_redis()
        return self.__r

    @property
    def _pipe(self):
        if not self.__pipe:
            self.__pipe = self._r.pipeline()
        return self.__pipe

    def train(self, data_source):
        start = time.time()
        info("Downloading & reading data from %s..." % data_source)
        ds = pd.read_csv(data_source)
        info("Finished. Data read in %s seconds." % (time.time() - start))

        info("Removing stale training data...")
        get_redis().flushdb()
        info("Done.")

        start = time.time()
        info("Starting training...")
        self._train(ds)
        info("Success! Engine trained in %s seconds." % (time.time() - start))

    def _train(self, ds):
        """
        Train the engine. Create a TF-IDF matrix of unigrams, bigrams, and trigrams for each product,
        then iterate through each product, computing the 100 most-similar products based on cosine similarity.
        Stops at 100 because well...how many similar products do you really need to show?
        Those similarities and their scores are stored in redis.
        :param ds: A pandas dataset containing two fields: description & id
        :return: Nothin!
        """
        tf = TfidfVectorizer(analyzer='word', ngram_range=(1, 3), min_df=0, stop_words='english')
        tfidf_matrix = tf.fit_transform(ds['description'])
        for idx, row in ds.iterrows():
            cosine_similarities = linear_kernel(tfidf_matrix[idx:idx + 1], tfidf_matrix).flatten()
            similar_indices = cosine_similarities.argsort()[:-100:-1]
            similar_items = [(cosine_similarities[i], ds['id'][i]) for i in similar_indices]
            flattened = sum(similar_items[1:], ())  # remove first item because it is identical
            self._r.zadd(simkey(row['id']), *flattened)

    def predict(self, item_id, num):
        """
        Couldn't be simpler! Just retrieves the similar items and their 'score' from redis.
        :param item_id: string
        :param num: number of similar items to return
        :return: A list of lists like: [["19", 0.2203], ["494", 0.1693], ...]. The first item in each sub-list is
        the item ID and the second is the similarity score. Sorted by similarity score, descending.
        """
        return self._r.zrange(simkey(item_id), 0, num-1, withscores=True, desc=True)


content_engine = ContentEngine()