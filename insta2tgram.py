#!/usr/bin/python3
print("importing os,sys,io,json,time…")
import os,sys,io
import json,time

print("importing asyncio,commoncodes,fs…")
import asyncio
from commoncodes import CommonCode
from fs.memoryfs import MemoryFS

print("importing instalooter…")
from instalooter.looters import ProfileLooter, PostLooter
from instalooter.cli.login import login

print("importing aiogram…")
import aiogram
from aiogram import Bot,Dispatcher,executor,types,exceptions
from aiogram.utils import markdown

curdir=os.path.abspath(os.path.dirname(__file__))
conf_fp=os.path.join(curdir,"config.json")
sent_fp=os.path.join(curdir,"sent_links.json")

if os.path.exists(conf_fp):
	with open(conf_fp,"r") as f:
		CONF=json.load(f)
else:
	raise CommonCode(78,f"No config file found at {conf_fp}")

for key in ("tg_token","ig_usrname","ig_passwd","wait_time","chans"):
	if key not in CONF:
		raise CommonCode(78,f"Missing key in configuration: {key}")

CHANS=CONF["chans"]

if len(CHANS)<1:
	raise CommonCode(78,"At least one chan has to be specified")

for chan in CHANS:
	for key in ("tg_chat_id","ig_profile"):
		if key not in chan:
			raise CommonCode(78,f"Missing key in chan configuration: {key}")

if not os.path.exists(sent_fp):
	with open(sent_fp,"w+") as f:
		f.write("[]")

TG_TOKEN=CONF["tg_token"]
WAIT_TIME=CONF["wait_time"]
IG_USRNAME=CONF["ig_usrname"]
IG_PASSWD=CONF["ig_passwd"]

bot=Bot(token=TG_TOKEN)

print(f"Started bot with Telegram token \033[46m\033[36m{TG_TOKEN}\033[0m\nPolling every {WAIT_TIME} seconds\nlogged in as \033[46m\033[36m{IG_USRNAME}\033[0m:\033[46m\033[36m{IG_PASSWD}\033[0m")

async def update(tg_chatid,ig_profile):
	await bot.send_chat_action(tg_chatid,types.ChatActions.TYPING)
	pl=ProfileLooter(ig_profile)
	with open(sent_fp,"r") as f:
		sent=json.load(f)
	sent_something=False
	for media in pl.medias():
		i=media["id"]
		sc=media["shortcode"]
		if i not in sent:
			_pl=PostLooter(sc)
			info=_pl.get_post_info(sc)
			caption="\n".join(edge["node"]["text"] for edge in info["edge_media_to_caption"]["edges"])
			with MemoryFS() as fs:
				if media["is_video"]:
					print("got video",end=" ")
					await bot.send_chat_action(tg_chatid,types.ChatActions.RECORD_VIDEO)
					_pl.download_videos(fs,media_count=1)
					func=bot.send_video
					fn=fs.listdir("./")[0]
					await bot.send_chat_action(tg_chatid,types.ChatActions.UPLOAD_VIDEO)
				elif media["__typename"].lower()=="graphimage":
					print("got graphimage",end=" ")
					await bot.send_chat_action(tg_chatid,types.ChatActions.UPLOAD_PHOTO)
					_pl.download_pictures(fs,media_count=1)
					func=bot.send_photo
					fn=fs.listdir("./")[0]
				elif media["__typename"].lower()=="graphsidecar":
					print("got graphsidecar",end=" ")
					await bot.send_chat_action(tg_chatid,types.ChatActions.UPLOAD_PHOTO)
					_pl.download_pictures(fs)
					fn=tuple(fs.listdir("./"))
					if len(fn)==1:
						func=bot.send_photo
						fn=fn[0]
					else:
						func=bot.send_media_group
				else:
					await bot.send_message(tg_chatid,f"Oh-oh. I've encountered a new post type!\nPlease tell my developer, so he can tell me what I should do with a {media}.")
					print("\033[31mUNKNOWN MEDIA TYPE AAAAA\033[0m",media)
					break
				print(fn)
				if isinstance(fn,tuple):
					print("sending album…")
					f=[fs.openbin(_fn) for _fn in fn]
					_media=types.input_media.MediaGroup()
					for _f in f:
						_media.attach_photo(_f)
				else:
					print("sending file…")
					_media=f=fs.openbin(fn)
				if len(caption)>100:#telegram media captions have a character limit of 200 chars & I want to have a buffer
					caption=caption[:100]+"[…]"
				markdown.quote_html(caption)
				text=f"{caption}\n→<a href=\"https://www.instagram.com/p/{sc}\">original post</a>"
				try:
					if isinstance(fn,tuple):
						msg_id=(await func(tg_chatid,_media))[-1]["message_id"]
						await bot.send_message(tg_chatid,text,reply_to_message_id=msg_id,parse_mode=types.ParseMode.HTML)
					else:
						await func(tg_chatid,_media,caption=text,parse_mode=types.ParseMode.HTML)
				except exceptions.BadRequest as e:
					print("Got Bad Request while trying to send message. skipping…")
				except exceptions.RetryAfter as e:
					print("MEEP MEEP FLOOD CONTROL - YOU'RE FLOODING TELEGRAM\nstopping sending messages & waiting for next cycle…")
					break
				else:
					sent.append(i)
				if isinstance(f,list):
					for _f in f:
						_f.close()
				else:
					f.close()
			if not sent_something:
				sent_something=True
				print(f"@{ig_profile} → {tg_chatid}")
			print(f"Sent {i}/{sc}")
	with open(sent_fp,"w+") as f:
		json.dump(sent,f)
	return sent_something

print("loggin into instagram…")
login({"--username":CONF["ig_usrname"],"--password":CONF["ig_passwd"],"--quiet":False})

async def looop_haha():
	idle_for=0
	while True:
		print(f"UPDATE TIME {idle_for}")
		updated=False
		for chan in CHANS:
			if await update(chan["tg_chat_id"],chan["ig_profile"]):
				updated=True
		if updated:
			idle_for=0
		else:
			idle_for+=1
		for t in range(60*CONF["wait_time"]-1,-1,-1):
			mins,secs=divmod(t,60)
			print(f"{mins:02d}:{secs:02d}",end="\r")
			time.sleep(1)

print("running the main loop…")
asyncio.run(looop_haha())#asyncio probably wasn't the best choice here but eh
