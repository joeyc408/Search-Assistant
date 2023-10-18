# Description: This is the main file for the streamlit app. It contains the code for the streamlit app.
import openai
import streamlit as st  
import requests
import json
import os
import nltk
from bs4 import BeautifulSoup
from sumy.parsers.plaintext import PlaintextParser
from sumy.parsers.html import HtmlParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
nltk.download('punkt')
openai.api_key = os.getenv("API_KEY")
serper_api_key = os.getenv("SERP_KEY")
url = "https://api.openai.com/v1/engines/text-davinci-003/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {openai.api_key}"
}

# Extract search phrases from the input
def extract_keywords(question):
    response = openai.ChatCompletion.create(
        model = "gpt-3.5-turbo",
        messages = [
        {"role": "user", "content": f"Please provide me a better expression for my input in order to obtain better search results: {question}"}
        ]
    )
    
    keywords = response["choices"][0]["message"]["content"]
    return keywords

# Get the search results from Serper API
def search_get_url(keywords):
    url = "https://google.serper.dev/search"

    payload = json.dumps({
    "q": keywords,
    "num": 10
    })

    headers = {
    'X-API-KEY': serper_api_key,
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    response_data = response.json()

    # Get the links and the intro of each website
    links = [website["link"] for website in response_data["organic"]]
    intro = [website["snippet"] for website in response_data["organic"]]

    url_intro = dict(zip(links, intro))
    return url_intro

# Clean the search results
def clean_google_results(url_intro):
    url_content = {}

    for url in url_intro.keys():
        try:
            response = requests.get(url)
            response.raise_for_status()

            # Remove the scripts, styles, meta, and links
            soup = BeautifulSoup(response.text, "html.parser")

            for script in soup(["script", "style", "meta", "link"]):
                script.extract()
            main_content = soup.get_text()
            cleaned_content = main_content.replace("\n", "")
            
            # Summarize the content
            parser = HtmlParser.from_string(cleaned_content, url, Tokenizer("english"))
            summarizer = LsaSummarizer()
            page_summary = summarizer(parser.document, 5) 
            url_content[url] = page_summary
            
        except requests.exceptions.RequestException as e:
            continue
    return url_content

# Rank the search results
def analyze_search_results(url_dict, keywords):
    for url, content in url_dict.items():
        response = openai.ChatCompletion.create(
            model = "gpt-3.5-turbo",
            messages = [
                {"role": "system", "content": f"I would like to rank the following search results based on their relevance to these keywords: {keywords}."},
                {"role": "system", "content": "You will receive the content and the url of each search result. Please rank them from most relevant to least relevant and display them in such order."},
                {"role": "system", "content": "Please note that you should compare each search result with the keywords as well as each other for the ranking."},
                {"role": "system", "content": "Please add a summary no longer than 100 words for each search result."},
                {"role": "system", "content": "Please show the ranking and the url of the website as well."},
                {"role": "user", "content": f"URL: {url}"},
                {"role": "user", "content": f"Content: {content}"}
            ]
        )

        ranking_content = response['choices'][0]['message']['content']
    
    return ranking_content

st.title("Searching Assistant")

question = st.text_input("Enter below:")
if st.button("Search"):
    search_keywords = extract_keywords(question)

    url_intro = search_get_url(search_keywords)
        
    url_content = clean_google_results(url_intro)

    ranked_results = analyze_search_results(url_content, search_keywords)
    st.write(ranked_results)
