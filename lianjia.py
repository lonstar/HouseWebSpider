# coding=utf-8
from lxml import etree
from util import get_html_by_url
import pymongo
import threading
from mongo import MongoDb


class LianJia(object):

    def __init__(self, url):
        self.url = url

    def __get_all_links(self):
        url = self.url + "/ershoufang/"
        html = get_html_by_url(url)
        tree = etree.HTML(html)

        # 找到所有分区
        url_list = []
        location_lists = tree.xpath("//div[@class='location-child']/div[1]/a")
        # 第一个是不限，最后一个是上海周边，都去掉
        location_lists = location_lists[1:-2]
        for location in location_lists:
            print(location.get("href"), location.text)
            url = self.url + location.get("href")
            html = get_html_by_url(url)
            location_tree = etree.HTML(html)
            sub_zones = location_tree.xpath("//div[@class='location-child']/div[2]/div")
            sub_zones = sub_zones[1:]
            for sub_zone in sub_zones:
                sub_zone_url = sub_zone.xpath("./a")[0].get("href")
                sub_zone_name = sub_zone.xpath("./a")[0].text
                # 取到每个区域下的页数
                url = self.url + sub_zone_url
                sub_zone_html = get_html_by_url(url)
                sub_zone_tree = etree.HTML(sub_zone_html)
                pages_xpath = sub_zone_tree.xpath("//div[@class='c-pagination']/a")
                if len(pages_xpath) == 0:
                    total_pages = 1
                else:
                    total_pages = int(pages_xpath[-2].text.strip())

                print(sub_zone_url, sub_zone_name, total_pages, u"页")
                for i in range(1, total_pages + 1):
                    url_list.append(url + "/d" + str(i))

        return url_list

    def __get_house_basic_info(self, tree):
        house_basic_info = {}
        house_basic_info_xpath = tree.xpath('//div[@id="js-baseinfo-header"]/div')
        house_type = house_basic_info_xpath[0].xpath("./div[1]/div[2]/ul/li[1]/span[2]/text()")[0].strip()
        print(u"房屋户型:", house_type)
        house_basic_info["house_type"] = house_type

        elevator = house_basic_info_xpath[0].xpath("./div[1]/div[2]/ul/li[2]/span[2]/text()")[0].strip()
        print(u"配备电梯:", elevator)
        house_basic_info["elevator"] = elevator

        area = house_basic_info_xpath[0].xpath("./div[1]/div[2]/ul/li[3]/span[2]/text()")[0].strip()
        area = float(area.replace(u"平", ""))
        print(u"建筑面积:", area)
        house_basic_info["area"] = area

        heating_mode = house_basic_info_xpath[0].xpath("./div[1]/div[2]/ul/li[4]/span[2]/text()")[0].strip()
        print(u"供暖方式:", heating_mode)
        house_basic_info["heating_mode"] = heating_mode

        #############################################################################################
        floor = house_basic_info_xpath[0].xpath("./div[1]/div[3]/ul/li[1]/span[2]/text()")[0].strip()
        print(u"所在楼层:", floor)
        house_basic_info["floor"] = floor

        renovation = house_basic_info_xpath[0].xpath("./div[1]/div[3]/ul/li[2]/span[2]/text()")[0].strip()
        print(u"装修情况:", renovation)
        house_basic_info["renovation"] = renovation

        orientation = house_basic_info_xpath[0].xpath("./div[1]/div[3]/ul/li[3]/span[2]/text()")[0].strip()
        print(u"房屋朝向:", orientation)
        house_basic_info["orientation"] = orientation

        park = house_basic_info_xpath[0].xpath("./div[1]/div[3]/ul/li[4]/span[2]/text()")[0].strip()
        print(u"车位情况:", park)
        house_basic_info["park"] = park

        trade = house_basic_info_xpath[0].xpath("./div[2]/div[2]/ul/li[1]/span[2]/text()")[0].strip()
        print(u"上次交易:", trade)
        house_basic_info["trade"] = trade

        life = house_basic_info_xpath[0].xpath("./div[2]/div[2]/ul/li[2]/span[2]/text()")[0].strip()
        print(u"房本年限:", life)
        house_basic_info["life"] = life

        reason = house_basic_info_xpath[0].xpath("./div[2]/div[3]/ul/li[1]/span[2]/text()")[0].strip()
        print(u"售房原因:", reason)
        house_basic_info["reason"] = reason

        return house_basic_info

    def __get_house_info(self, detail_link):
        house_dict = {}
        url = self.url + detail_link
        print(url)
        detail_html = get_html_by_url(url)
        detail_tree = etree.HTML(detail_html)

        price_total, price_unit = self.__get_price(detail_tree)
        house_dict["price_total"] = price_total
        house_dict["price_unit"] = price_unit

        build_year = self.__get_build_year(detail_tree)
        house_dict["build_year"] = build_year

        description = self.__get_description(detail_tree)
        house_dict["description"] = description

        house_basic_info = self.__get_house_basic_info(detail_tree)
        house_dict.update(house_basic_info)

        # 获取对应小区信息
        cell_info = self.__get_cell_info(detail_tree)
        # 小区剩余信息
        building_num = detail_tree.xpath('//div[@id="js-estate-intro"]/div/div/div[2]/ul/li[4]/span[2]/text()')[0]
        print(u"楼栋总数:", building_num)
        building_num = int(building_num.replace(u"栋", ""))

        households = detail_tree.xpath('//div[@id="js-estate-intro"]/div/div/div[2]/ul/li[5]/span[2]/text()')[0]
        print(u"房屋总数:", households)
        households = int(households.replace(u"户", ""))
        cell_info["building_num"] = building_num
        cell_info["households"] = households

        house_dict["cell_info"] = cell_info

        # 将小区信息和房子信息分别记录到mongo
        print(u"记录到数据库")
        mongo = MongoDb('house')
        mongo.update("cell", {"name": cell_info["name"]}, cell_info)
        mongo.insert("house", house_dict)
        mongo.close()

    def paser(self):
        #         url_list = []
        #         url = self.url + "/ershoufang/"
        #         url_list.append(url)

        url_list = self.__get_all_links()
        total_url_nums = len(url_list)
        print(u"总计需要处理%s个链接" % total_url_nums)

        for index, url in enumerate(url_list):

            rate = index * 100 / total_url_nums

            print("*" * 80)
            print("*")
            print("*")
            print("*")
            print(u"*已完成%s%%" % rate)
            print("*")
            print("*")
            print("*")
            print("*" * 80)

            html = get_html_by_url(url)
            tree = etree.HTML(html)

            # house_list = []
            house_list_per_page = tree.xpath("//ul[@class='js_fang_list']/li")
            thread_list = []
            for li in house_list_per_page:
                print()
                print("=" * 80)
                # <ul class="js_fang_list">
                #  <li>
                #     <a gahref="results_click_order_1" target="_blank" href="/ershoufang/sh4578071.html" class="img js_triggerGray">
                detail_link = li.xpath("./a[1]/@href")[0].strip()

                __mongo = MongoDb('house')
                ret = __mongo.find("links", {"link": detail_link})
                if ret:
                    print(u"链接", detail_link, u"已经处理过，跳过")
                    continue

                self.__get_house_info(detail_link)
                __mongo.insert("links", {"link": detail_link})
                __mongo.close()

                # 多线程读写

    #                 p = threading.Thread(target=self.__get_house_info, args=(detail_link,))
    #                 thread_list.append(p)
    #             for p in thread_list:
    #                 p.start()
    #             for p in thread_list:
    #                 p.join()

    def __get_description(self, tree):
        des_xpath = tree.xpath("//h1[@class='header-title']")[0]
        if des_xpath.text:
            description = des_xpath.text.strip()
        else:
            description = ""
        # description = tree.xpath("//h1[@class='header-title']/text()")[0].strip()
        print(u"描述:", description)
        return description

    # <div class="price-total">
    #     <span class="price-num">240</span>
    #     <span class="price-total-unit">万</span>
    # </div>
    #
    # <div class="price-unit">
    #     <p class="price-unit-num"><span class="u-bold">58337</span>元/平</p>
    def __get_price(self, tree):
        '''获取总价和每平米单价，单位分别是万元和元/平方
        '''

        price_total_xpath = tree.xpath("//div[@class='price-total']/span")
        price_unit = price_total_xpath[1].text.strip()
        price_total = price_total_xpath[0].text.strip()
        if price_unit == u"亿":
            price_total = float(price_total) * 10000
        print(u"总价:", price_total)
        price_unit_xpath = tree.xpath("//div[@class='price-unit']/p/span")
        price_unit = price_unit_xpath[0].text.strip()
        print(u"单价:", price_unit)
        return int(price_total), int(price_unit)

    # <ul class="maininfo-main maininfo-item">
    #     <li class="main-item">
    #         <p class="u-fz20 u-bold">1室1厅</p>
    #         <p class="u-mt8 u-fz12">
    #                 简装
    #         </p>
    #     </li>
    #     <li class="main-item u-tc">
    #         <div class="u-inblock u-tl">
    #             <p class="u-fz20 u-bold">
    #                     南
    #             </p>
    #             <p class="u-mt8 u-fz12">高区/6层</p>
    #         </div>
    #     </li>
    #     <li class="main-item u-tr">
    #         <p class="u-fz20 u-bold">41.14平</p>
    #         <p class="u-mt8 u-fz12">
    #                 1995年建
    #         </p>
    #     </li>
    # </ul>
    def __get_build_year(self, tree):
        '''获取房屋建筑年代
        '''
        build_year_xpath = tree.xpath("//ul[@class='maininfo-main maininfo-item']/li")
        build_year = build_year_xpath[2].xpath("./p[2]/text()")[0].strip().replace(u"年建", "")
        if build_year == u"暂无数据":
            build_year = None
        else:
            build_year = int(build_year)
        print(u"建筑年代:", build_year)
        return build_year

    # <ul class="maininfo-minor maininfo-item">
    #
    #     <li>
    #         <span class="item-cell item-label">最低首付</span>
    #         <span class="item-cell">84万</span>
    #     </li>
    #     <li>
    #         <span class="item-cell item-label">参考月供</span>
    #         <span class="item-cell">8279元</span>
    #     </li>
    #
    #
    #
    #     <li>
    #         <span class="item-cell item-label">环线信息</span>
    #         <span class="item-cell">内中环</span>
    #     </li>
    #
    #     <li>
    #         <span class="item-cell item-label">小区名称</span>
    #         <span class="item-cell">
    #             <span class="maininfo-estate-name"><a href="/xiaoqu/5011000011786.html" target="_blank" class="u-link" gahref="ershoufang_gaiyao_xiaoqu_link" title="南杨小区（长清路）">南杨小区（长清路）</a>&nbsp;(<a href="/ershoufang/pudongxinqu" target="_blank" class="u-link">浦东</a>&nbsp;<a href="/ershoufang/sanlin" target="_blank" class="u-link">三林</a>)</span>&nbsp;&nbsp;&nbsp;<a href="javascript:;" class="u-link u-mt8" id="jumpToAround">地图</a>
    #         </span>
    #     </li>
    #     <li>
    #         <span class="item-cell item-label">所在地址</span>
    #         <span class="item-cell maininfo-estate-address" title="长清路643弄, 长清路693弄, 长清路773弄, 长清路807弄, 长清路837弄">长清路643弄, 长清路693弄, 长清路773弄, 长清路807弄, 长清路837弄</span>
    #     </li>

    def __get_cell_info(self, tree):
        '''获取小区详细信息'''
        cell_info = {}
        li_list = tree.xpath("//ul[@class='maininfo-minor maininfo-item']/li")
        for li in li_list:
            if li.xpath("./span[1]/text()")[0] == u"小区名称":
                cell_link = li.xpath("./span[2]/span/a[1]/@href")[0]
                break
        else:
            # print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            return cell_info

        print(u"小区链接:", cell_link)
        url = self.url + cell_link
        html = get_html_by_url(url)
        cell_tree = etree.HTML(html)
        name = cell_tree.xpath("//div[@class='nav-container detail-container']/section/div/div/span/h1/text()")[
            0].strip()
        print(u"小区名称:", name)
        cell_info["name"] = name

        address = cell_tree.xpath("//div[@class='nav-container detail-container']/section/div/div/span/span[2]/text()")[
            0].strip()
        print(u"地址:", address)
        cell_info["address"] = address

        basic_infos = cell_tree.xpath("//div[@class='res-info fr']/div")
        avg_price = basic_infos[1].xpath("./div/p[2]/span/text()")[0].strip()
        print(u"挂牌均价:", avg_price)
        if u"暂无" in avg_price:
            cell_info["avg_price"] = None
        else:
            cell_info["avg_price"] = int(avg_price)

        property_type = basic_infos[2].xpath("./ol/li[1]/span/text()")[0].strip()
        property_type = property_type.split("-")[1].strip()
        print(u"物业类型:", property_type)
        cell_info["property_type"] = property_type

        build_year = basic_infos[2].xpath("./ol/li[2]/span/span/text()")[0].strip()
        # print "build_year:", build_year
        if build_year == u"暂无信息":
            build_year = None
        else:
            build_year = build_year.replace(u"年", "")
            build_year = build_year.split("~")[0].strip()
            build_year = int(build_year)
        print(u"建成年代:", build_year)
        cell_info["build_year"] = build_year

        property_cost = basic_infos[2].xpath("./ol/li[3]/span/text()")[0].strip()
        if property_cost == u"暂无信息":
            property_cost = None
        else:
            property_cost = int(property_cost)
        print(u"物业费用:", property_cost)
        cell_info["property_cost"] = property_cost

        property_company = basic_infos[2].xpath("./ol/li[4]/span/text()")[0].strip()
        print(u"物业公司:", property_company)
        cell_info["property_company"] = property_company

        property_developer = basic_infos[2].xpath("./ol/li[5]/span/text()")[0].strip()
        print(u"开发商:", property_developer)
        cell_info["property_developer"] = property_developer

        zone = basic_infos[2].xpath("./ol/li[6]/span/a/text()")[0].strip()
        print(u"区域:", zone)
        cell_info["zone"] = zone

        cycle = basic_infos[2].xpath("./ol/li[7]/span/text()")[0].strip()
        print(u"环线:", cycle)
        cell_info["cycle"] = cycle

        LngLat = basic_infos[2].xpath("./ol/li[8]/a")[0].get("xiaoqu")
        LngLat = eval(LngLat.strip())
        print(u"经纬线: %s" % (LngLat[:2]))
        cell_info["Lng"] = LngLat[0]
        cell_info["Lat"] = LngLat[1]

        return cell_info
