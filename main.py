import argparse
import os

import nltk
from tqdm import tqdm
from wordcloud import WordCloud

from extractors import extract_abstract
from scholar import fetch_articles, last_names_iterator
from util import noun_iterator

nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')

cli = argparse.ArgumentParser(description='Generates wordclouds from Google Scholar articles.')
cli.add_argument('-q', '--query', help='query text', required=True)
cli.add_argument('-o', '--output', help='output directory', default="results")
cli.add_argument('--width', help='wordcloud width', type=int, default=1920)
cli.add_argument('--height', help='wordcloud height', type=int, default=1080)
cli.add_argument('-p', '--pages', help='number of pages to query and parse', type=int, default=1)
args = cli.parse_args()

tags_map = {}
people_wordcloud_text = ''
articles = fetch_articles(args.query, args.pages)
articles_without_extended = []

for a in tqdm(articles):
    article_tags_map = {}
    actual_annotation = extract_abstract(a.link)
    if actual_annotation is None or len(a.annotation) > len(actual_annotation):
        actual_annotation = a.annotation
        articles_without_extended.append(a)
    for word in noun_iterator(actual_annotation):
        article_tags_map[word] = True
    for word in article_tags_map:
        tags_map[word] = tags_map.get(word, 0) + 1
    for last_name in last_names_iterator(a):
        people_wordcloud_text += f'{last_name} '

if not os.path.exists(args.output):
    os.makedirs(args.output)

tags_wordcloud_text = ''
for word in tags_map:
    for _ in range(tags_map[word]):
        tags_wordcloud_text += f'{word} '

tags_wordcloud = WordCloud(width=args.width, height=args.height, collocations=False).generate(tags_wordcloud_text)
tags_wordcloud.to_file(os.path.join(args.output, 'tags_wordcloud.png'))

people_wordcloud = WordCloud(width=args.width, height=args.height, collocations=False).generate(people_wordcloud_text)
people_wordcloud.to_file(os.path.join(args.output, 'people_wordcloud.png'))

extended_percentage = 100 * (len(articles) - len(articles_without_extended)) / len(articles)
print(f'Articles with extended abstract: {round(extended_percentage)}%')
print(f'Failed to extract extended abstract for these articles ({len(articles_without_extended)}):')
for a in articles_without_extended:
    print(a.link)
print("Done")
