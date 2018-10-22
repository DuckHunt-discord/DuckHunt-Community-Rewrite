import collections
import json
import os
import random
import time
import unicodedata

import logging

import itertools
import requests
from tqdm import tqdm

from cogs.helpers.context import CustomContext


class WordNotFoundInCorpus(Exception):
    pass


class BaseCorpus:
    def __init__(self, logger=logging):
        self.depth = 3
        self.name = "base"
        self.logger = logger


    @property
    def model(self) -> dict:
        # In subclasses, you'd have to do something so that we can use the model with self.model
        return None

    @model.setter
    def model(self, value):
        self._model = value

    @model.deleter
    def model(self):
        pass

    def create_markov(self, sentences: list, limit=1000000) -> dict:
        start_time = time.time()

        model = collections.defaultdict(collections.Counter)    

        for sentence in tqdm(random.sample(sentences, limit), desc="Processing corpus into the model"):
            splitted = [''] * (self.depth - 1) + sentence.split() + ['__END__']

            for i in range(len(splitted) - self.depth):
                words_current = tuple(splitted[i:i+self.depth])
                word_next = splitted[i+self.depth]

                model[words_current][word_next] += 1

        model = dict(model)

        end_time = time.time()
        self.logger.debug(f"Processing the corpus into the model took {round(end_time-start_time, 3)}s")

        # logging.debug("Saving model to cache!")

        # start_time = time.time()
        # with open(self.name + '.modelcache', 'wb') as f:
        #     pickle.dump(model, f)

        # end_time = time.time()

        # logging.debug(f"Saved in {round(end_time-start_time, 3)}s!")

        return model

    def make_sentence_with_start(self, start: str) -> str:
        current = collections.deque(maxlen=self.depth)
        start_list = start.strip().split()

        current.extend([''] * (self.depth - len(current)))

        current.extend(start_list)

        total = start_list[:]

        while current[-1] != "__END__":
            try:
                possibilites_counter = self.model[tuple(current)]
            except KeyError:
                raise WordNotFoundInCorpus(f"Word(s) {list(current)} not found in corpus")

            s = sum(possibilites_counter.values())

            self.logger.debug(f"[Make sentence]\n  > [current] = {list(current)}\n  > [possibilities] = {possibilites_counter.most_common(5)}(...) -> Total weight {s} \n  > [total] = {total}")

            if s == 0:
                raise Exception
                #  next_word = "__END__"  # Didn't find the word in the corpus
            else:
                i = random.randrange(s)
                next_word = next(itertools.islice(possibilites_counter.elements(), i, None))

            current.append(next_word)
            total.append(next_word)

        string = " ".join(total[:-1]).capitalize() + "."
        return string


class DuckHuntCorpus(BaseCorpus):
    def __init__(self, logger=None):
        super().__init__(logger)
        self.name = 'DuckHunt'
        self.url = 'http://duckhunt.api-d.com/messages.txt'
        self._model = None
        self.logger = logger

    @property
    def model(self):
        if self._model is None:
            # Corpus Cache ?
            fname = self.name + '.corpuscache'
            if os.path.isfile(fname) and time.time() - os.path.getmtime(fname) < 3600:  # Cache will expire after an hour
                #r = input("No corpus loaded, use cache [Y/n] >")
                r = 'y'

                if r.lower() == 'n':
                    corpus = self.process_corpus(self.download())
                else:
                    start_time = time.time()
                    with open(fname, 'r') as f:
                        corpus = json.load(f)

                    end_time = time.time()
                    self.logger.debug(f"Loading the corpus from cache took {round(end_time-start_time, 3)}s")
            else:
                corpus = self.process_corpus(self.download())
            self._model = self.create_markov(corpus)

        return self._model

    @model.setter
    def model(self, value):
        self._model = value

    @model.deleter
    def model(self):
        if self._model:
            self._model = None

    def update(self):
        del self.model

    def download(self) -> requests.Response:
        """
        Download the corpus with a progress bar shown to the user
        :return:
        """
        # Streaming, so we can iterate over the response.
        r = requests.get(self.url, stream=True)

        return r

    def process_corpus(self, file: requests.Response) -> list:

        start_length = 0
        start_time = time.time()

        lines_parsed = []

        for line in tqdm(file.iter_lines(), desc="Downloading and processing text corpus"):
            start_length += 1
            line = line.decode()
            message = line.lower().strip()
            try:
                message_ = unicodedata.normalize('NFKD', message)

            except:
                message_ = message

            if message_ is None:
                message_ = message

            message = message_

            message = unicodedata.normalize('NFKD', message)

            if len(message) < 2:
                continue

            if message.startswith('dh'):
                continue

            if any([x in message for x in ['nigga', 'http', 'discord.gg', 'fuck', 'hentai']]):
                continue

            splitted = message.split()

            if len(splitted) < self.depth:
                continue

            for word in splitted:
                if len(word) > 15:
                    break
            else:
                lines_parsed.append(message)

        lines_parsed = sorted(lines_parsed)

        end_length = len(lines_parsed)
        end_time = time.time()

        self.logger.debug(f"Fixing the corpus text took {round(end_time-start_time, 3)}s, and the corpus was trimmed from {start_length} to {end_length} lines (diff: {end_length-start_length})")

        self.logger.debug("Saving corpus to cache!")

        start_time = time.time()
        with open(self.name + '.corpuscache', 'w') as f:
            json.dump(lines_parsed, f)

        end_time = time.time()

        self.logger.debug(f"Saved in {round(end_time-start_time, 3)}s!")

        return lines_parsed


class Chains:
    def __init__(self, bot):
        self.bot = bot
        self.corpus = DuckHuntCorpus(logger=bot.logger)
        bot.logger.info("Pre-loading chains")
        self.corpus.model  # Pre-load
        bot.logger.info("Loaded chains")

    async def on_message(self, message):
        if message.content.endswith('...') and not message.author.bot:
            ctx = await self.bot.get_context(message, cls=CustomContext)
            inp = message.clean_content[:-3]

            try:
                inp_ = unicodedata.normalize('NFKD', inp)

            except:
                inp_ = inp

            if inp_ is None:
                inp_ = inp

            inp_ = inp_.lower()

            try:
                await ctx.send_to(f'{self.corpus.make_sentence_with_start(inp_)}')
            except WordNotFoundInCorpus as e:
                ctx.logger.warning(str(e))


def setup(bot):
    bot.add_cog(Chains(bot))
