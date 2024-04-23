#Imports
from discord import Client, Intents,app_commands,Object as discord_object
from asyncio import sleep
from json import JSONDecoder, JSONEncoder
from os import listdir, environ
from atexit import register
from dotenv import dotenv_values

#Values to pull from your local .env file to separate data from code
config = {
    **dotenv_values(),
    **environ
}

#To translate the admin list from JSON format
config['ADMIN'] = JSONDecoder().decode(config['ADMIN'])

#File to store score, currently set to store where program is
PSC = "player_score.json"
file_exists = PSC in listdir()

#This is where your points system is set up
DEBUG = False #Change to True to print emojis to add to library
cols = {'white': '⚪', 'green':'🟢', 'blue':'🔵', 'purple': '🟣', 'orange':'🟠'}
points = {
    cols['white']: 2**1,
    cols['green']: 2**2,
    cols['blue']: 2**4,
    cols['purple']: 2**8,
    cols['orange']: 2**16
}

#to create/load file to store player scores
wysi_score = {}
if file_exists:
    with open(PSC) as file:
        rawd = file.read()
    wysi_score = JSONDecoder().decode(rawd or "{}")
else:
    open(PSC,"w").close()

#Connection to discord api and setting permissions for our use case and to be able to use commands
intents = Intents(messages=True, guilds=True, typing=True, message_content=True, reactions=True)
client = Client(intents=intents)
commander = app_commands.CommandTree(client)

#Sorting algorithm for top 5 scores. Can change scope to expand leaderboard.
def leader(scope=5, caller=None):
    topscores = []
    caller_score = None
    for user in wysi_score:
        user_score = wysi_score[user]
        if len(topscores) == 0: topscores.append(user)
        else:
            for i in range(len(topscores)):
                if user_score > wysi_score[topscores[i]]:
                    topscores.insert(i, user)
                    break
            else: topscores.append(user)
    return topscores[:scope], caller, topscores.index(caller)+1 if caller and caller in wysi_score else None

#Funtion for the leaderboard output is below. Can edit using markdown format 
def lead_out(toplb,caller,caller_pos):
    print(toplb)
    noodle = "**__Top 5__**\n"
    for n,user in enumerate(toplb,1):
        noodle += f"#{n} {'__' if caller == user else ''}{user}{'__' if caller == user else ''} - {wysi_score[user]}\n"
    if caller_pos and caller_pos >= len(toplb):
        noodle += f"\n__**You**__\n#{caller_pos} {caller} - {wysi_score[caller]}\n"
    elif not caller_pos:
        noodle += f"\n__**You**__\n#{len(toplb)+1} {caller} - 0\n"
    return noodle

#This is the command in discord. Can change from ephemeral if you want public response from the bot
@commander.command(name="lb",guild=discord_object(id=config['SERVERID']),
description = "Top 5 Leaderboard")
async def slash_lb(interactions):
    ret = lead_out(*leader(caller=interactions.user.name))
    await interactions.response.send_message(ret,ephemeral=True)

@client.event
async def on_ready():
    await commander.sync(guild=discord_object(id=config['SERVERID']))

#Called when someone reacts to a message. Adds their score to the player_score file
@client.event
async def on_raw_reaction_add(payload):
    if DEBUG: print(payload.emoji.name)
    
    if payload.member.name not in config['ADMIN']: return  #If they're not an admin, fuck em! (only admins can add score)
    if payload.emoji.name not in points: return  #Check that emoji is in our dictionary
    
    channel = await client.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    if message.author.name not in wysi_score:
        wysi_score[message.author.name] = 0
    wysi_score[message.author.name] += points[payload.emoji.name]
    save()
    await channel.send(f"{message.author.name} earned {points[payload.emoji.name]} points")

#To remove score when a reacton is removed
@client.event
async def on_raw_reaction_remove(payload):
    if DEBUG: print(payload.emoji.name)
    
    channel = await client.fetch_channel(payload.channel_id)
    reactor = await client.fetch_user(payload.user_id)
    
    if reactor.name not in config['ADMIN']: return
    if payload.emoji.name not in points: return

    message = await channel.fetch_message(payload.message_id)

    if message.author.name not in wysi_score:
        wysi_score[message.author.name] = 0
    wysi_score[message.author.name] -= points[payload.emoji.name]
    if wysi_score[message.author.name] == 0:
        del wysi_score[message.author.name]
    save()
    
    await channel.send(f"{message.author.name} lost {points[payload.emoji.name]} points")
    await calculate_score(channel, payload.message_id)

#This is the start of the +1 code
async def calculate_score(channel, message_id):
    await sleep(1)
    message = await channel.fetch_message(message_id)
    reactions = message.reactions  # seems to be in the right order
    print(message)
    print(message.reactions)

#To save scored when program is closed. Code also saves whenever a score is changed (see above code)
@client.event
async def on_disconnect():
    save()

def save():
    print ("closing")
    with open (PSC,"w") as file:
        ecd = JSONEncoder().encode(wysi_score)
        file.write(ecd)
        
register(save)

client.run(config['APIKEY']) 
