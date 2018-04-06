## Generic news skill

Plays the latest hour news via audio source

## Description

Choose default news station based on your location, or you can configure it in settings

You can request the following news stations:

* [ABC](http://radio.abc.net.au/help/streams)
* [BBC](https://www.bbc.com/news)
* [CBC](http://www.cbc.ca/news)
* [FOX](http://www.foxnews.com/)
* [GBP](http://www.gpb.org/)
* [NOS](https://www.nporadio1.nl/nos-radio-1-journaal)
* [NPR](https://www.npr.org/)
* [RNE](http://www.rtve.es/radio/)
* [TSF](http://tsf.pt)

## Examples

* "news"
* "tell me news"
* "stop news"
* "end news"
* "play fox news"
* "tell me bbc news"
* "play the australian news"
* "spanish news"


## TODO

* adding more default feeds by location
* world news station as a default's default

## Add a new news station

* optionally make station_name.vocab, add station names and country if desired

    tsf.voc

        tsf
        T S F
        portuguese
        portugal

* optionally make station_name.dialog if you want customized dialog

    tsf.dialog

        Here are your annoying news from T S F

* add url to self.feeds dictionary in line 48 (__init__ method)


        def __init__(self):
            super(UnifiedNewsSkill, self).__init__(name="UnifiedNewsSkill")
            # static feed urls go here
            self.feeds = {
                "abc": "http://live-radio02.mediahubaustralia.com/PBW/mp3/",
                # keys are used for fuzzy match when no intent matches
                # optional if you add it to update_feed_url
                "bbc": ""}

* add url parsing if needed in line 100 (update_feed_url method)


        # feeds made as properties to simplify logic

        @property
        def npr_feed(self):
            data = feedparser.parse(
                "http://www.npr.org/rss/podcast.php?id=500005")
            url = re.sub('https', 'http', data['entries'][0]['links'][0]['href'])
            return url

        # urls that need updating at runtime go here
        def update_feed_url(self, feed):
            if feed == "npr":
                self.feeds[feed] = self.npr_feed

* optionally add to default feed logic in line 133 (default_feed property), if it should be auto selected in some country


        @property
        def default_feed(self):

            # check if user configured a default feed
            if self.settings.get("default_feed", ""):
                return self.settings["default_feed"]

            # select feed by country
            if self.country.lower() == "us":
                return "npr"
            elif self.country_name.lower() == "portugal":
                return "tsf"

* optionally make an intent if you made the .vocab, else fuzzy match will be used


        @intent_handler(IntentBuilder("ABCNewsIntent").require(
            "ABC").require("news").optionally("play"))
        def handle_abc_intent(self, message):
            self.play_news("abc")

## Credits

* JarbasAI
* [MycroftAI](https://github.com/MycroftAI/skill-npr-news)
* [KathyReid](https://github.com/KathyReid/skill-australian-news)
* [ReK2Fernandez](https://github.com/ReK2Fernandez/skill-radio-rne)
* [JosiahDub](https://github.com/JosiahDub/skill-gpb-news)
* [WalterKlosse](https://github.com/WalterKlosse/mycroft-skill-bbc-news)
* [chrison999](https://github.com/chrison999/mycroft-skill-cbc-news)

