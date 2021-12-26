import tweepy
from dotenv import load_dotenv
import os
from flask import Flask, render_template, request
import re 
from textblob import TextBlob
import time
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import io
import base64



load_dotenv()


# SET AUTH
MY_API_KEY = os.getenv("API_KEY")
MY_API_KEY_SECRET = os.getenv("API_KEY_SECRET")
MY_ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
MY_ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")

app = Flask(__name__)

@app.route('/', methods=["GET", "POST"])
def main():
    if request.method == "POST":
        input_api_key = request.form.get("api_key")
        input_api_key_secret = request.form.get("api_key_secret")
        input_access_token = request.form.get("access_token")
        input_access_token_secret = request.form.get("access_token_secret")
        input_query = request.form.get("query")
        input_language = request.form.get("language")
        input_default_key = request.form.get("default_key")
        input_max_tweet = request.form.get("max_tweet")

        if not input_query or not input_language or not input_max_tweet:
            data = {}
            errorMsg = "Please fill all the field before run the program!"
            data["error"] = errorMsg
            return render_template('index.html', data=data, is_posted=False)
        else:
            if int(input_max_tweet) > 0:
                if input_default_key == "true":
                    data = twitter_api_call(MY_API_KEY, MY_API_KEY_SECRET, MY_ACCESS_TOKEN, MY_ACCESS_TOKEN_SECRET, input_query, input_language, input_max_tweet)
                    image = create_plot(data['result']) if data["status"] == "success" else None
                    is_posted = True if data["status"] == "success" else False
                    return render_template('index.html' if is_posted == False else 'result.html', data=data, is_posted=is_posted, image=image, query=input_query)
                else:
                    data = twitter_api_call(input_api_key, input_api_key_secret, input_access_token, input_access_token_secret, input_query, input_language,input_max_tweet)
                    image = create_plot(data['result']) if data["status"] == "success" else None
                    is_posted = True if data["status"] == "success" else False
                    return render_template('index.html' if is_posted == False else 'result.html', data=data, is_posted=is_posted,image=image, query=input_query)
            else:
                data = {}
                errorMsg = "Max search tweet has to be more than zero!"
                data["error"] = errorMsg
                return render_template('index.html', data=data, is_posted=False)
    else:
        errorMsg = "Any error while program is running will showed up here."
        return render_template('index.html', data=errorMsg, is_posted="default")


def create_plot(result):
     # Generate plot
    sentiments = ['Positive 😀', 'Negative ☹', 'Neutral 😐']
    fig = Figure()
    axis = fig.add_subplot()
    axis.set_title("Sentiment Analysis Graph")
    axis.set_xlabel("Sentiment")
    axis.set_ylabel("Number of Tweets")
    axis.bar(sentiments, result)
    
    # Convert plot to PNG image
    pngImage = io.BytesIO()
    FigureCanvas(fig).print_png(pngImage)
    
    # Encode PNG image to base64 string
    pngImageB64String = "data:image/png;base64,"
    pngImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')

    return pngImageB64String


def twitter_api_call(api_key, api_key_secret, access_token, access_token_secret, query, lang, max_tweet):
    # ACCESS TWEEPY
    auth = tweepy.OAuthHandler(api_key, api_key_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    tweet_analytic_result = {}

    try:
        search = [status for status in tweepy.Cursor(api.search, q=f'{query} -filter:retweets', lang=lang, tweet_mode='extended').items(int(max_tweet))]
        tweet_data = []

        def on_status(status):
            if hasattr(status, 'retweeted_status'):
                try:
                    return status.retweeted_status.extended_tweet["full_text"]
                except:
                    return status.retweeted_status.full_text
            else:
                try:
                    return status.extended_tweet["full_text"]
                except AttributeError:
                    return status.full_text

        for tweet in search:
            tweet_prop = {}
            tweet_prop["tanggal"] = tweet.created_at
            tweet_prop["user_screen"] = tweet.user.screen_name
            tweet_prop["user_name"] = tweet.user.name
            tweet_prop["user_links"] = f"https://twitter.com/{tweet.user.screen_name}"
            tweet_prop["user_profile_pic"] = tweet.user.profile_image_url_https
            tweet_prop["user_tweet"] = on_status(tweet)
            tweet_prop["user_id"] = tweet.user.id
            tweet_prop["tweet_id"] = tweet.id
            tweet_prop["replies"] =tweet.in_reply_to_status_id
            tweet_prop["user_tweet_url"] = f"https://www.twitter.com/{tweet.user.screen_name}/status/{tweet.id}"
            cleaned_tweet = ' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)"," ",on_status(tweet)).split())
            analysis = TextBlob(cleaned_tweet)

            if(lang == "id"):
                try:
                    analysis.translate(to="en")
                except Exception as e:
                    print(e)

            tweet_prop["tweet_score"] = analysis.sentiment.polarity
            tweet_prop["tweet_sentiment"] = "positive" if analysis.sentiment.polarity > 0.0 else "negative" if analysis.sentiment.polarity < 0.0 else "neutral"

            if not tweet.in_reply_to_status_id:
                if tweet.retweet_count > 0:
                    if tweet_prop not in tweet_data:
                        tweet_data.append(tweet_prop)
                else:
                    tweet_data.append(tweet_prop)

        tweet_positive = [t for t in tweet_data if t["tweet_sentiment"]=="positive"]
        tweet_negative = [t for t in tweet_data if t["tweet_sentiment"]=="negative"]
        tweet_neutral = [t for t in tweet_data if t["tweet_sentiment"]=="neutral"]

        result = {}

        try: 
            result["positive"] = "{} %".format(round(100*len(tweet_positive)/len(tweet_data), 2)) 
        except Exception as e: 
            result["positive"] = "0%"

        try: 
            result["negative"] = "{} %".format(round(100*len(tweet_negative)/len(tweet_data), 2)) 
        except Exception as e: 
            result["negative"] = "0%"

        try: 
            result["neutral"] = "{} %".format(round(100*len(tweet_neutral)/len(tweet_data), 2)) 
        except Exception as e: 
            result["neutral"] = "0%"
        

        result["positive_result"] = len(tweet_positive)
        result["negative_result"] = len(tweet_negative)
        result["neutral_result"] = len(tweet_neutral)
        tweet_analytic_result["tweet_data"] = tweet_data
        tweet_analytic_result["tweet_analytic"] = result
        tweet_analytic_result["status"] = "success"
        tweet_analytic_result["result"] = [result["positive_result"], result["negative_result"], result["neutral_result"]]
        return tweet_analytic_result

    except tweepy.TweepError as error:
        if error == "[{u'message': u'Rate limit exceeded', u'code': 88}]":
            time.sleep(60*5) #Sleep for 5 minutes
        else:
            print(error)
            if "401" in str(error): 
                tweet_analytic_result["error"] = "Forbidden Access! Please provide valid API Key and Access Token"
            else:
                tweet_analytic_result["error"] = "Bad Request! Please provide valid API Key and Access Token or Queries"
            tweet_analytic_result["status"] = "failed"
            return tweet_analytic_result


# app.config['DEBUG'] = True
if __name__ == "__main__":
    app.run()