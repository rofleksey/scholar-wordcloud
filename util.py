import signal

import nltk
from langdetect import detect, DetectorFactory
from natasha import (
    Segmenter,

    NewsEmbedding,
    NewsMorphTagger,
    NewsSyntaxParser,

    Doc, MorphVocab
)

DetectorFactory.seed = 0


# interrupts function after seconds_before_timeout seconds
def with_timeout(seconds_before_timeout):
    def decorate(f):
        def handler():
            raise TimeoutError()

        def new_f(*args, **kwargs):
            old = signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds_before_timeout)
            try:
                result = f(*args, **kwargs)
            finally:
                signal.signal(signal.SIGALRM, old)
            signal.alarm(0)
            return result

        new_f.__name__ = f.__name__
        return new_f

    return decorate


def noun_iterator_default(s):
    tokens = nltk.word_tokenize(s)
    for (word, pos) in nltk.pos_tag(tokens):
        if word.isalpha() and len(word) > 2:
            if pos.startswith('N'):
                yield word.capitalize()


def noun_iterator_ru(s):
    segmenter = Segmenter()
    morph_vocab = MorphVocab()
    emb = NewsEmbedding()
    morph_tagger = NewsMorphTagger(emb)
    syntax_parser = NewsSyntaxParser(emb)
    doc = Doc(s)
    doc.segment(segmenter)
    doc.tag_morph(morph_tagger)
    doc.parse_syntax(syntax_parser)
    for token in doc.tokens:
        token.lemmatize(morph_vocab)
        if token.pos in ["NOUN", "PROPN"]:
            yield token.lemma.capitalize()


def noun_iterator(s):
    lang = detect(s)
    if lang == "ru":
        return noun_iterator_ru(s)
    return noun_iterator_default(s)
