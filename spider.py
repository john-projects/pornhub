# -*- coding:utf-8 -*-
# __author__: MaoYong
import re
import requests
import json
from bs4 import BeautifulSoup
from mysql_db import Mysql
import os
import datetime
from pymysql.err import IntegrityError
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(thread)d %(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='pornhub_spider.log',
                    filemode='a')
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

mysql = Mysql()


class SpiderPornhub(object):
    def __init__(self):
        self.index_url = "https://www.pornhub.com"
        self.url = "https://www.pornhub.com/video"
        self.secondary_page_limit = 10
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/48.0.2564.116 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip',
            'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6,zh-TW;q=0.4'
        }

    # 根据得到的二级页面url，爬取二级页面上前secondary_page_limit页的所有视频信息，并将其保存入库
    def main(self, secondary_page_dict):
        for video_type, secondary_page_url in secondary_page_dict.items():
            print "video_type:", video_type
            print "secondary_page_url:", secondary_page_url
        
            for limit in xrange(self.secondary_page_limit):
                exists_view_key = self._get_all_view_key()
                print limit
                html_source = self._get_html_source(url=secondary_page_url + "&page=" + str(limit + 1))
                
                if not html_source:
                    continue
                soup = BeautifulSoup(html_source.content, "html.parser")

                video_info_list = []
                video_info_div_list = soup.find_all("div", "img")
                for video_info_div in video_info_div_list:
                    view_key = re.search(r"viewkey=(\w*)", video_info_div.a.get("href")).group(1)
                    if view_key in exists_view_key:
                        continue
                    try:
                        name = video_info_div.a.get("title").encode("utf8")
                        duration = video_info_div.div.var.get_text().encode("utf8")
                        video_info_dict = self.get_video_info_dict(self.index_url + video_info_div.a.get("href"))
                        quality = video_info_dict.get("quality", '')
                        size = video_info_dict.get("size", '')
                        url = video_info_dict.get("url", '')
                        cover_url = video_info_div.a.img.get("data-image")
                        if not cover_url:
                            cover_url = video_info_div.a.img.get("data-mediumthumb")
                        cover_url = cover_url.encode("utf8")
                        cover_name = self.save_cover(cover_url, video_type, view_key)

                        mediabook_url = video_info_div.a.img.get("data-mediabook").encode("utf8")
                        mediabook_name = self.save_mediabook(mediabook_url, video_type, view_key)

                    except AttributeError as err:
                        logging.warning(err)
                        continue

                    video_info_list.append([
                        video_type, name, view_key, quality, size, duration, cover_name, mediabook_name
                    ])
                    datetime_now = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime(
                        "%Y-%m-%d %H:%M:%S")

                    print "%s view_key: %s included success!" % (datetime_now, view_key)
                    with open("./video_info.txt", "a") as fp:
                        fp.write("*" * 100 + "\n")
                        fp.write(str(datetime_now) + "  type     :" + video_type + "\n")
                        fp.write(str(datetime_now) + "  title    :" + name + "\n")
                        fp.write(str(datetime_now) + "  viewkey  :" + view_key + "\n")
                        fp.write(str(datetime_now) + "  cover    :" + cover_name + "\n")
                        fp.write(str(datetime_now) + "  mediabook:" + mediabook_name + "\n")
                        fp.write(str(datetime_now) + "  duration :" + duration + "\n")
                        fp.write(str(datetime_now) + "  quality  :" + quality + "\n")
                        fp.write(str(datetime_now) + "  size     :" + size + "\n")
                        fp.write(str(datetime_now) + "  url      :" + url + "\n")
    
                self._insert_info(video_info_list)

        # return video_info_dict_list

    # 获取网页源代码
    def _get_html_source(self, url):
        try:
            result = requests.get(url=url, headers=self.headers, timeout=5, stream=True)
        except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError) as err:
            logging.warning(err)
            return False

        # print result 
        return result

    # 获取二级页面
    def get_secondary_page_dict(self):
        html_source = self._get_html_source(url=self.url)
        if not html_source:
            return {}
        soup = BeautifulSoup(html_source.content, "html.parser")

        navigation_a = soup.find_all("a", "sidebarIndent")
        secondary_page_dict = {}
        for info in navigation_a:
            secondary_page_dict[info.get("data-mxptext")] = self.index_url + info.get("href")
        return secondary_page_dict

    # 根据视频的 url 获取视频的详细信息
    def get_video_info_dict(self, video_url):
        html_source = self._get_html_source(url=video_url)
        if not html_source:
            return {}

        video_info_obj = re.search(r'disable_sharebar(.*?)mediaDefinitions":\[(.*?)\]', html_source.content)

        if not video_info_obj:
            return {}
        video_info = video_info_obj.group(2)
        video_info_list = json.loads('[' + video_info + ']')
        video_info_dict = {}
        # 获取该视频下所有清晰度的视频url
        # for video_info in video_info_list:
        #     if not video_info["videoUrl"]:
        #         continue
        #     video_response = requests.get(url=video_info["videoUrl"], headers=self.headers, stream=True, timeout=5)
        #     video_size = video_response.headers["content-length"]
        #     video_info_dict[video_info["quality"] + "url"] = video_info["videoUrl"]
        #     video_info_dict[video_info["quality"] + "size"] = str(int(video_size)/1024.0//1024) + "M"

        # 获取该视频下最高清晰度的视频url
        best_quality = 0
        for video_info in video_info_list:
            if not video_info["videoUrl"]:
                continue
            if int(video_info["quality"]) > best_quality:
                best_quality = int(video_info["quality"])
                video_info_dict = {
                    "quality": video_info["quality"],
                    "url": video_info["videoUrl"],
                }
        html_source = self._get_html_source(url=video_info_dict.get("url"))
        if not html_source:
            return {}

        video_size = html_source.headers["content-length"]
        video_info_dict["size"] = "%.2fM" % (float(video_size)/1024/1024)

        return video_info_dict

    # 获取已经数据库中已经爬取到的所有 view_key
    @staticmethod
    def _get_all_view_key():
        sql = 'SELECT view_key FROM video_info'
        results = mysql.get_all(sql)
        all_view_keys = [result.values()[0] for result in results]
        return all_view_keys

    # 将爬取到的视频信息批量存储到数据库
    @staticmethod
    def _insert_info(video_info_list):
        sql = 'INSERT INTO video_info(`type`, `name`, `view_key`, `quality`, `size`, `duratuib`, `cover`, ' \
              '`mediabook`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)'
        try:
            mysql.insert_many(sql, video_info_list)
            mysql.end()
        except IntegrityError as err:
            logging.warning(err)

    # 根据封面url下载封面，返回下载后的封面path
    def save_cover(self, cover_url, video_type, view_key):
        img_path = "./cover_img/%s/" % video_type
        img_name = img_path + "%s.jpg" % view_key
        if not os.path.exists(img_path):
            os.makedirs(img_path)

        html_source = self._get_html_source(url=cover_url)
        if not html_source:
            return ''

        if html_source.status_code == 200:
            with open(img_name, "wb") as fp:
                fp.write(html_source.content)
            return img_name
        
        return ''

    # 根据视频预告url下载视频预告，返回下载后的视频预告path
    def save_mediabook(self, mediabook_url, video_type, view_key):
        mediabook_path = "./mediabook_video/%s/" % video_type
        mediabook_name = mediabook_path + "%s.webm" % view_key
        if not os.path.exists(mediabook_path):
            os.makedirs(mediabook_path)

        html_source = self._get_html_source(url=mediabook_url)
        if not html_source:
            return ''

        chunk_size = 10240
        if html_source.status_code == 200:
            with open(mediabook_name, "wb") as fp:
                for data in html_source.iter_content(chunk_size=chunk_size):
                    fp.write(data)
            return mediabook_name

        return ''

    # 运行
    def run(self):
        secondary_page_dict = self.get_secondary_page_dict()
        print len(secondary_page_dict)
        self.main(secondary_page_dict)

        # for video_type, video_type_url in secondary_page_dict.items():

        # video_type_url = secondary_page_dict.get("Babe")
        # print video_type_url
        # self.get_video_info(video_type_url)


if __name__ == "__main__":
    spider_pornhub = SpiderPornhub()
    spider_pornhub.run()
