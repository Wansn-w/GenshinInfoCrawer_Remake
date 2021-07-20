import json
import re

import requests
from bs4 import BeautifulSoup as bs

list_page_url = 'https://bbs.mihoyo.com/ys/obc/channel/map/189/'
item_type = ["characters", "weapons", "artifacts", "monsters", "foods", "bag", "activities", "tasks", "animals",
             "books", "quests", "NPC", "domains", "teapot", "abyss", "namecard", "equipments"]


def get_all_items(url):
    html_tmp = requests.get(url).text
    soup_tmp = bs(html_tmp, 'html.parser')
    items_table_tmp = soup_tmp.find_all('li', {"class": "swiper-slide position-list__tab-content"})
    all_list = {}
    for i, j in enumerate(items_table_tmp):
        items_tmp = j.find_all('li', {"class": "position-list__item"})
        item_list_tmp = {}
        for m in items_tmp:
            a_tmp = m.find('a')
            item_list_tmp[a_tmp.get('title')] = {
                "image": a_tmp.find('img').get('data-src'),
                "url": "https://bbs.mihoyo.com/{}".format(a_tmp.get('href'))
            }
        all_list[item_type[i]] = item_list_tmp
    return all_list


def character(url):
    html_tmp = requests.get(url).text
    soup_tmp = bs(html_tmp, 'html.parser')
    divs = {}
    for i in soup_tmp.find_all('div', {"class": "obc-tmpl-character"}):
        divs[i.get('data-part')] = i
    character_dict = {
        "名字": divs['main'].next.get_text(),
        "信息": {},
        "基础属性": {},
        "角色突破": {},
        "命之座": {},
        "天赋": {},
        "语音": {},
        "故事": {},
        "展示": {}
    }

    # 展示
    painting_list_raw, painting_main_raw = divs['painting'].find_all('ul')
    for i, btn in enumerate(painting_list_raw.contents):
        character_dict['展示'][btn.get_text().strip()] = painting_main_raw.contents[i].next['src']

    # 角色信息
    info = divs['main'].find('table')
    main_describe = divs['describe'].find('tbody')
    character_dict['信息'] = {
        "头像": info.find('img').get('src'),
        "生日": main_describe.next.contents[2].text,
        "称号": main_describe.next.contents[6].text
    }
    try:
        character_info_part1, character_info_part2 = info.find_all('tbody')
        for i in character_info_part1:
            character_dict['信息'][i.contents[2].get_text()] = i.contents[4].get_text()
        character_dict['信息']['名片'] = character_info_part2.contents[1].find('img').get('src')
        character_dict['信息']['特殊料理'] = {
            "图片": character_info_part2.contents[2].find('img').get('src'),
            "名字": character_info_part2.contents[2].find('a').get_text(),
            "链接": character_info_part2.contents[2].find('a').get('href')
        }
    except AttributeError:
        pass

    # 语音
    character_dict['语音']['声优'] = {}
    cvs = character_info_part2.contents[3].contents[2].contents[:4]
    for cv in cvs:
        lang, cv_name = cv.get_text().split('：')
        character_dict['语音']['声优'][lang] = cv_name
    audio_page_url = "https://bbs.mihoyo.com{}?bbs_presentation_style=no_header" \
        .format(character_info_part2.contents[3].find('a', {"data-type": "obc-content"}).get('href'))
    audio_page_html = requests.get(audio_page_url).text
    audio_page_soup = bs(audio_page_html, 'html.parser')
    audio_list = audio_page_soup.find_all('div', {"data-part": "main"})
    character_dict['语音']['语音'] = {}
    for i in audio_list:
        tmp = i.find_all('div')
        audio_title = tmp[0].text
        audio_text = tmp[1].text
        character_dict['语音']['语音'][audio_title] = {
            "文本": audio_text,
            "链接": i.find('source').get('src')
        }

    # 基础属性
    base_list = divs['basicAttr'].find('tbody').find_all('tr')
    for i in base_list:
        character_dict['基础属性'][i.find_all('td')[0].text] = i.find_all('td')[1].text.strip()

    # 角色突破
    ascend_type_list = ['20级突破', '40级突破', '50级突破', '60级突破', '70级突破', '80级突破', '90级属性']
    ascend_main_lis = divs['breach'].find('ul', {"class": "obc-tmpl__switch-list"}).find_all('li')
    for i, j in enumerate(ascend_main_lis):
        type_index_num = ascend_type_list[(i + 1) // 5]
        for m, n in enumerate(j.find_all('tr')):
            # 突破材料
            if m == 0:
                character_dict['角色突破'][type_index_num] = {
                    "突破材料": {},
                }
                if '无' in n.find('li').text:
                    continue
                for material_li in n.find_all('li'):
                    material = material_li.find('a').text
                    character_dict['角色突破'][type_index_num]['突破材料'][material.split('*')[0]] = {
                        "数量": material.split('*')[1],
                        "图片链接": material_li.find('img').get('src')
                    }
                continue
            # 其它突破信息
            ascend_infos = n.find_all('td')
            if ascend_infos[0].text == '新天赋解锁':
                character_dict['角色突破'][type_index_num]["新天赋解锁"] = {
                    "天赋": ascend_infos[1].text,
                    "图标链接": ascend_infos[1].find('img').get('src')
                }
                continue
            character_dict['角色突破'][type_index_num][ascend_infos[0].text] = ascend_infos[1].text.strip()
            character_dict['角色突破'][type_index_num][ascend_infos[2].text] = ascend_infos[3].text.strip()

    # 命之座
    for c in divs['life'].find('tbody').find_all('tr'):
        constellation_tds = c.find_all('td')
        character_dict['命之座'][constellation_tds[0].text.strip()] = {
            "图标": constellation_tds[0].find('img').get('src'),
            "激活素材": constellation_tds[1].text.strip(),
            "介绍": constellation_tds[2].text.strip()
        }

    # 天赋
    talent_type_list = \
        [i.text.strip() for i in divs['skill'].find('ul', {"class": "obc-tmpl__switch-btn-list"}).find_all('li')]

    talents_html = divs['skill'].find('ul', {"class": "obc-tmpl__switch-list"}).find_all('li')
    for i, j in enumerate(talents_html):
        character_dict['天赋'][talent_type_list[i]] = {
            "名称": j.next.text.strip(),
            "图标": j.find('img').get('src'),
            "介绍": j.find('pre').text.strip()
        }
        if i in range(3):

            character_dict['天赋'][talent_type_list[i]]['属性'] = {}
            talent_attribute_head = [a.text.strip() for a in j.find('thead').find_all('th')][1:]
            for lvl in talent_attribute_head:
                character_dict['天赋'][talent_type_list[i]]['属性'][lvl] = {}
            for tr in j.find('tbody').find_all('tr'):
                attributes_part_title = tr.next.text.strip()
                attributes_part_tds = [td.text.strip() for td in tr.contents[2:]]
                for pos, lvl in enumerate(talent_attribute_head):
                    character_dict['天赋'][talent_type_list[i]]['属性'][lvl][attributes_part_title] = \
                        attributes_part_tds[pos]
            continue

    # 故事
    story_html = soup_tmp.find_all('div', {"class": "obc-tmpl__part--fold"})
    for s in story_html:
        title = s.find('div', {"class": "obc-tmpl-fold__title"}).find('p').text.strip()
        desc_html = s.find('div', {"class": "obc-tmpl__paragraph-box"}).find_all('p')
        desc = ''
        for d in desc_html:
            desc += f'{d.text}/n'
        character_dict['故事'][title] = desc

    return character_dict


def weapon(url):
    html_tmp = requests.get(url).text
    soup_tmp = bs(html_tmp, 'html.parser')
    equipment_div_html = soup_tmp.find('div', {"class": "obc-tmpl-equipment"}).find_all('div')
    divs = {}
    # for i in equipment_div_html:  # Are def weapon(url):
    html_tmp = requests.get(url).text
    soup_tmp = bs(html_tmp, 'html.parser')
    equipment_div_html = soup_tmp.find('div', {"class": "obc-tmpl-equipment"}).find_all('div')
    divs = {}
    for i in equipment_div_html:  # Are you already in？
        # divs[i.get('data-part')] =
        divs[i.get('data-part')] = i
    weapon_dict = {
        "名称": divs['main'].find('tbody').find_all("tr")[0].text[4:],
        "类型": divs['main'].find_all("tr")[1].text[5:],  # 善用评估表达式 alt+f8
        "星级": len(divs['main'].find_all("tr")[2].find_all("i")),
        "图标": divs['main'].find_all("tr")[0].find("td").find("img").attrs["src"],
        "装备描述": {
            "阶数": re.sub("[\u4e00-\u9fa5·](\d.*%)[\u4e00-\u9fa5·]", "",
                         divs['description'].find("td").find_all("p")[0].text),
            "功能": {},
            "介绍": divs['description'].find("td").find_all("p")[2].text
        },
        "获取途径": divs['description'].find_all("td")[1].text[5:],
        "成长数值": []
    }

    # 描述
    description = divs['description'].find("td").find_all("p")[1].text.split("·")
    weapon_dict["装备描述"]["功能"]["名称"] = description[0].replace(" ", "")
    weapon_dict["装备描述"]["功能"]["描述"] = description[1].replace(" ", "")

    # 成长数值
    levels = soup_tmp.find("div", style="order: 2;").find("ul").find_all("li")
    for level in levels:
        weapon_dict["成长数值"].append({
            "等级": level.text.replace("\n", "").replace(" ", "")
        })
    numerical_value_tmp = list(soup_tmp.find("div", style="order: 2;").find_all("ul")[1].find_all("li"))
    numerical_value_tmp.insert(0, "占位符 Placeholder")
    numerical_value = [numerical_value_tmp[i:i + 6] for i in range(0, len(numerical_value_tmp), 6)]
    for m, l in enumerate(numerical_value):
        for n, i in enumerate(l):
            if m == 0:
                if n == 0 or n == 1:
                    continue
                elif n == 2:
                    weapon_dict["成长数值"][m]["初始基础数值"] = {}
                    weapon_dict["成长数值"][m]["初始基础数值"]["基础攻击力"] = i.text[7:]
                elif n == 3:
                    weapon_dict["成长数值"][m]["初始基础数值"]["攻击力"] = i.text[5:]
                elif n == 4:
                    weapon_dict["成长数值"][m]["平均每级提升"] = {}
                    weapon_dict["成长数值"][m]["平均每级提升"]["基础攻击力"] = i.text[7:]
                elif n == 5:
                    weapon_dict["成长数值"][m]["平均每级提升"]["攻击力"] = i.text[7:]
            elif m == 7:
                if n == 0:
                    continue
                elif n == 1:
                    weapon_dict["成长数值"][m]["初始基础数值"] = {}
                    weapon_dict["成长数值"][m]["初始基础数值"]["基础攻击力"] = i.text[7:]
                elif n == 2:
                    weapon_dict["成长数值"][m]["初始基础数值"]["攻击力"] = i.text[5:]
                weapon_dict["成长数值"][m]["平均每级提升"] = None
            else:
                if n == 0:
                    continue
                elif n == 1:
                    weapon_dict["成长数值"][m]["初始基础数值"] = {}
                    weapon_dict["成长数值"][m]["初始基础数值"]["基础攻击力（未突破）"] = i.text[12:]
                elif n == 2:
                    weapon_dict["成长数值"][m]["初始基础数值"]["基础攻击力（突破后）"] = i.text[12:]
                elif n == 3:
                    weapon_dict["成长数值"][m]["初始基础数值"]["攻击力"] = i.text[5:]
                elif n == 4:
                    weapon_dict["成长数值"][m]["平均每级提升"] = {}
                    weapon_dict["成长数值"][m]["平均每级提升"]["基础攻击力"] = i.text[7:]
                elif n == 5:
                    weapon_dict["成长数值"][m]["平均每级提升"]["攻击力"] = i.text[5:]

    # 故事
    weapon_dict["故事"] = divs['story'].text.replace(" ", "").replace("\n", "")[5:-6]
    return weapon_dict


def artifacts(url):
    print('Ping pong')
    pass


if __name__ == '__main__':
    weapon = weapon("https://bbs.mihoyo.com/ys/obc/content/296/detail?bbs_presentation_style=no_header")
    # char = character('https://bbs.mihoyo.com/ys/obc/content/1498/detail?bbs_presentation_style=no_header')
    with open('info_demo.json', 'w+', encoding='UTF-8') as f:
        json.dump(weapon, f, ensure_ascii=False, indent=4)
