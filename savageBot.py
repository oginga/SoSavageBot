import os,pickle,logging,tweepy,redis
from argparse import ArgumentParser
from datetime import datetime
from pprint import pprint


#-------------INIT--------------
conn = redis.Redis(decode_responses=True) #decode to return results as strings instead of bytes
pipeline=conn.pipeline()

logger = logging.getLogger('savagebot')
hdlr = logging.FileHandler('logsavagebot.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.DEBUG)

logger.info("Fetched mentions")

#---------------------
MESSAGES={}

API_KEY=os.getenv("SAV_API_KEY")
API_SECRET_KEY=os.getenv("SAV_API_SECRET_KEY")
ACCESS_TOKEN=os.getenv("SAV_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET=os.getenv("SAV_ACCESS_TOKEN_SECRET")
DEBUG=os.getenv("SAV_BOT_DEBUG")
AUTO_RETWEET=os.getenv("SAV_BOT_RETWEET")


def store(data):
    with open('pickled','wb') as f:
        pickle.dump(data,f)

def retreive():
    with open('pickled','rb') as f:
        data=pickle.load(f)
    
    return data

def load_messages():
    global MESSAGES
    MESSAGES=conn.hgetall(f"sav:messages:")


def get_api():
    auth = tweepy.OAuthHandler(API_KEY, API_SECRET_KEY)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True)

    return api

def get_mentions(api):
    '''Polls twitter for mentions from the last fetched mention
    
    Params
    api: Obj
        Tweepy api object

    Returns
    mentions: list
        List of the found mentions

    '''

    last_mention_id=conn.get(f"sav:lastMention")
    logger.info(f"Last mention befor fetch {last_mention_id}")
    mentions=[]
    if last_mention_id:
        mentions = api.mentions_timeline(since_id=last_mention_id)
    else:
        mentions = api.mentions_timeline()
    return mentions

def store_messages(mention_id,msg,pipeline,sent=0):
        
        pipeline.sadd(f"sav:replies",mention_id)
        pipeline.hmset(f"sav:replies:{mention_id}",{'msg':msg,'sent':sent})#TODO: add expiry 
        logger.info(f"Message {msg} stored for mention id {mention_id}")

def process_mentions(mentions,api):
    
    global pipeline
    global MESSAGES

    bool_check=lambda x:1 if x else 0
    str_check=lambda x:x if x else "-"

    def store_authors(mention):
        
        author_details={'name':str_check(mention.author.name),'screen_name':str_check(mention.author.screen_name),'location':str_check(mention.author.location),'verified':bool_check(mention.author.verified)}
        author_id=mention.author.id
        author_key=f"sav:authors:{author_id}"
        pipeline.hset(f"sav:authors",author_id,str_check(mention.author.name))
        pipeline.hmset(author_key,author_details)
        # Score savage reply autho
        pipeline.zadd(f"sav:authors:scores",{mention.in_reply_to_user_id:0})
        logger.info(f"Stored author {str_check(mention.author.name)}")

    def store_mentions(mention):
        mention_id=mention.id
        link=f"https://twitter.com/{str_check(mention.author.screen_name)}/status/{mention_id}"
        mention_details={'reply_id':mention.in_reply_to_status_id,'reply_author_id':mention.in_reply_to_user_id,'mention_author_id':mention.author.id,'mention_author_screen_name':str_check(mention.author.screen_name),'link':link,'status':0,'retweeted':0}
        pipeline.zadd(f"sav:mentions",{mention_id:mention.created_at.timestamp()})
        pipeline.hmset(f"sav:mentions:{mention_id}",mention_details)
        logger.info(f"Stored mention {mention_details}")
        
    for mention in mentions:
        # Process mention if not already retweeted by bot or if mention is a reply
        if not mention.retweeted and mention.in_reply_to_status_id_str:
            store_authors(mention)
            store_mentions(mention)
            

        else:# Queue for reply
            msg=MESSAGES.get('sorry',f"Hi {str_check(mention.author.screen_name)}, Sorry,I received an error processing this tweet")
            if mention.retweeted:
                msg=MESSAGES.get('retweeted',f"Hi {str_check(mention.author.screen_name)}, I already retweeted this.Thanks.")
            elif not mention.in_reply_to_status_id_str:
                msg=MESSAGES.get('not_reply',f"Hi {str_check(mention.author.screen_name)},I retweet mentions on reply tweets not parent tweets.Thanks")
            api.update_status(status = msg, in_reply_to_status_id = mention.id , auto_populate_reply_metadata=True)
            logger.info(f"Replied to mention tweet:{mention.id}")
            store_messages(mention.id,msg,pipeline,sent=1)
    
        pipeline.set(f"sav:lastMention",mention.id)
        res=pipeline.execute()
        print(f"Finished executing {res}")
    

def retweet(api):
    global pipeline
    mention_ids=conn.zrange('sav:mentions', 0, -1, withscores=True) #List of tuples

    def send_tweet_update_status(mention,msg,mode="Validated"):
        try:
            api.retweet(mention['reply_id'])
            pipeline.hset(f'sav:mentions:{m_id}','retweeted',1)
            logger.info(f"[{mode}] Retweeted tweet:{m_id} by {mention['link']}")
            api.update_status(status = msg, in_reply_to_status_id = mention['id'] , auto_populate_reply_metadata=True)
            logger.info(f"Replied to mention tweet:{m_id}")
                
        except Exception as e:
            logger.error(f"Error encountered sending tweet: {e}")
            pipeline.hset(f'sav:mentions:{m_id}','retweeted',1)

    for m_id,_ in mention_ids:
        print(f"mid sav:mentions:{m_id}")
        mention=conn.hgetall(f'sav:mentions:{m_id}')
        msg=MESSAGES.get('shared',f"Hi {mention['mention_author_screen_name']},I shared the blunt :-D")
        # AUTORETWEET if enabled
        if AUTO_RETWEET and int(mention['retweeted'])== 0:
            send_tweet_update_status(mention,msg,"Auto")
            reply_author_id=conn.hget(f'sav:mentions:{m_id}','reply_author_id')
            # Increase approved reply author's score
            pipeline.zincrby(f"sav:authors:scores",reply_author_id,1)
            # store_messages(mention['id'],msg,pipeline,sent=1)
        elif int(mention['status'])== 1 and int(mention['retweeted'])== 0 : #Check retweet APPROVE status
            # retweet
            send_tweet_update_status(mention,msg)
            
    pipeline.execute()

def send_replies(api):
    global pipeline
    reply_ids=conn.smembers('sav:replies') #List of tuples
    for r_id in reply_ids:
        reply=conn.hgetall(f'sav:replies:{r_id}')
        logger.info(f"Reply {reply['msg']} sent_status: {reply['sent']}")
        if reply['msg'] and int(reply['sent'])==0:#message not yet sent
            # send message
            api.update_status(status = reply['msg'], in_reply_to_status_id = r_id , auto_populate_reply_metadata=True)
            # Update message to sent
            pipeline.hset(f'sav:replies:{r_id}','sent',1)
            logger.info(f"Replied to mention {r_id}")
            print(f"Replied to mention {r_id}")

    pipeline.execute()

if __name__ == "__main__":
    
    parser=ArgumentParser()
	
	# --------------CRON COMMANDLINE ARGS---------------------
    parser.add_argument('-f','--fetch', action='store_true',help='Fetch mentions.')
    parser.add_argument('-r','--retweet',action='store_true',help="Retweet approved tweets")
    parser.add_argument('-m','--message', action='store_true',help='Tweet reply to mentions')

    args=parser.parse_args()

    # --------init bot----------------
    api=get_api()
    load_messages()
    # -------end init------------

    if args.fetch:
        mentions=[]
        if DEBUG:
            mentions=retreive()
        else:
            mentions=get_mentions(api)
            # store(mentions) #pickle data to avoid rate limits during dev

        mentions.reverse()
        mentions_string=" | ".join([str(m.id) for m in mentions])
        logger.info(f"Fetched mentions {mentions_string}")
        process_mentions(mentions,api)
        # Do all tasks once instead of creating different cron tabs
        retweet(api)
        # send_replies(api)        
    elif args.retweet:
        retweet(api)
    elif args.message:
        send_replies(api)
    