#!/usr/bin/python
#-*-coding:utf-8 -*-

from bs4 import BeautifulSoup
import requests
import datetime
import time
from random import randint


theuseryoulike = 'input the user\'s name here'
inshomepageurl = 'https://www.instagram.com/' + theusername + '/'



def getmediatype(jsonfile):
    if jsonfile['graphql']['shortcode_media']['__typename']=='GraphVideo':
        return 'video'
    elif jsonfile['graphql']['shortcode_media']['__typename'] == "GraphSidecar":
        return 'multiplepic'
    else:
        return 'singlepic'

class Inspost(object):


    def __init__(self, tag ):    #tag是指最大的a tag: bs4.element.Tag
        hp = 'https://www.instagram.com'
        self.time = str((datetime.datetime.now()+datetime.timedelta(0, 28800)).strftime('%Y%m%d-%H%M%S-%f')) #convert UTC to +8 local time
        self.madiapath = str(tag.find('img')['src']) #thumbnail path
        self.dscrp = str(tag.find('img')['alt'])
        self.url = hp + str(tag['href']).split('/?taken-by='+ theusername)[0]
        # href会定向到弹窗而不是真正的帖子页面 所以需要去掉最后的taken-by
        self.jsonurl = self.url + '/?__a=1'
        self.getjson = requests.get(self.jsonurl, proxies = proxies, headers = headers).json()
        self.mediatype = getmediatype(self.getjson)
        if self.mediatype == 'multiplepic':
            self.hiddenpics = []
            for node in self.getjson['graphql']["shortcode_media"]["edge_sidecar_to_children"]['edges']:
                picurl = node['node']["display_resources"][-1]['src']
                self.hiddenpics.append(picurl)
        else:
            self.hiddenpics = self.getjson['graphql']["shortcode_media"]['display_resources'][-1]['src']
            # string





    def add_statuscode(self, code=None):
        self.statuscode = code

        # 方便后面确认上传后删除文件
        # 好像也不是很有必要

def getnewpost(newhp , oldhp):

    with open(oldhp,'r',encoding='utf-8') as oldhptxt:
        oldbs = BeautifulSoup(oldhptxt, "lxml")
    newbs = BeautifulSoup(newhp, 'lxml')


    old = [ Inspost(imge) for imge in oldbs.article.find_all('a')]
    new = [ Inspost(imge) for imge in newbs.article.find_all('a')]
    # list里面全是Inspost对象
    newpost = []
    for item in new:
        if item.url not in [olditem.url for olditem in old]:
            newpost.append(item)

    if not newpost:
        with open('/insta2weibo_bot/urllist', 'w') as f:
            for post in new:
                f.write(post.url+ '\t' + post.mediatype + '\t' + post.madiapath)
        print('There\'s no new post! at ' + str(datetime.datetime.now()+datetime.timedelta(0, 28800)))
        return None

    else:
        with open(oldhp, 'w', encoding='utf-8') as f:
            f.write(newhp)
        return newpost


def post_a_weibo(mediapath, status_content, mediaurl):
    # 发表文字微博的接口
    url_post_a_text = "https://api.weibo.com/2/statuses/share.json"

    inspost = mediaurl

    # 构建POST参数
    playload = {
        "access_token": "yourtokenhere",  # bot号的token
        "status": status_content + inspost,

    }

    file = {
        "pic": open(mediapath, 'rb')

    }

    r = requests.post(url_post_a_text, data=playload, files=file)
    time.sleep(randint(30,60))
    if r.status_code == 200:
        return r.status_code
    else:
        return r.json()['error']

# 请求ins主页

from selenium.webdriver import Firefox
from pyvirtualdisplay import Display

display = Display(visible=0, size=(800,600))
display.start()

opener = Firefox()   # open the browser

opener.get(inshomepageurl)
inshomepage = opener.page_source

opener.quit()
display.stop()   #quit the browser and the virtual display


oldhp = '/insta2weibo_bot/seeifinshatesme'
newpost = getnewpost(inshomepage, oldhp)


proxies={'http':'62.75.241.91:80'}
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'}


if newpost == None:
    raise SystemExit

#start downloading pictures

else:
    print('New post! at ' + str(datetime.datetime.now()+datetime.timedelta(0, 28800)))
    for post in newpost:
        if post.mediatype == 'singlepic':
            savepath = '/insta2weibo_bot/pics/' + post.time + '.jpg'
            status_description = post.dscrp[0:200] + '...'
            mediaurl = post.hiddenpics

            # download picture

            picrequests = requests.get(mediaurl, proxies = proxies, headers = headers)
            if picrequests.status_code == 200:
                with open(savepath, 'wb') as f:
                    f.write(picrequests.content)

            # post the weibo

            statuscode = post_a_weibo(savepath, status_description , post.url)
            if statuscode == 200:
                print('upload successfully!' + savepath)
            else:
                print(statuscode) #error meassage


        elif post.mediatype == 'video':
            savepath = '/insta2weibo_bot/videos/'+ post.time + '.mp4'
            thumbnailpath = '/insta2weibo_bot/videos/' + post.time + '-thumbnail.jpg'
            status_description = post.dscrp[0:200] + '...' + '(原视频在链接里哦)'
            mediaurl = post.piddenpics
            videourl = post.getjson['graphql']["shortcode_media"]["video_url"]

            # download thumbnail

            thumbnailr = requests.get(mediaurl, proxies=proxies, headers=headers)
            if thumbnailr.status_code == 200:
                with open(thumbnailpath, 'wb') as f:
                    f.write(thumbnailr.content)

            # download video
            videor = requests.get(videourl, proxies=proxies, headers=headers)
            if videor.status_code == 200:
                with open(savepath, 'wb') as f:
                    f.write(videor.content)

            statuscode = post_a_weibo(thumbnailpath, status_description, post.url)
            if statuscode == 200:
                print('upload successfully!' + thumbnailpath)
            else:
                print(statuscode)


        else: # when it's a multi-pic post



            for index in range(len(post.hiddenpics)): # loop every sub-file in the post
                mark = ' (%s/%s)' % (str(index + 1), str(len(post.hiddenpics) + 1))
                savepath = '/insta2weibo_bot/pics/' + post.time + '-' + str(index + 1) + '.jpg'
                status_description = post.dscrp[0:200] + '...' + mark
                mediaurl = post.hiddenpics[index]

                # download pictures

                picrequests = requests.get(mediaurl, proxies=proxies, headers=headers)
                if picrequests.status_code == 200:
                    with open(savepath, 'wb') as f:
                        f.write(picrequests.content)

                # post the weibo

                statuscode = post_a_weibo(savepath, status_description, post.url)
                if statuscode == 200:
                    print('upload successfully!' + savepath)
                else:
                    print(statuscode)



