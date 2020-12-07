#!/usr/bin/python3
import os,sys,io
import json,time

import asyncio
from commoncodes import CommonCode

from instalooter.looters import ProfileLooter, PostLooter
from instalooter.cli.login import login

from fs.memoryfs import MemoryFS

from aiogram import Bot,Dispatcher,executor,types
from aiogram import types

curdir=os.path.abspath(os.path.dirname(__file__))
conf_fp=os.path.join(curdir,"config.json")
sent_fp=os.path.join(curdir,"sent_links.json")

if os.path.exists(conf_fp):
	with open(conf_fp,"r") as f:
		CONF=json.load(f)
else:
	raise CommonCode(78,f"No config file found at {conf_fp}")

for key in ("tg_token","tg_chat_id","ig_profile","ig_usrname","ig_passwd","wait_time"):
	if key not in CONF:
		raise CommonCode(78,f"Missing key in configuration: {key}")

if not os.path.exists(sent_fp):
	with open(sent_fp,"w+") as f:
		f.write("[]")

TG_TOKEN=CONF["tg_token"]
TG_CHAT_ID=CONF["tg_chat_id"]

bot=Bot(token=TG_TOKEN)

async def update():
	await bot.send_chat_action(TG_CHAT_ID,types.ChatActions.TYPING)
	pl=ProfileLooter(CONF["ig_profile"])
	with open(sent_fp,"r") as f:
		sent=json.load(f)
	sent_something=False
	for media in pl.medias():
		i=media["id"]
		sc=media["shortcode"]
		if i not in sent:
			sent.append(i)
			_pl=PostLooter(sc)
			info=_pl.get_post_info(sc)
			caption="\n".join(edge["node"]["text"] for edge in info["edge_media_to_caption"]["edges"])
			with MemoryFS() as fs:
				if media["is_video"]:
					await bot.send_chat_action(TG_CHAT_ID,types.ChatActions.RECORD_VIDEO)
					_pl.download_videos(fs,media_count=1)
					func=bot.send_video
					await bot.send_chat_action(TG_CHAT_ID,types.ChatActions.UPLOAD_VIDEO)
				elif media["__typename"].lower()=="graphimage":
					await bot.send_chat_action(TG_CHAT_ID,types.ChatActions.UPLOAD_PHOTO)
					_pl.download_pictures(fs,media_count=1)
					func=bot.send_photo
				else:
					print("\033[31mUNKNOWN MEDIA TYPE AAAAA\033[0m",media)
					break
				fn=fs.listdir("./")[0]
				with fs.openbin(fn) as f:
					await func(TG_CHAT_ID,f,caption=f"{caption}\n→[original post](https://www.instagram.com/p/{sc})",parse_mode="Markdown")
			print(f"Sent {i}/{sc}")
			sent_something=True
	with open(sent_fp,"w+") as f:
		json.dump(sent,f)
	return sent_something

login({"--username":CONF["ig_usrname"],"--password":CONF["ig_passwd"],"--quiet":False})

async def looop_haha():
	idle_for=0
	while True:
		print(f"UPDATE TIME {idle_for}")
		if await update():
			idle_for=0
		else:
			idle_for+=1
		time.sleep(60*CONF["wait_time"])

asyncio.run(looop_haha())#asyncio probably wasn't the best choice here but eh
