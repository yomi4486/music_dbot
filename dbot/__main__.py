from __future__ import unicode_literals
import os,discord,asyncio,queue,requests,json,ffmpeg,random
from os.path import join, dirname
from dotenv import load_dotenv
from discord import app_commands
from yt_dlp import YoutubeDL
from apiclient import discovery
from bs4 import BeautifulSoup

# envを読むための設定なあああああああああああああああああああああああああああああああああああああああああああああああうんちいいいいいいいいいいいいいいいいいいいいいいいいいいいいいいいいいいい
load_dotenv(verbose=True)
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Youtube API settings
API_KEY = os.environ.get("YOUTUBE_API_KEY")
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

youtube = discovery.build(
    YOUTUBE_API_SERVICE_NAME,
    YOUTUBE_API_VERSION,
    developerKey=API_KEY
)

play_queue = queue.Queue()
audio_name = 'music_name'

TOKEN = os.environ.get("BOT_TOKEN")
APPLICATION_ID = os.environ.get("APPLICATION_ID")

ytdlp_options = {
    'format': 'bestaudio',
    'noplaylist': True,
    'quiet': True,
    'no_warnings':True,
    # 'extractaudio': True,
    'audioformat': 'wav',
}

client = discord.Client(intents = discord.Intents.all())
intents = discord.Intents.default()
intents.message_content = True
tree = app_commands.CommandTree(client)

def __get_audio_url__(url):
    with YoutubeDL(ytdlp_options) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']
        return audio_url

def YouTube_Search(Search_query:str,mode:int):
    """
    YouTube APIでURLの取得やキャッシュの書き込みを行います
    modeを2にすると検索とキャッシュの書き込み、返り値としてURLを返します。
    3にするとSearch_queryと関連性の高い動画のタイトルを返します。
    """
    global youtube
    if mode == 2:
        json_load = json.load(open('./cache.json', 'r',encoding="utf-8"))
        if f"{Search_query}" in json_load:
            youtube_url = str(json_load[f'{Search_query}']['url'])
            return youtube_url
        else:
            youtube_query = youtube.search().list(part='id,snippet',q=Search_query,type='video',maxResults=1,order='relevance',)
            youtube_response = youtube_query.execute()
            response = youtube_response.get('items', [])
            response = response[0]
            response_id = response["id"]
            video_id = response_id["videoId"]
            snippet = response["snippet"]
            youtube_title = snippet["title"]
            youtube_url = f'https://www.youtube.com/watch?v={video_id}'
            filename = __get_audio_url__(youtube_url)
            # JSONファイルを読み込む
            with open('./cache.json', 'r',encoding="utf-8") as file:
                data = json.load(file)
            # 読み込んだJSONデータをPythonの辞書に変換
            # これは前提としてJSONデータがオブジェクト（辞書）として始まっていることを前提としています
            # もしJSONデータが配列（リスト）から始まっている場合は、dataの要素に追加します
            # 例：data.append(new_data)
            data_as_dict = dict(data)
            # 新しい要素を辞書に追加
            new_data = {
                f"{Search_query}": {
                    "url":f"{youtube_url}",
                    "filename":f"{filename}",
                    "title":f"{youtube_title}"
                }
            }
            data_as_dict.update(new_data)
            # 更新された辞書をJSON形式に変換
            updated_json = json.dumps(data_as_dict, indent=4,ensure_ascii = False)
            # JSONファイルに新しいデータを書き込む
            with open('./cache.json', 'w',encoding="utf-8") as file:
                file.write(updated_json)
            return youtube_url
    elif mode == 3:
        with open('./cache.json', 'r',encoding="utf-8") as file:
            data = json.load(file)
        data_as_dict = dict(data)
        if f"{Search_query}" in data_as_dict:
            return data_as_dict[f"{Search_query}"]["title"]
        youtube_query = youtube.search().list(part='id,snippet',q=Search_query,type='video',maxResults=1,order='relevance',)
        youtube_response = youtube_query.execute()
        response = youtube_response.get('items', [])
        response = response[0]
        snippet = response["snippet"]
        lz_name = snippet["title"]
        return lz_name
    else:
        pass

def mutagen_length(path):
    try:
        probe = ffmpeg.probe(path)
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        duration = video_info['tags']['DURATION']
        
        return duration
    except Exception as e:
        print(f"Error: {e}")
        return 0

async def play_next(guild,Discordclient):
    # 再生キューから次の曲を取得
    if not play_queue.empty():
        global audio_name
        filename, audio_name = play_queue.get()
        await Discordclient(activity = discord.Activity(name=str(f"🎵 {audio_name}"), type=2))
        guild.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(source=filename,before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"),volume=0.2), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(guild,Discordclient), client.loop))
        return audio_name
    else:
        await Discordclient(activity = discord.CustomActivity(name=str('まだ何も再生されていません'), type=1))
        audio_name = ""


@client.event
async def on_ready():
    # この関数はBotの起動準備が終わった際に呼び出されます
    print('{0.user}'.format(client) ,"がログインしました",flush=True)
    await client.change_presence(activity = discord.CustomActivity(name=str('まだ何も再生されていません'), type=1))
    await tree.sync()#スラッシュコマンドを同期

# VCに誰もいなくなった時の処理
@client.event
async def on_voice_state_update(member, before, after):
    if before.channel is not None:
        # ただの人数カウントだからほかのBotがいる限りあまり意味をなさない
        if len(before.channel.members) == 1 and before.channel.members[0] == client.user:
            await before.channel.members[0].move_to(None)  

    
@tree.command(name="help",description="Botの説明を表示します。")
async def test_command(interaction: discord.Interaction):
    embed = discord.Embed(title="使用方法",description="基本的にはこのBotではコマンドを使用する必要はありません。")
    embed.add_field(name='概要', inline=False ,value='')
    embed.add_field(name='「@BMA 曲名」と送信すると、自動であなたがいるVCに参加し、指定の曲名の音楽を再生します。', value='')
    embed.add_field(name='コマンド（一般）', inline=False ,value='')
    embed.add_field(name='`/bye`', value='VCから退出させます（VCに人がいなくなったときに勝手に退出するので、普段は使用する必要はありません。）')
    embed.add_field(name='`/help`', value='Botの説明を表示します。')
    embed.add_field(name='`%url`', value='リクエストを送信したメッセージに対してリプライを行うと、再生した楽曲の詳細について教えてくれます。')
    embed.add_field(name='`/skip`', value='次の曲にスキップします。')
    embed.add_field(name='`/stop`', value='再生を停止します')
    embed.add_field(name='`/pause`', value='曲を一時停止します')
    embed.add_field(name='`/resume`', value='一時停止した曲を再開します')
    embed.add_field(name='コマンド（プレイリスト系）', inline=False ,value='')
    embed.add_field(name='`/create_playlist`', value='あなた専用のプレイリストを作成します。')
    embed.add_field(name='`/delete`', value='プレイリストを削除します。')
    embed.add_field(name='`/edit_playlist`', value='プレイリストの編集を行います。')
    embed.add_field(name='`/list_playlist`', value='作成したプレイリストをすべて表示します。')
    embed.add_field(name='`/reference_playlist`', value='指定したプレイリストを参照します')
    embed.add_field(name='`/remove`', value='編集中のプレイリストから指定の曲を削除します')
    embed.add_field(name='`/save_playlist`', value='プレイリストの編集を終了します。')

    await interaction.response.send_message(embed=embed,ephemeral=True)

@tree.command(name="bye",description="VCから退出させます（VCに人がいなくなったときに勝手に退出するので、普段は使用する必要はありません。）")
async def test_command(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message('このコマンドはDMでは使えません！',silent=True)
        return
    if interaction.guild.voice_client is None:
        await interaction.response.send_message("退出済みです",silent=True)
        return

    # 切断する
    await interaction.guild.voice_client.disconnect()
    await interaction.response.send_message("VCを退出します",silent=True)
    return

@tree.command(name="stop",description="再生を停止します。次の曲がある場合は、その曲にスキップします。通常は、リクエストメッセージを削除することで停止可能です。")
async def test_command(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message('このコマンドはDMでは使えません！',silent=True)
        return
    if interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.stop()
        if interaction.user.name == "makao1521":
            await interaction.response.send_message('# ばーかばーか\n(停止しました)',silent=True)
        else:
            await interaction.response.send_message(content='再生を停止しました！',delete_after=5,silent=True)
    else:
        await interaction.response.send_message(content='まだ何も再生されていません！',delete_after=5,silent=True)

@tree.command(name="pause",description="再生を一時停止します。再開する場合はresumeコマンドを実行してください")
async def pause_command(interaction: discord.Interaction):
    global audio_name
    if not interaction.guild:
        await interaction.response.send_message('このコマンドはDMでは使えません！',silent=True)
        return
    try:
        if interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            if interaction.user.name == "makao1521":
                await interaction.response.send_message('# ばーかばーか\n(一時停止しました)',silent=True)
            else:
                await interaction.response.send_message(content='再生を一時停止しました！',delete_after=5,silent=True)
            await client.change_presence(activity = discord.CustomActivity(name=str(f'⏯️ 一時停止中：{audio_name}'), type=1))
        else:
            await interaction.response.send_message(content='既に停止されています！',delete_after=5,silent=True)
    except:
        await interaction.response.send_message(content='現在何も再生されていません',delete_after=5,silent=True)
        

@tree.command(name="resume",description="再生を再開します。")
async def resume_command(interaction: discord.Interaction):
    global audio_name
    if not interaction.guild:
        await interaction.response.send_message('このコマンドはDMでは使えません！',silent=True)
        return
    if interaction.user.voice is None:
        await interaction.response.send_message("VCに参加してください",delete_after=5,silent=True)
        return
    elif interaction.guild.voice_client is None:
        await interaction.user.voice.channel.connect(self_deaf=True) # ボイスチャンネルに接続する
    elif interaction.guild.voice_client:
        pass
    else:
        await interaction.response.send_message("VCに参加できません",delete_after=5,silent=True)
        return
    try:
        if not interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.resume()
            if interaction.user.name == "makao1521":
                await interaction.response.send_message('# ばーかばーか\n(再開しました)',silent=True)
            else:
                await interaction.response.send_message(content='再開しました！',delete_after=5,silent=True)
            await client.change_presence(activity = discord.Activity(name=str(f"🎵 {audio_name}"), type=2))
        else:
            await interaction.response.send_message(content='既に再生されています！',delete_after=5,silent=True)
    except:
        await interaction.response.send_message(content='既に再生されているか、まだ一時停止されているものがありません',delete_after=5,silent=True)

@tree.command(name="create_playlist",description="あなた専用のプレイリストを作成します。")
async def create_command(interaction: discord.Interaction ,プレイリスト名:str):
    # JSONファイルを読み込む
    
    playlist_name = f"{interaction.user.id}.json"
    if not os.path.exists(f'./playlist/{playlist_name}'):
        f = open(f'./playlist/{playlist_name}', 'w',encoding="utf-8")
        f.write('{}')
        f.close()
    json_load = json.load(open(f'./playlist/{playlist_name}', 'r',encoding="utf-8"))
    if f"{プレイリスト名}" in json_load:
        await interaction.response.send_message(content=f'「{プレイリスト名}」というプレイリストは既に存在しています！ぜひ、`/editplaylist`で曲を追加してください！',silent=True)
        return
    
    with open(f'./playlist/{playlist_name}', 'r',encoding="utf-8") as file:
        data = json.load(file)
    # 読み込んだJSONデータをPythonの辞書に変換
    # これは前提としてJSONデータがオブジェクト（辞書）として始まっていることを前提としています
    # もしJSONデータが配列（リスト）から始まっている場合は、dataの要素に追加します
    # 例：data.append(new_data)
    data_as_dict = dict(data)
    # 新しい要素を辞書に追加
    new_data = {
        f"{プレイリスト名}":[]
    }
    data_as_dict.update(new_data)
    # 更新された辞書をJSON形式に変換
    updated_json = json.dumps(data_as_dict, indent=4,ensure_ascii = False)
    # JSONファイルに新しいデータを書き込む
    with open(f'./playlist/{playlist_name}', 'w',encoding="utf-8") as file:
        file.write(updated_json)
    await interaction.response.send_message(content=f'「{プレイリスト名}」というプレイリストを作成しました。\n`/editplaylist`でプレイリストを選択し、編集を開始してください！',silent=True)

@tree.command(name="edit_playlist",description="プレイリストの編集を行います。")
async def edit_playlist_command(interaction: discord.Interaction ,プレイリスト名:str):
    # JSONファイルを読み込む

    playlist_name = f"{interaction.user.id}.json"
    if not os.path.exists(f'./playlist/{playlist_name}'):
        os.mkdir(f'./playlist/{playlist_name}')
    json_load = json.load(open(f'./playlist/{playlist_name}', 'r',encoding="utf-8"))
    editlist = json.load(open(f'./playlist/editlist.json', 'r',encoding="utf-8")) 
    if f"{interaction.user.id}" in editlist:
        if editlist[f"{interaction.user.id}"]["edit"] == True:
            playlist_name = editlist[f"{interaction.user.id}"]["name"]
            await interaction.response.send_message(content=f'現在「{playlist_name}」というプレイリストの編集が続行中です。ほかのプレイリストを編集したい場合は、`/saveplaylist`で編集を終了してください。',delete_after=5,silent=True)
            return
    if not f"{プレイリスト名}" in json_load:
        await interaction.response.send_message(content=f'あなたは「{プレイリスト名}」というプレイリストを作成していません。\n`/createplaylist`で先にプレイリストを作成してください！',delete_after=5,silent=True)
        return
    
    with open(f'./playlist/editlist.json', 'r',encoding="utf-8") as file:
        data = json.load(file)
    # 読み込んだJSONデータをPythonの辞書に変換
    # これは前提としてJSONデータがオブジェクト（辞書）として始まっていることを前提としています
    # もしJSONデータが配列（リスト）から始まっている場合は、dataの要素に追加します
    # 例：data.append(new_data)
    data_as_dict = dict(data)
    # 新しい要素を辞書に追加
    new_data = {
        f"{interaction.user.id}":{
            "edit":True,
            "name":f"{プレイリスト名}" 
        }
    }
    data_as_dict.update(new_data)
    # 更新された辞書をJSON形式に変換
    updated_json = json.dumps(data_as_dict, indent=4,ensure_ascii = False)
    # JSONファイルに新しいデータを書き込む
    with open(f'./playlist/editlist.json', 'w',encoding="utf-8") as file:
        file.write(updated_json)
    await interaction.response.send_message(content=f'プレイリスト「{プレイリスト名}」の編集モードを開始します。いつも通りリクエストメッセージを送信すると、プレイリストに曲を追加します。`/saveplaylist`で編集を終了できます。',silent=True)

@tree.command(name="save_playlist",description="プレイリストの編集を終了します。")
async def save_playlist_command(interaction: discord.Interaction):
    # JSONファイルを読み込む

    playlist_name = f"{interaction.user.id}.json"
    if not os.path.exists(f'./playlist/{playlist_name}'):
        await interaction.response.send_message(content=f'プレイリストが編集モードになっていません。',delete_after=5,silent=True)
        return
    editlist = json.load(open(f'./playlist/editlist.json', 'r',encoding="utf-8"))
    if not editlist[f"{interaction.user.id}"]["edit"] == True:
        await interaction.response.send_message(content=f'プレイリストが編集モードになっていません。',delete_after=5,silent=True)
        return
    playlist_name = editlist[f"{interaction.user.id}"]["name"]
    with open(f'./playlist/editlist.json', 'r',encoding="utf-8") as file:
        data = json.load(file)
    # 読み込んだJSONデータをPythonの辞書に変換
    # これは前提としてJSONデータがオブジェクト（辞書）として始まっていることを前提としています
    # もしJSONデータが配列（リスト）から始まっている場合は、dataの要素に追加します
    # 例：data.append(new_data)
    data_as_dict = dict(data)
    # 新しい要素を辞書に追加
    #edit : 編集中であるかどうか
    #name : 何のプレイリストを編集しているのか
    new_data = {
        f"{interaction.user.id}":{
            "edit":False,
        }
    }
    data_as_dict.update(new_data)
    # 更新された辞書をJSON形式に変換
    updated_json = json.dumps(data_as_dict, indent=4,ensure_ascii = False)
    # JSONファイルに新しいデータを書き込む
    with open(f'./playlist/editlist.json', 'w',encoding="utf-8") as file:
        file.write(updated_json)
    
    await interaction.response.send_message(content=f'プレイリスト「{playlist_name}」の編集モードを終了します。',delete_after=5,silent=True)

@tree.command(name="remove",description="編集中のプレイリストから指定の曲を削除します")
async def remove_command(interaction: discord.Interaction ,曲名:str):
    if not os.path.exists(f'./playlist/{interaction.user.id}.json'):
        await interaction.response.send_message(content=f'プレイリストが編集モードになっていません。',delete_after=5,silent=True)
        return
    editlist = json.load(open(f'./playlist/editlist.json', 'r',encoding="utf-8"))
    if not editlist[f"{interaction.user.id}"]["edit"] == True:
        await interaction.response.send_message(content=f'プレイリストが編集モードになっていません。',delete_after=5,silent=True)
        return
    
    json_load = json.load(open(f'./playlist/{interaction.user.id}.json', 'r',encoding="utf-8"))
    try:
        playlist_name = editlist[f"{interaction.user.id}"]["name"]
        if f"{曲名}" in json_load[f"{playlist_name}"]:
            json_load[f"{playlist_name}"].remove(f"{曲名}")
            # 更新されたデータをJSON形式に変換
            updated_json = json.dumps(json_load, indent=4, ensure_ascii=False)
            # JSONファイルに更新データを書き込む
            with open(f'./playlist/{interaction.user.id}.json', 'w',encoding="utf-8") as file:
                file.write(updated_json)
            await interaction.response.send_message(content=f'プレイリスト「{playlist_name}」から「{曲名}」を削除しました。',delete_after=5,silent=True)
        else:
            await interaction.response.send_message(content=f'プレイリスト「{playlist_name}」には、「{曲名}」という曲は入っていません。',delete_after=5,silent=True)
    except Exception as e:
        await interaction.response.send_message(content=f'特殊なエラーが発生しました。プレイリストから曲を削除できませんでした')
        print(e,flush=True)
    
    

@tree.command(name="play",description="プレイリストを再生します。シャッフル再生する場合はオプションをTrueに設定してください。")
async def play_command(interaction: discord.Interaction, プレイリスト名:str,シャッフル:bool):
    # JSONファイルを読み込む
    global play_queue
    playlist_name = f"{interaction.user.id}.json"
    if not os.path.exists(f'./playlist/{playlist_name}'):
        await interaction.response.send_message(content=f'プレイリストがありません。',delete_after=5,silent=True)
        return
    editlist = json.load(open(f'./playlist/editlist.json', 'r',encoding="utf-8"))
    if editlist[f"{interaction.user.id}"]["edit"] == True:
        await interaction.response.send_message(content=f'プレイリストの編集を終了させてから再生を開始してください。',delete_after=5,silent=True)
        return
    json_load = json.load(open(f'./playlist/{playlist_name}', 'r',encoding="utf-8"))
    if f"{プレイリスト名}" in json_load:
        if interaction.user.voice is None:
            await interaction.response.send_message("先にVCに参加してください",delete_after=5,silent=True)
            return
        elif interaction.guild.voice_client is None:
            await interaction.user.voice.channel.connect(self_deaf=True) # ボイスチャンネルに接続する
        elif interaction.guild.voice_client:
            pass
        else:
            await interaction.response.send_message("VCに参加できません",delete_after=5,silent=True)
            return

        music_length = len(json_load[f"{プレイリスト名}"])

        if シャッフル:
            ns = []
            while len(ns) < music_length:
                n = random.randint(0, (music_length - 1))
                if not n in ns:
                    ns.append(n)
            await interaction.response.send_message(content=f'プレイリスト「{プレイリスト名}」から、{music_length}曲の楽曲をシャッフルしてお届けします！',delete_after=5,silent=True)
            i=0
            for w in ns:
                request_name = json_load[f"{プレイリスト名}"][w]
                try:
                    youtube_audio_name = str(json.load(open('./cache.json', 'r',encoding="utf-8"))[f'{request_name}']['title'])
                    yt_url = str(json.load(open('./cache.json', 'r',encoding="utf-8"))[f'{request_name}']['url'])
                except:
                    break
                filename = __get_audio_url__(url=yt_url)
                play_queue.put((filename,youtube_audio_name))
                
                if (not interaction.guild.voice_client.is_playing()) and i==0:
                    await play_next(interaction.guild,client.change_presence)
                i+=1
            
        else:
            await interaction.response.send_message(content=f'プレイリスト「{プレイリスト名}」から、{music_length}曲の楽曲をお届けします！',delete_after=5,silent=True)
            i=0
            for w in json_load[f"{プレイリスト名}"]:
                try:
                    youtube_audio_name = str(json.load(open('./cache.json', 'r',encoding="utf-8"))[f'{request_name}']['title'])
                    yt_url = str(json.load(open('./cache.json', 'r',encoding="utf-8"))[f'{request_name}']['url'])
                except:
                    break
                filename = __get_audio_url__(url=yt_url)
                play_queue.put((filename,youtube_audio_name))
                if (not interaction.guild.voice_client.is_playing()) and i==0:
                    await play_next(interaction.guild,client.change_presence)
                i+=1
        return
    else:
        await interaction.response.send_message(content=f'「{プレイリスト名}」というプレイリストは見つかりませんでした',delete_after=5,silent=True)
        return

@tree.command(name="reference_playlist",description="プレイリストを参照します")
async def reference_playlist_command(interaction: discord.Interaction, プレイリスト名:str):
    # JSONファイルを読み込む

    playlist_name = f"{interaction.user.id}.json"
    if not os.path.exists(f'./playlist/{playlist_name}'):
        await interaction.response.send_message(content=f'プレイリストがありません。',delete_after=5,silent=True)
        return
    json_load = json.load(open(f'./playlist/{playlist_name}', 'r',encoding="utf-8"))
    cache_json_load = json.load(open('./cache.json', 'r',encoding="utf-8"))
    if f"{プレイリスト名}" in json_load:
        music_length = len(json_load[f"{プレイリスト名}"])
        queue_list = "" 
        music_time = 0
        for w in json_load[f"{プレイリスト名}"]:
            music_name = cache_json_load[f"{w}"]["title"]
            queue_list = f"{queue_list}- {music_name}\n" 
            filename = str(json.load(open('./cache.json', 'r',encoding="utf-8"))[f'{w}']['filename'])
            
            if os.path.exists(f"./music/{filename}.webm"):
                length = mutagen_length(f"./music/{filename}.webm")
                music_time = (music_time + ((int(length[0:2]) * 3600) + (int(length[3:5]) * 60) + (int(length[6:8]))) )
                # print(f"{(length[0:2])}:{(length[3:5])}:{(length[6:8])}",flush=True)
            else:
                length = mutagen_length(f"./music/{filename}.mkv")
                try:
                    music_time = (music_time + ((int(length[0:2]) * 3600) + (int(length[3:5]) * 60) + (int(length[6:8]))) )
                except:
                    music_time = music_time
            music_time_min = (music_time // 60)
            music_time_sec = (music_time % 60)


        await interaction.response.send_message(content=f'## {プレイリスト名}\n{queue_list}\n全{music_length}曲・{str(music_time_min)}分{str(music_time_sec)}秒',silent=True,ephemeral=True)
        return
    else:
        await interaction.response.send_message(content=f'「{プレイリスト名}」というプレイリストは見つかりませんでした',delete_after=5,silent=True)
        return

@tree.command(name="delete_playlist",description="プレイリストを削除します。")
async def delete_playlist_command(interaction: discord.Interaction, プレイリスト名:str):
    editlist = json.load(open(f'./playlist/editlist.json', 'r',encoding="utf-8"))
    if editlist[f"{interaction.user.id}"]["edit"] == True:
        await interaction.response.send_message(content=f'プレイリストの編集を終了させてからコマンドを実行してください。',delete_after=5,silent=True)
        return

    playlist_name = f"{interaction.user.id}.json"
    if not os.path.exists(f'./playlist/{playlist_name}'):
        await interaction.response.send_message(content=f'プレイリストがありません。',delete_after=5,silent=True)
        return
    json_load = json.load(open(f'./playlist/{playlist_name}', 'r',encoding="utf-8"))
    if f"{プレイリスト名}" in json_load:
        del json_load[f"{プレイリスト名}"]
        # 更新されたデータをJSON形式に変換
        updated_json = json.dumps(json_load, indent=4, ensure_ascii=False)
        # JSONファイルに更新データを書き込む
        with open(f'./playlist/{playlist_name}', 'w',encoding="utf-8") as file:
            file.write(updated_json)
        await interaction.response.send_message(content=f'プレイリスト「{プレイリスト名}」を削除しました。',delete_after=5,silent=True)
        return
    else:
        await interaction.response.send_message(content=f'「{プレイリスト名}」というプレイリストは既に削除されているか、見つかりませんでした',delete_after=5,silent=True)
        return

@tree.command(name="list_playlist",description="作成したプレイリストをすべて表示します。")
async def list_playlist_command(interaction: discord.Interaction):
    playlist_name = f"{interaction.user.id}.json"
    if not os.path.exists(f'./playlist/{playlist_name}'):
        await interaction.response.send_message(content=f'プレイリストがありません。',delete_after=5,silent=True)
        return
    json_load = json.load(open(f'./playlist/{playlist_name}', 'r',encoding="utf-8"))
    queue_list = ""
    for w in json_load:
        queue_list = f"{queue_list}- {w}\n" 
    await interaction.response.send_message(content=f'## プレイリスト一覧\n{queue_list}',silent=True)

@tree.command(name="clear",description="キューを空にします")
async def clear_command(interaction: discord.Interaction):
    global play_queue
    index = 0
    while not play_queue.empty():
        play_queue.get()
        index +=1
    if index == 0:
        await interaction.response.send_message("キューに曲は入っていません。",delete_after=5)
    else:
        await interaction.response.send_message(f"キューに入っている{index}曲を削除しました")

@client.event
async def on_message_delete(message:discord.Message):
    if message.guild.voice_client is None:
        return
    if f'<@{APPLICATION_ID}>' in message.content and message.guild.voice_client.is_playing():
        global audio_name
        message_content = message.content.replace(f'<@{APPLICATION_ID}> ','').replace(f'<@{APPLICATION_ID}>','')
        json_load = json.load(open('./cache.json', 'r',encoding="utf-8"))
        try:
            if audio_name == json_load[f'{message_content}']["title"]:
                message.guild.voice_client.stop()
                if message.author.name == "makao1521":
                    await message.channel.send(f'<@{message.author.id}> \n# ばーかばーか\n(再生を停止しました)',silent=True)
                else:
                    await message.channel.send(content='リクエストメッセージが削除されたため、再生を停止しました！',delete_after=5,silent=True)
        except:
            pass
@client.event
async def on_message(message:discord.Message):
    # メッセージの送信者がbotだった場合は無視する
    if message.author.bot:
        return

    if message.author != client and message.content == '%url':
        if not message.guild:
            await message.reply('このコマンドはDMでは使えません！',silent=True)
            return
        msg = None
        # リプライ元のメッセージを取得。取得に失敗した場合はリプライをしていないため、使い方のアドバイスを返す
        try:
            msg = await message.channel.fetch_message(message.reference.message_id)
        finally:
            if msg == None:
                try:
                    global audio_name
                    if audio_name == "":
                        embed = discord.Embed(title="このコマンドは、リクエストメッセージにリプライするか、楽曲が再生されているときに使用する必要があります！",description="リクエストメッセージとは、「@BMA 曲名」というフォーマットのメッセージのことです。",color=0xff0000)
                        await message.reply(embed=embed,silent=True)
                        return
                    if message.guild.voice_client.is_playing():
                        # JSONデータをパースしてリストに変換
                        json_load = json.load(open('./cache.json', 'r',encoding="utf-8"))
                        for k,v in json_load.items():
                            if audio_name == json_load[f"{k}"]["title"]:
                                await message.reply(f'{v["url"]}',silent=True)
                                return
                except:
                    embed = discord.Embed(title="このコマンドは、リクエストメッセージにリプライするか、楽曲が再生されているときに使用する必要があります！",description="リクエストメッセージとは、「@BMA 曲名」というフォーマットのメッセージのことです。",color=0xff0000)
                    await message.reply(embed=embed,silent=True)
                return

        # ベータじゃない方のBMAに対するURLコマンドは無視
        if "<@1176875616272920616>" in msg.content :
            return

        if not f'<@{APPLICATION_ID}>' in msg.content:
            embed = discord.Embed(title="このコマンドは、リクエストメッセージにリプライして使用する必要があります！",description="リクエストメッセージとは、「@BMA 曲名」というフォーマットのメッセージのことです。",color=0xff0000)
            await message.reply(embed=embed,silent=True)
            return
        elif f'<@{APPLICATION_ID}>' in msg.content:
            query_words = msg.content.replace(f'<@{APPLICATION_ID}> ','').replace(f'<@{APPLICATION_ID}>','')
            
            json_load = json.load(open('./cache.json', 'r',encoding="utf-8"))
            if not f"{query_words}" in json_load:
                await message.reply("そのような曲は見つかりませんでした。再生に失敗したか、メッセージが編集されている可能性があります。")
                return
            audio_name = str(json_load[f'{query_words}']['title'])
            OpenURL = YouTube_Search(query_words,2)
            await message.reply(f'{OpenURL}',silent=True)
            return
        else:
            embed = discord.Embed(title="このコマンドは、リクエストメッセージにリプライして使用する必要があります！",description="リクエストメッセージとは、「@BMA 曲名」というフォーマットのメッセージのことです。",color=0xff0000)
            await message.reply(embed=embed,silent=True)
            return
    #urlコマンド終わり

    # 音声再生
    if f'<@{APPLICATION_ID}>' in message.content:
        temp_audio_name = message.content.replace(f'<@{APPLICATION_ID}> ','').replace(f'<@{APPLICATION_ID}>','')
        if temp_audio_name.replace(' ','') == '':
            await message.reply('こんにちは！使い方を知りたい場合は、`/help`コマンドを実行してください！',silent=True)
            return
        editlist = json.load(open(f'./playlist/editlist.json', 'r',encoding="utf-8"))
        async def get_audio_source(url,cached_text):
            """
            ## YoutubeのURLから実際のオーディオが保存されているURLを返却する関数です。
            args:
                url=YouTubeの動画URL(例：https://www.youtube.com/watch/?v=xxxx)
            """

            # cache = json.load(open(f'./cache.json', 'r',encoding="utf-8"))
            # if f"{cached_text}" in cache:
            #     return cache[f"{cached_text}"]["filename"]

            with YoutubeDL(ytdlp_options) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                    audio_url = info['url']
                    return audio_url
                except:
                    await message.reply("この曲を再生することはできません。")
                    return ""

        if f"{message.author.id}" in editlist:        
            if editlist[f"{message.author.id}"]["edit"] == True:
                playlist_name = editlist[f"{message.author.id}"]["name"]
                with open(f'./playlist/{message.author.id}.json', 'r',encoding="utf-8") as file:
                    data = json.load(file)
                # 読み込んだJSONデータをPythonの辞書に変換
                # これは前提としてJSONデータがオブジェクト（辞書）として始まっていることを前提としています
                # もしJSONデータが配列（リスト）から始まっている場合は、dataの要素に追加します
                # 例：data.append(new_data)
                data_as_dict = dict(data)
                data_as_dict[playlist_name].append(f"{temp_audio_name}")
                # 更新された辞書をJSON形式に変換
                updated_json = json.dumps(data_as_dict, indent=4,ensure_ascii = False)
                # JSONファイルに新しいデータを書き込む

                if "www.youtube.com/watch?v=" in message.content or "https://youtu.be/" in message.content:
                    try:
                        youtube_url = temp_audio_name
                        response = requests.get(youtube_url)
                        youtube_title = str(BeautifulSoup(response.text, "html.parser").find("title")).replace(" - YouTube","").replace("<title>","").replace("</title>","")
                    except:
                        await message.reply("楽曲の取得に失敗しました！",silent=True,delete_after=5)
                        return
                else:
                    youtube_url = YouTube_Search(temp_audio_name,2) # ダウンロードとURLの取得
                    youtube_title = YouTube_Search(temp_audio_name,3)
                with open(f'./playlist/{message.author.id}.json', 'w',encoding="utf-8") as file:
                    file.write(updated_json)
                try:
                    image_url = str(BeautifulSoup(response.text, "html.parser").find("meta", property="og:image"))
                    embed = discord.Embed(title=f"{youtube_title}",color=0xff00ff)
                    embed.set_thumbnail(url=f"{image_url}")
                    await message.reply(f'楽曲を「{playlist_name}」に追加しました！',silent=True,delete_after=5,embed=embed) # ここにサムネイルを乗せたembedを追加
                except:
                    await message.reply(f'楽曲を「{playlist_name}」に追加しました！',silent=True,delete_after=5) # ここにサムネイルを乗せたembedを追加
                return
            
# ここまでプレイリスト系の処理=======================================ﾔﾏｵﾘ===========================================================================================
        
        temp_audio_name = temp_audio_name.replace('\n','')
        try:
            if message.author.voice is None:
                await message.reply("先にVCに参加してください",silent=True)
                return

            elif message.guild.voice_client is None:
                await message.author.voice.channel.connect(self_deaf=True) # ボイスチャンネルに接続する
            elif message.guild.voice_client:
                pass
            else:
                await message.reply("VCに参加できません",silent=True)
                return
        except Exception as e:
            if not message.guild:
                await message.reply("DMではリクエストを行うことができません！\n利用可能なVCに参加した状態でサーバーからリクエストしてください！")
                return
            else:
                print(e,flush=True)
                await message.reply("例外的なエラーが発生しました！")
        
        if "www.youtube.com/watch?v=" in f"{message.content}" or "music.youtube.com/watch?v=" in f"{message.content}":
            try:
                youtube_url = temp_audio_name
                response = requests.get(youtube_url)
                youtube_title = str(BeautifulSoup(response.text, "html.parser").find("title")).replace(" - YouTube","").replace("<title>","").replace("</title>","")
            except:
                await message.reply("楽曲の取得に失敗しました！",silent=True,delete_after=5)
                return
        else:
            youtube_url = YouTube_Search(temp_audio_name,2) # ダウンロードとURLの取得
            youtube_title = YouTube_Search(temp_audio_name,3)
        
        # if youtube_url == None:
        #     await message.reply(f'「{audio_name}」という曲は見つかりませんでした...\nアーティスト名などを含めてリクエストすると見つかるかもしれません！',silent=True)
        #     return

        filename = await get_audio_source(url=youtube_url,cached_text=temp_audio_name)
        # 再生キューに追加
        play_queue.put((filename,youtube_title))

        # 再生中でなければ音楽を再生
        if not message.guild.voice_client.is_playing():
            await play_next(message.guild,client.change_presence)
        
        try:
            response = requests.get(youtube_url)
            youtube_title = str(BeautifulSoup(response.text, "html.parser").find("title")).replace(" - YouTube","").replace("<title>","").replace("</title>","")
            image_url = str(BeautifulSoup(response.text, "html.parser").find("meta", property="og:image").get("content"))
            embed = discord.Embed(title=f"{youtube_title}",color=0xff00ff)
            embed.set_image(url=f"{image_url}")
            await message.reply(embed=embed,silent=True,delete_after=5)
        except Exception as e:
            print(e)

client.run(TOKEN)