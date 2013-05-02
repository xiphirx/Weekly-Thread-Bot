import praw
import configparser
import sys
import re
import urllib.request
from datetime import datetime

class Thread:
  mTitlePrepend = "[Weekly] "
  mTitleSuffix = datetime.today().strftime(" - %m/%d/%y")

  def __init__(self, type, title, args = []):
    with open(type + ".template", 'r') as template:
      self.mTemplateString = template.read()

    self.mTitle = Thread.mTitlePrepend + title + Thread.mTitleSuffix
    self.mTemplateString = self.mTemplateString % tuple(args)

  def title(self):
    return self.mTitle

  def body(self):
    return self.mTemplateString

class WeeklyThreadBot:
  mTypes = ["LOOT", "QUEST", "GEAR"]

  class HeadRequest(urllib.request.Request):
    def get_method(self):
      return "HEAD"

  def __init__(self):
    # Load config
    self.mConfigParser = configparser.ConfigParser()
    self.mConfigParser.read("config.ini")

    # Initialize reddit instance and login
    self.mReddit = praw.Reddit(user_agent=self.mConfigParser.get("DEFAULT", "user_agent"))
    self.mReddit.login(self.mConfigParser.get("DEFAULT", "user"), self.mConfigParser.get("DEFAULT", "password"))

  def retrieveLastWinners(self, id):
    previousSubmission = self.mReddit.get_submission(submission_id=id, comment_sort="top")

    returnArgs = []
    i = 0;

    # Attempt to find any links posted, and determine if its an image
    for comment in previousSubmission.comments:
      links = re.compile('&lt;a(.+)href="(.*)"(.+)&gt;', re.IGNORECASE)
      items = re.findall(links, comment.body_html)

      if (len(items) > 0):
        img = urllib.request.urlopen(self.HeadRequest(items[0][1]))
        contentType = img.info()['Content-Type']

        if contentType != None and contentType.startswith('image/'):
          returnArgs.append(comment.author.name)
          returnArgs.append(comment.permalink)
          returnArgs.append(items[0][1])
          i += 1

      if (i >= 3):
        break;

    returnArgs.append(previousSubmission.url)

    return returnArgs

  def post(self, type):
    if (type not in WeeklyThreadBot.mTypes):
      print("Invalid type of thread '" + type + "'")
      return

    # Prepare template arguments. If we are doing the loot thread then we need to grab more info
    tempArgs = []
    tempArgs.append(self.mConfigParser.getint(type, "week_num"))

    if (type == "LOOT"):
      lootThreadExtraParams = self.retrieveLastWinners(self.mConfigParser.get(type, "previous_submission"))
      tempArgs.extend(lootThreadExtraParams)

    thread = Thread(type, self.mConfigParser.get(type, "title"), tempArgs)

    newThread = self.mReddit.submit(self.mConfigParser.get("DEFAULT", "subreddit"), thread.title(), text=thread.body())
    newThread.distinguish()

    # Save new config variables
    self.mConfigParser.set(type, "week_num", tempArgs[0] + 1)
    if (type == "LOOT"):
      self.mConfigParser.set(type, "previous_submission", newThread.id)

    with open("config.ini", "w") as config:
      self.mConfigParser.write(config)

def usage():
  print("Usage: bot.py <type of thread to post>")
  print("--------------------------------------")
  print("     Type of thread can be one of the following")
  print("           LOOT  - Weekly loot thread")
  print("           QUEST - Stupid questions")
  print("           GEAR  - Gear checks")

def main():
  if (len(sys.argv) == 1):
    usage()
    exit()

  bot = WeeklyThreadBot()
  bot.post(sys.argv[1])

if __name__ == '__main__':
  main()