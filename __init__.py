# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import feedparser
import re
from os.path import exists
from adapt.intent import IntentBuilder
from mycroft.skills.core import intent_handler
from mycroft.util.log import LOG
from mycroft.util.parse import match_one
import random
from os.path import join
from datetime import datetime
import requests
from requests.exceptions import ConnectionError, ReadTimeout
from mycroft_jarbas_utils.skills.audio import AudioSkill


__author__ = "jarbas"


class UnifiedNewsSkill(AudioSkill):
    def __init__(self):
        super(UnifiedNewsSkill, self).__init__(name="UnifiedNewsSkill")
        # static feed urls go here
        self.feeds = {
            "abc": "http://live-radio02.mediahubaustralia.com/PBW/mp3/",
            "nos": "https://download.omroep.nl/nos/radionieuws"
                   "/nosnieuws_bulalg.mp3",
            # optional, keys are used for fuzzy match when no intent matches
            "bbc": "",
            "cbc": "",
            "npr": "",
            "tsf": "",
            "fox": "",
            "rne": ""}

    def play_news(self, feed=None):
        """
        for provided news feed:
                update url,
                fallback to default feed if  necessary,
                choose dialog for this feed if it exists
                fallback to default dialog if necessary,
                stop audio
                play news audio
        """
        feed = feed or self.default_feed
        if feed not in self.feeds:
            LOG.warning("bad news feed chosen, using default")
            feed = self.default_feed
        self.update_feed_url(feed)
        url = self.feeds[feed]
        if self.settings["force_http"]:
            url = url.replace("https", "http")
        # if news is already playing, stop it silently
        self.stop()
        # speak news intro
        specialized_dialog = join(self.root_dir, 'dialog', self.lang,
                                  feed+".dialog")
        # if feed specific dialog exists use it
        if exists(specialized_dialog):
            self.speak_dialog(feed+".dialog")
        else:
            # else use default dialog
            self.speak_dialog('news', {"feed": feed})
        if url:
            self.play(url)
        else:
            self.speak_dialog('news.error', {"feed": feed})

    def update_feed_url(self, feed):
        """ updates news stream url before playing """
        # urls that need updating at runtime go here
        if feed == "npr":
            self.feeds[feed] = self.npr_feed
        elif feed == "tsf":
            self.feeds[feed] = self.tsf_feed
        elif feed == "fox":
            self.feeds[feed] = self.fox_feed
        elif feed == "cbc":
            self.feeds[feed] = self.cbc_feed
        elif feed == "bbc":
            self.feeds[feed] = self.bbc_feed
        elif feed == "gbp":
            self.feeds[feed] = self.gbp_feed
        elif feed == "rne":
            self.feeds[feed] = self.rne_feed

    # choose default feed based on current location
    @property
    def country(self):
        loc = self.location
        if type(loc) is dict and loc["city"]:
            return loc["city"]["state"]["country"]["code"]
        return None

    @property
    def country_name(self):
        loc = self.location
        if type(loc) is dict and loc["city"]:
            return loc["city"]["state"]["country"]["name"]
        return None

    @property
    def default_feed(self):
        """ select user configured feed or choose one based on location """
        # check if user configured a default feed
        if self.settings.get("default_feed", ""):
            return self.settings["default_feed"]

        # select feed by country
        if self.country.lower() == "us":
            return "npr"
        elif self.country_name.lower() == "portugal":
            return "tsf"
        elif self.country_name.lower() == "canada":
            return "cbc"
        elif self.country.lower() == "au":
            return "abc"
        elif self.country.lower() == "nl":
            return "dutch"
        elif self.country.lower() == "es":
            return "rne"
        elif self.country.lower() == "uk":
            return "bbc"
        # TODO news from all the places

        # default to official mycroft skill behaviour
        # TODO world news station
        return "npr"

    # feeds made as properties to simplify logic
    @property
    def rne_feed(self):
        data = feedparser.parse(
            "http://api.rtve.es/api/programas/36019/audios.rs")
        url = data['entries'][0]['links'][0]['href']
        return url

    @property
    def gbp_feed(self):
        data = feedparser.parse(
            "http://feeds.feedburner.com/gpbnews/GeorgiaRSS?format=xml")
        next_link = data["entries"][0]["links"][0]["href"]
        html = requests.get(next_link)
        # Find the first mp3 link
        # Note that the latest mp3 may not be news,
        # but could be an interview, etc.
        # If you know a better source for the latest news mp3, let me know.
        mp3_find = re.search('href="(?P<mp3>.+\.mp3)"', html.content)
        # Replace https with http because AudioService can't handle it
        if mp3_find is None:
            LOG.error("could not get gbp news feed")
            return ""
        url = mp3_find.group("mp3")
        return url

    @property
    def bbc_feed(self):
        # TODO fix me
        data = feedparser.parse("http://feeds.bbci.co.uk/news/rss.xml")
        print data
        url = data['entries'][0]['links'][0]['href']
        return None

    @property
    def cbc_feed(self):
        data = feedparser.parse(
            "http://www.cbc.ca/podcasting/includes/hourlynews.xml")
        url = 'http', data['entries'][0]['links'][0]['href']
        return url

    @property
    def npr_feed(self):
        data = feedparser.parse(
            "http://www.npr.org/rss/podcast.php?id=500005")
        url = data['entries'][0]['links'][0]['href']
        return url

    @property
    def tsf_feed(self):
        date = datetime.now()
        year = str(date.year)
        month = str(date.month)
        if len(month) == 1:
            month = "0" + month
        day = str(date.day)
        if len(day) == 1:
            day = "0" + day
        hour = str(date.hour)
        if len(hour) == 1:
            hour = "0" + hour

        status = 404
        fails = 0
        timeout = 0.5
        while status == 404 and fails <= 6:
            url = join("https://www.tsf.pt/stream/audio/",
                       year, month, "noticias", day, "not" + hour + ".mp3")
            try:
                # yes it is ugly, but the fastest way
                req = requests.get(url, timeout=timeout)
                status = req.status_code
                print year, month, hour
                print status
            except ConnectionError:
                # cant open mp3 stream, this indicates success
                return url
            except ReadTimeout:
                # should not happen, increase timeout above
                timeout += 0.5
                continue
            except Exception as e:
                # should not happen
                print e
            # try to go back 6 hours until news are found
            fails += 1
            hour = str(int(hour) - 1)
            if "-" in hour:
                hour = "23"
                day = str(int(day) - 1)
                if "-" in day or day == "0":
                    day = "31"
                    month = str(int(month) - 1)
                    if month == "0" or "-" in month:
                        month = "12"
            if len(month) == 1:
                month = "0" + month
            if len(day) == 1:
                day = "0" + day
            if len(hour) == 1:
                hour = "0" + hour
        LOG.error("could not find url for latest news")
        return ""

    @property
    def fox_feed(self):
        data = feedparser.parse("http://feeds.foxnewsradio.com/FoxNewsRadio")
        url = data['entries'][0]['links'][0]['href']
        return url

    # intent per news station
    @intent_handler(IntentBuilder("FoxNewsIntent").require(
        "FOX").require("news").optionally("play").optionally("latest"))
    def handle_fox_intent(self, message):
        self.play_news("fox")

    @intent_handler(IntentBuilder("CBCNewsIntent").require(
        "CBC").require("news").optionally("play").optionally("latest"))
    def handle_cbc_intent(self, message):
        self.play_news("cbc")

    #@intent_handler(IntentBuilder("BBCNewsIntent").require(
    #    "BBC").require("news").optionally("play").optionally("latest"))
    def handle_bbc_intent(self, message):
        self.play_news("bbc")

    @intent_handler(IntentBuilder("GBPNewsIntent").require(
        "GBP").require("news").optionally("play").optionally("latest"))
    def handle_gbp_intent(self, message):
        self.play_news("gbp")

    @intent_handler(IntentBuilder("NPRNewsIntent").require(
            "NPR").require("news").optionally("play").optionally("latest"))
    def handle_npr_intent(self, message):
        self.play_news("npr")

    @intent_handler(IntentBuilder("TSFNewsIntent").require(
            "TSF").require("news").optionally("play").optionally("latest"))
    def handle_tsf_intent(self, message):
        self.play_news("tsf")

    @intent_handler(IntentBuilder("RNENewsIntent").require(
        "RNE").require("news").optionally("play").optionally("latest"))
    def handle_rne_intent(self, message):
        self.play_news("rne")

    @intent_handler(IntentBuilder("ABCNewsIntent").require(
        "ABC").require("news").optionally("play").optionally("latest"))
    def handle_abc_intent(self, message):
        self.play_news("abc")

    @intent_handler(IntentBuilder("NOSNewsIntent").require(
        "NOS").require("news").optionally("play").optionally("latest"))
    def handle_abc_intent(self, message):
        self.play_news("nos")

    # generic news intents
    @intent_handler(IntentBuilder("randomNewsIntent").require(
        "random").require("news").optionally("play").optionally("latest"))
    def handle_random_intent(self, message):
        self.play_news(random.choice(self.feeds.keys()))

    @intent_handler(IntentBuilder("GenericNewsIntent").require("news")
                    .optionally("play").optionally("latest"))
    def handle_news_intent(self, message):
        # clean a bit the utterance
        remainder = message.utterance_remainder()
        # fuzzy match available feeds
        feed, score = match_one(remainder, self.feeds.keys())
        # if score is low fallback to default
        if score <= 0.5:
            feed = self.default_feed
        self.play_news(feed)

    @intent_handler(IntentBuilder("NewsStopIntent").require(
        "stop").require("news"))
    def handle_stop(self, message):
        was_playing = self.stop()
        if was_playing:
            self.speak_dialog('news.stop')
        else:
            # be funny if you were told to stop news without them playing
            self.speak_dialog('news.stop.error')

    def stop(self):
        was_playing = False
        self.enclosure.activate_mouth_events()
        self.enclosure.mouth_reset()
        if self.settings["use_audio_service"]:
            was_playing = self.audio.is_playing
            if was_playing:
                self.audio.stop()
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
            was_playing = True
        return was_playing

    # WIP zone
    def generate_intent(self, feed):
        """ auto generate intents from .voc files """
        name = feed.upper() + "NewsIntent"
        intent = IntentBuilder(name).require(feed).require(
            "news").optionally("play").optionally("latest").build()

        def news_handler(message, dummy=""):
            self.play_news(feed)

        self.register_intent(intent, news_handler)


def create_skill():
    return UnifiedNewsSkill()
