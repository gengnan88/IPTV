#!/usr/bin/env python3
"""
IPTV直播源域名提取工具 - CCTV排序版本
"""

import requests
import re
import json
import os
import ipaddress
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from urllib.parse import urlparse

# ============== 域名列表 ==============
DOMAINS = [
    "ltypth.cn:9901",
    "zh.10010tv.cn:9901",
    "iptv.my669.com:9901",
    "wgrmyy.cn:9901",
    "jxx.wlzsyw.cn:9901",
    "zsh.ltypth.cn:9901",
    "http://dz.mzsyt.com:7066/",
    "http://ozxz.cncnnc.com:9901/",
    "http://baoqing003.coccc.online:9901/",
    "http://itv.inrand.com:9888/",
    "http://iptv.my669.com:9903/",
    "http://www.kingtom-tech.com:9902/",
    "http://sun135790.x3322.net:9902/",
    "http://wxapi.hqqgbxy.com:9901/",
    "http://iptv.zhonghenginfo.cn:8989/",
    "http://hunhhyd.sohu.blog:9999/",
    "http://ekesh.cn:9999/",
    "http://zh.ltypth.cn:9901/",
    "http://tpc.x3322.net:9901/",
    "http://demo.ruijingnet.com:2001/",
    "http://fujuniptv.cn:9901/",
    "http://51chuquwan.com:10133/",
    "http://sykj1.3322.org:9901/",
    "http://shuangyashan.coccc.online:65000/",
    "http://bpt.wifi98.com:9901/",
    "http://dh.wifi98.com:9901/",
    "http://i2.ekesh.cn:9999/",
]

# ============== CCTV排序规则 ==============
# CCTV1-17的正确顺序
CCTV_ORDER = {
    'CCTV1': 1, 'CCTV2': 2, 'CCTV3': 3, 'CCTV4': 4, 'CCTV5': 5,
    'CCTV5+': 6,  # 5+放在5之后
    'CCTV6': 7, 'CCTV7': 8, 'CCTV8': 9, 'CCTV9': 10,
    'CCTV10': 11, 'CCTV11': 12, 'CCTV12': 13, 'CCTV13': 14,
    'CCTV14': 15, 'CCTV15': 16, 'CCTV16': 17, 'CCTV17': 18,
    'CGTN': 19, 'CGTN纪录': 20, 'CCTV4K': 21,
}

# 其他频道排序规则
WEISHI_ORDER = [
    '湖南卫视', '浙江卫视', '江苏卫视', '东方卫视', '北京卫视', '深圳卫视',
    '广东卫视', '山东卫视', '辽宁卫视', '安徽卫视', '天津卫视', '重庆卫视',
    '河南卫视', '湖北卫视', '江西卫视', '黑龙江卫视', '四川卫视', '云南卫视',
    '贵州卫视', '陕西卫视', '甘肃卫视', '青海卫视', '宁夏卫视', '新疆卫视',
    '西藏卫视', '内蒙古卫视', '广西卫视', '海南卫视', '东南卫视', '兵团卫视',
    '河北卫视', '山西卫视', '吉林卫视', '福建卫视', '旅游卫视', '金鹰卡通',
    '卡酷少儿', '嘉佳卡通', '优漫卡通'
]

# ============== 内网IP段定义 ==============
PRIVATE_IP_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('224.0.0.0/4'),
    ipaddress.ip_network('240.0.0.0/4'),
    ipaddress.ip_network('255.255.255.255/32'),
]

PRIVATE_IP_PREFIXES = (
    '10.', '127.', '169.254.', '172.16.', '172.17.', '172.18.', '172.19.',
    '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.', '172.26.',
    '172.27.', '172.28.', '172.29.', '172.30.', '172.31.', '192.168.',
    '224.', '225.', '226.', '227.', '228.', '229.', '230.', '231.', '232.',
    '233.', '234.', '235.', '236.', '237.', '238.', '239.', '240.', '241.',
    '242.', '243.', '244.', '245.', '246.', '247.', '248.', '249.', '250.',
    '251.', '252.', '253.', '254.', '255.', '0.0.0.0','16.0.'
)

# ============== IP判断函数 ==============
def is_private_ip(ip_str):
    """判断IP是否为内网IP"""
    if not ip_str:
        return True
    
    for prefix in PRIVATE_IP_PREFIXES:
        if ip_str.startswith(prefix):
            return True
    
    try:
        ip = ipaddress.ip_address(ip_str)
        for network in PRIVATE_IP_RANGES:
            if ip in network:
                return True
        return False
    except ValueError:
        return False

def extract_ip_from_url(url):
    """从URL中提取IP地址"""
    match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', url)
    if match:
        return match.group(1)
    return None

def is_valid_stream_url(url):
    """判断流URL是否有效（非内网）"""
    ip = extract_ip_from_url(url)
    if ip:
        return not is_private_ip(ip)
    return True

# ============== 工具函数 ==============
def clean_domain(domain):
    """清理域名格式"""
    domain = domain.strip()
    if not domain.startswith('http'):
        domain = f'http://{domain}'
    if not domain.endswith('/'):
        domain = f'{domain}/'
    return domain

def normalize_channel_name(name):
    """统一频道名称"""
    if not name:
        return None
    
    name = name.upper()
    
    # 去除干扰字符
    remove_patterns = [
        r'\s+', r'-', r'\*', r'频道', r'高清', r'HD', r'标清', 
        r'\(.*?\)', r'\[.*?\]', r'（.*?）', r'测试', r'备选', r'IPV4', r'IPV6'
    ]
    for pattern in remove_patterns:
        name = re.sub(pattern, '', name)
    
    # CCTV格式统一
    name = re.sub(r'CCTV-?(\d+)', r'CCTV\1', name)
    
    # CCTV特殊映射
    cctv_map = {
        'CCTV1综合': 'CCTV1', 'CCTV2财经': 'CCTV2', 'CCTV3综艺': 'CCTV3',
        'CCTV4中文国际': 'CCTV4', 'CCTV4国际': 'CCTV4', 'CCTV5体育': 'CCTV5',
        'CCTV5+体育赛事': 'CCTV5+', 'CCTV5+体育': 'CCTV5+', 'CCTV5PLUS': 'CCTV5+',
        'CCTV6电影': 'CCTV6', 'CCTV7国防军事': 'CCTV7', 'CCTV7军事': 'CCTV7',
        'CCTV7军农': 'CCTV7', 'CCTV8电视剧': 'CCTV8', 'CCTV9纪录': 'CCTV9',
        'CCTV10科教': 'CCTV10', 'CCTV11戏曲': 'CCTV11', 'CCTV12社会与法': 'CCTV12',
        'CCTV13新闻': 'CCTV13', 'CCTV新闻': 'CCTV13', 'CCTV14少儿': 'CCTV14',
        'CCTV15音乐': 'CCTV15', 'CCTV16奥林匹克': 'CCTV16', 'CCTV17农业农村': 'CCTV17'
    }
    for k, v in cctv_map.items():
        if k in name:
            return v
    
    name = name.strip()
    
    if len(name) < 2 or name.isdigit():
        return None
    
    return name

def get_channel_group(name):
    """获取频道分组"""
    if 'CCTV' in name or 'CGTN' in name:
        return '央视频道'
    
    weishi = ('卫视', '湖南', '浙江', '江苏', '东方', '北京', '深圳', '广东', 
              '山东', '辽宁', '安徽', '天津', '重庆', '河南', '湖北', '江西',
              '黑龙江', '四川', '云南', '贵州', '陕西', '甘肃', '青海', '宁夏',
              '新疆', '西藏', '内蒙古', '广西', '海南', '东南', '兵团', '河北',
              '山西', '吉林', '福建')
    if any(w in name for w in weishi):
        return '卫视频道'
    
    hkmotw = ('凤凰', '香港', 'TVB', '翡翠', '明珠', '台湾', '台视', '中视', 
              '华视', '民视', '东森', '三立', '澳门', '澳视')
    if any(h in name for h in hkmotw):
        return '港澳台频道'
    
    return '其他频道'

def get_channel_sort_key(name, group):
    """获取频道排序键值"""
    if group == '央视频道':
        # CCTV频道按数字排序
        if name in CCTV_ORDER:
            return CCTV_ORDER[name]
        # 提取数字
        match = re.search(r'CCTV(\d+)', name)
        if match:
            num = int(match.group(1))
            if num <= 17:
                return num
            return 100 + num
        return 999
    
    elif group == '卫视频道':
        # 卫视按预设顺序排序
        if name in WEISHI_ORDER:
            return WEISHI_ORDER.index(name)
        return 1000
    
    else:
        # 其他分组按字母排序
        return name

# ============== 提取函数 ==============
def fetch_from_domain(domain_url):
    """从单个域名获取频道列表"""
    json_url = f'{domain_url}iptv/live/1000.json?key=txiptv'
    source_name = urlparse(domain_url).netloc or domain_url.split('//')[1].split('/')[0]
    
    try:
        response = requests.get(json_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data and isinstance(data['data'], list):
                results = []
                private_count = 0
                
                for item in data['data']:
                    if isinstance(item, dict):
                        raw_name = item.get('name')
                        url_path = item.get('url')
                        
                        if raw_name and url_path:
                            clean_name = normalize_channel_name(raw_name)
                            if clean_name:
                                if url_path.startswith('http'):
                                    full_url = url_path
                                else:
                                    base_url = domain_url.rstrip('/')
                                    if url_path.startswith('/'):
                                        full_url = base_url + url_path
                                    else:
                                        full_url = base_url + '/' + url_path
                                
                                if is_valid_stream_url(full_url):
                                    results.append({
                                        'name': clean_name,
                                        'url': full_url,
                                        'source': source_name
                                    })
                                else:
                                    private_count += 1
                
                if results:
                    print(f'  ✅ {source_name}: {len(results)}个频道 (剔除{private_count}个内网源)')
                    return results
                else:
                    if private_count > 0:
                        print(f'  ⚠️ {source_name}: 全部为内网源 ({private_count}个)')
                    else:
                        print(f'  ⚠️ {source_name}: 无有效频道')
            else:
                print(f'  ⚠️ {source_name}: 数据格式错误')
        else:
            print(f'  ❌ {source_name}: HTTP {response.status_code}')
            
    except requests.exceptions.Timeout:
        print(f'  ⏰ {source_name}: 超时')
    except requests.exceptions.ConnectionError:
        print(f'  🔌 {source_name}: 连接失败')
    except json.JSONDecodeError:
        print(f'  📄 {source_name}: JSON解析失败')
    except Exception as e:
        print(f'  ❌ {source_name}: {str(e)[:50]}')
    
    return []

def fetch_all():
    """从所有域名获取频道"""
    print('=' * 60)
    print('IPTV直播源域名提取工具')
    print(f'运行时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)
    
    print('\n📌 过滤规则:')
    print('   - 内网IP: 10.x.x.x, 172.16.x.x-172.31.x.x, 192.168.x.x')
    print('   - 回环地址: 127.x.x.x')
    print('   - 组播地址: 224.x.x.x-239.x.x.x')
    
    domains = [clean_domain(d) for d in DOMAINS]
    print(f'\n📡 待提取域名: {len(domains)} 个\n')
    
    all_channels = []
    success_count = 0
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_from_domain, domain): domain for domain in domains}
        
        for future in as_completed(futures):
            try:
                results = future.result(timeout=30)
                if results:
                    success_count += 1
                    all_channels.extend(results)
            except Exception as e:
                print(f'  ❌ 处理失败: {e}')
    
    print(f'\n{"=" * 60}')
    print('✅ 提取完成！')
    print(f'   成功域名: {success_count} 个')
    print(f'   原始频道: {len(all_channels)} 个')
    
    return all_channels

# ============== 保存函数 ==============
def save_results(channels):
    """保存结果文件"""
    if not channels:
        print('❌ 未提取到任何频道')
        return False
    
    # 去重
    seen = set()
    unique = []
    for ch in channels:
        key = f"{ch['name']}_{ch['url']}"
        if key not in seen:
            seen.add(key)
            unique.append(ch)
    
    print(f'   去重后: {len(unique)} 个')
    
    # 创建输出目录
    os.makedirs('output', exist_ok=True)
    
    # 按分组整理
    groups = defaultdict(list)
    for ch in unique:
        groups[get_channel_group(ch['name'])].append(ch)
    
    # 在每个分组内排序
    for group in groups:
        groups[group].sort(key=lambda x: get_channel_sort_key(x['name'], group))
    
    group_order = ['央视频道', '卫视频道', '港澳台频道', '其他频道']
    
    # 保存M3U
    with open('output/iptv.m3u', 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        f.write(f'# 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'# 频道数量: {len(unique)}\n')
        f.write(f'# 排序规则: CCTV1-17顺序排列\n\n')
        
        for group in group_order:
            if group not in groups:
                continue
            
            ch_list = groups[group]
            
            for ch in ch_list:
                f.write(f'#EXTINF:-1 group-title="{group}",{ch["name"]}\n')
                f.write(f'{ch["url"]}\n')
    
    print(f'✅ 已保存: output/iptv.m3u')
    
    # 保存TXT（多线路用#分隔）
    channel_urls = defaultdict(list)
    for ch in unique:
        if ch['url'] not in channel_urls[ch['name']]:
            channel_urls[ch['name']].append(ch['url'])
    
    # 按排序规则输出TXT
    with open('output/iptv.txt', 'w', encoding='utf-8') as f:
        f.write(f'# IPTV直播源\n')
        f.write(f'# 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'# 频道数量: {len(channel_urls)}\n')
        f.write(f'# 排序规则: CCTV1-17顺序排列\n\n')
        
        # 按分组顺序输出
        for group in group_order:
            if group not in groups:
                continue
            
            ch_list = groups[group]
            
            for ch in ch_list:
                name = ch['name']
                urls = channel_urls[name]
                combined = '#'.join(urls)
                f.write(f'{name},{combined}\n')
    
    print(f'✅ 已保存: output/iptv.txt')
    
    # 保存JSON
    json_data = {
        'generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'sort_rules': 'CCTV1-17顺序排列',
        'filter_rules': [
            '内网IP: 10.x.x.x, 172.16.x.x-172.31.x.x, 192.168.x.x',
            '回环地址: 127.x.x.x',
            '组播地址: 224.x.x.x-239.x.x.x'
        ],
        'total_channels': len(unique),
        'channels': {}
    }
    for name, urls in channel_urls.items():
        json_data['channels'][name] = {
            'urls': urls,
            'count': len(urls)
        }
    
    with open('output/iptv.json', 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f'✅ 已保存: output/iptv.json')
    
    # 统计信息
    print(f'\n📊 分组统计:')
    for group in group_order:
        count = len(groups.get(group, []))
        if count > 0:
            print(f'   {group}: {count} 个')
    
    # 显示CCTV排序预览
    cctv_channels = [ch['name'] for ch in groups.get('央视频道', [])]
    if cctv_channels:
        print(f'\n📺 CCTV频道排序预览:')
        for i, name in enumerate(cctv_channels[:20], 1):
            print(f'   {i:2}. {name}')
    
    return True

# ============== 主函数 ==============
def main():
    channels = fetch_all()
    save_results(channels)

if __name__ == '__main__':
    main()