#!/usr/bin/env python3
"""
IPTV直播源域名提取工具 - GitHub Actions版本
"""

import re
import time
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

# ============== 域名列表 ==============
DOMAIN_SOURCES = [
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


def clean_domain_url(domain):
    """清理域名URL格式"""
    domain = domain.strip()
    if not domain.startswith('http'):
        domain = f"http://{domain}"
    if not domain.endswith('/'):
        domain = f"{domain}/"
    return domain


def normalize_channel_name(name):
    """统一频道名称"""
    if not name:
        return None
    
    name = name.upper()
    
    # 去除干扰字符
    remove_patterns = [
        r'\s+', r'-', r'\*', r'频道', r'高清', r'HD', r'标清', r'测试',
        r'\(.*?\)', r'\[.*?\]', r'（.*?）'
    ]
    for p in remove_patterns:
        name = re.sub(p, '', name)
    
    # CCTV统一
    name = re.sub(r'CCTV-?(\d+)', r'CCTV\1', name)
    
    # CCTV特殊处理
    cctv_map = {
        'CCTV1综合': 'CCTV1', 'CCTV2财经': 'CCTV2', 'CCTV3综艺': 'CCTV3',
        'CCTV4中文国际': 'CCTV4', 'CCTV5体育': 'CCTV5', 'CCTV5+体育赛事': 'CCTV5+',
        'CCTV5+体育': 'CCTV5+', 'CCTV6电影': 'CCTV6', 'CCTV7国防军事': 'CCTV7',
        'CCTV7军事': 'CCTV7', 'CCTV8电视剧': 'CCTV8', 'CCTV9纪录': 'CCTV9',
        'CCTV10科教': 'CCTV10', 'CCTV11戏曲': 'CCTV11', 'CCTV12社会与法': 'CCTV12',
        'CCTV13新闻': 'CCTV13', 'CCTV新闻': 'CCTV13', 'CCTV14少儿': 'CCTV14',
        'CCTV15音乐': 'CCTV15', 'CCTV16奥林匹克': 'CCTV16', 'CCTV17农业农村': 'CCTV17'
    }
    for k, v in cctv_map.items():
        if k in name:
            return v
    
    name = name.strip()
    return name if len(name) >= 2 else None


def fetch_from_domain(domain_url):
    """从单个域名获取频道列表"""
    json_url = f"{domain_url}iptv/live/1000.json?key=txiptv"
    source_name = urlparse(domain_url).netloc or domain_url.split('//')[1].split('/')[0]

    try:
        response = requests.get(json_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data and isinstance(data['data'], list):
                results = []
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
                                
                                results.append({
                                    'name': clean_name,
                                    'url': full_url,
                                    'source': source_name
                                })
                
                print(f"  ✅ {source_name}: {len(results)}个频道")
                return results
            else:
                print(f"  ⚠️ {source_name}: 数据格式错误")
        else:
            print(f"  ❌ {source_name}: HTTP {response.status_code}")
            
    except requests.exceptions.Timeout:
        print(f"  ⏰ {source_name}: 超时")
    except requests.exceptions.ConnectionError:
        print(f"  🔌 {source_name}: 连接失败")
    except Exception as e:
        print(f"  ❌ {source_name}: {str(e)[:50]}")
    
    return []


def get_channel_group(name):
    """获取频道分组"""
    if 'CCTV' in name or 'CGTN' in name:
        return "央视频道"
    
    weishi = ('卫视', '湖南', '浙江', '江苏', '东方', '北京', '深圳', '广东', 
              '山东', '辽宁', '安徽', '天津', '重庆', '河南', '湖北', '江西',
              '黑龙江', '四川', '云南', '贵州', '陕西', '甘肃', '青海', '宁夏',
              '新疆', '西藏', '内蒙古', '广西', '海南', '东南', '兵团')
    if any(w in name for w in weishi):
        return "卫视频道"
    
    hkmotw = ('凤凰', '香港', 'TVB', '翡翠', '明珠', '台湾', '台视', '中视', 
              '华视', '民视', '东森', '三立', '澳门')
    if any(h in name for h in hkmotw):
        return "港澳台频道"
    
    return "其他频道"


def save_m3u(channels, output_path):
    """保存M3U格式"""
    groups = defaultdict(list)
    for ch in channels:
        groups[get_channel_group(ch['name'])].append(ch)
    
    group_order = ["央视频道", "卫视频道", "港澳台频道", "其他频道"]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 频道数量: {len(channels)}\n\n")
        
        for group in group_order:
            if group not in groups:
                continue
            
            ch_list = groups[group]
            if group == "央视频道":
                def sort_key(c):
                    match = re.search(r'CCTV(\d+)', c['name'])
                    return int(match.group(1)) if match else 999
                ch_list.sort(key=sort_key)
            else:
                ch_list.sort(key=lambda x: x['name'])
            
            for ch in ch_list:
                f.write(f'#EXTINF:-1 group-title="{group}",{ch["name"]}\n')
                f.write(f'{ch["url"]}\n')
    
    print(f"✅ 已保存: {output_path}")


def save_txt(channels, output_path):
    """保存TXT格式"""
    channel_urls = defaultdict(list)
    for ch in channels:
        if ch['url'] not in channel_urls[ch['name']]:
            channel_urls[ch['name']].append(ch['url'])
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# IPTV直播源\n")
        f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 频道数量: {len(channel_urls)}\n\n")
        
        for name in sorted(channel_urls.keys()):
            combined = '#'.join(channel_urls[name])
            f.write(f"{name},{combined}\n")
    
    print(f"✅ 已保存: {output_path}")


def save_json(channels, output_path):
    """保存JSON格式"""
    channel_data = defaultdict(lambda: {'urls': [], 'sources': []})
    for ch in channels:
        if ch['url'] not in channel_data[ch['name']]['urls']:
            channel_data[ch['name']]['urls'].append(ch['url'])
        if ch['source'] not in channel_data[ch['name']]['sources']:
            channel_data[ch['name']]['sources'].append(ch['source'])
    
    output = {
        'generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_channels': len(channel_data),
        'total_urls': len(channels),
        'channels': {}
    }
    
    for name, data in channel_data.items():
        output['channels'][name] = {
            'urls': data['urls'],
            'count': len(data['urls']),
            'sources': data['sources']
        }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已保存: {output_path}")


def main():
    print("=" * 70)
    print("IPTV直播源域名提取工具 - GitHub Actions")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    cleaned_domains = [clean_domain_url(d) for d in DOMAIN_SOURCES]
    print(f"\n📡 待提取域名: {len(cleaned_domains)} 个")
    print("开始提取...\n")
    
    all_channels = []
    success_count = 0
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_from_domain, domain): domain for domain in cleaned_domains}
        
        for future in as_completed(futures):
            try:
                results = future.result(timeout=30)
                if results:
                    success_count += 1
                    all_channels.extend(results)
            except Exception as e:
                print(f"  ❌ 处理失败: {e}")
    
    print(f"\n" + "=" * 70)
    print("✅ 提取完成！")
    print(f"   成功域名: {success_count} 个")
    print(f"   原始频道: {len(all_channels)} 个")
    
    if all_channels:
        # 去重
        seen = set()
        unique = []
        for ch in all_channels:
            key = f"{ch['name']}_{ch['url']}"
            if key not in seen:
                seen.add(key)
                unique.append(ch)
        
        print(f"   去重后: {len(unique)} 个")
        
        # 创建输出目录
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # 保存文件
        save_m3u(unique, output_dir / "iptv_domain.m3u")
        save_txt(unique, output_dir / "iptv_domain.txt")
        save_json(unique, output_dir / "iptv_domain.json")
        
        # 统计
        groups = defaultdict(int)
        for ch in unique:
            groups[get_channel_group(ch['name'])] += 1
        
        print("\n📊 分组统计:")
        for g, c in sorted(groups.items()):
            print(f"   {g}: {c} 个")
    else:
        print("\n❌ 未提取到任何频道")
        print("提示: 可能需要使用代理或检查网络环境")


if __name__ == "__main__":
    main()