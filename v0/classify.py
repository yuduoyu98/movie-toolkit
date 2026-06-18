import configparser
import os
import re
import shutil


def distribute_by_prefix(source_dir, dest_map):
    if not os.path.exists(source_dir):
        print(f"Source    /*-+xz -+-+ directory '{source_dir}' does not exist.")
        return

    for filename in os.listdir(source_dir):
        file_path = os.path.join(source_dir, filename)
        if os.path.isfile(file_path):
            file_prefix = filename.split(']')[0].replace('[', '')
            if file_prefix in dest_map:
                destination_dir = dest_map[file_prefix]
                destination_path = os.path.join(destination_dir, filename)
                shutil.move(file_path, destination_path)
                print(f"'{filename}' -> '{destination_dir}'")
            else:
                print(f"未知前缀：{file_prefix}")


def extract_actor_name(text):
    # 取电影名之前
    text = text.split('»')[0]
    # pattern = r'[\u4e00-\u9fff]+' # 仅仅中文

    pattern = r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3040-\u309f\u30a0-\u30ff]+' #中文+日文
    # 使用findall方法查找所有匹配的子串
    chn_words = re.findall(pattern, text)

    if chn_words is not None and len(chn_words) > 0:
        return str(chn_words[0])
    return None


def classify_by_chn_name(base_dir):
    # 遍历所有文件
    for filename in os.listdir(base_dir):
        file_path = os.path.join(base_dir, filename)
        # 如果是文件
        if os.path.isfile(file_path):
            # 尝试提取中文/中文+日文艺名
            chn_name = extract_actor_name(filename)
            # 提取电影名
            movie_info = extract_movie_name(filename)
            print(f"DEBUG >> '{filename}' 提取movie信息: {movie_info }")
            if movie_info is None:
                continue
            if chn_name is not None:
                print(f"DEBUG >> '{filename}' 提取中文艺名：{chn_name}")
                classify(base_dir, chn_name, file_path, filename, movie_info)
            else:
                en_name = filename.split(']')[1].split('»')[0].strip().replace('.', ' ')
                if en_name.__contains__('+'):
                    en_name = en_name.split('+')[0]
                print(f"'DEBUG >> {filename}' 提取英文艺名：{en_name}")
                if en_name != 'Unknown':
                    classify(base_dir, en_name, file_path, filename, movie_info)
                else:
                    classify(base_dir, 'Unknown', file_path, filename, movie_info)


def classify(base_dir, actor_name, file_path, filename, movie_info):
    classify_dir_path = os.path.join(base_dir, actor_name, movie_info)
    os.makedirs(classify_dir_path, exist_ok=True)
    dest_path = os.path.join(classify_dir_path, filename)
    shutil.move(file_path, dest_path)
    print(f"'{filename}' -> '{dest_path}'")


def extract_movie_name(file_name: str):
    movie_info = None
    try:
        if file_name.endswith('.jpg') or file_name.endswith('.png'):
            raw = file_name.split('»')[1].strip()
            pattern = r"-\d+\.(jpg|png)"
            match = re.search(pattern, raw)
            if match:
                matched_string = match.group(0)
                movie_info = raw.replace(matched_string, '')
        elif file_name.endswith('.gif'):
            raw = file_name.split('»')[1].strip()
            pattern = r"\(\d+\).gif"
            match = re.search(pattern, raw)
            if match:
                matched_string = match.group(0)
                movie_info = raw.replace(matched_string, '')
        elif file_name.endswith('.mp4'):
            movie_info = file_name.split("»")[1].strip()
        else:
            print(f"ERROR >> 未识别文件名(后缀): {file_name}")
            return None

        if movie_info is None:
            print(f"ERROR >> 未识别文件名(匹配失败): {file_name}")
            return None
        else:
            # 如果是剧集 类似 [JAP]Unknown » Lupin.the.Third.Mine.Fujiko.to.Iu.Onna.2012.S01E04-1.jpg 去除".S01E04"
            series_pattern  = r"S\d{2}E\d{2}"
            match = re.search(series_pattern, movie_info)
            if match:
                matched_string = match.group()
                movie_info = movie_info.replace(f'.{matched_string}', '')
            # print(movie_info)
            year = movie_info.split('.')[-1]
            movie = movie_info[0:-5].replace('.', ' ')
            # 早期日文电影 使用'日文名#英文名'的格式 以日文名作为文件夹
            return f"[{year}]{movie}"

    except Exception as e:
        print(f"ERROR >> 未识别文件名(异常): {file_name}")
        return None


# 测试字符串
text = "[KOR]Park.Jung-yoon.朴贞允 » Nineteen.Shh.No.Imagining.2015 » 00.12.42-00.12.56"
# text = "[KOR]Unknown » Nineteen.Shh.No.Imagining.2015-2"

# 目标目录，根据文件前缀进行映射
dirs = {
    'KOR': r"F:\DB\影视\Clip\Korean",
    'SEA': r"F:\DB\影视\Clip\South-East Asia",
    'WEST': r"F:\DB\影视\Clip\West",
    'JAP': r"F:\DB\影视\Clip\Japan",
    'CHN': r"F:\DB\影视\Clip\China",
    'SLA': r"F:\DB\影视\Clip\Slavs",
    'LTA': r"F:\DB\影视\Clip\Latin America"
}

config = configparser.ConfigParser()
config.read('../movie.ini', encoding='utf-8')
source_directory = config.get('MovieConfig', 'target_base_path')

# 源目录
# source_directory = r'F:\DB\影视\Clip\待整理'

if __name__ == '__main__':
    distribute_by_prefix(source_directory, dirs)
    classify_by_chn_name(dirs['SLA'])
    classify_by_chn_name(dirs['WEST'])
    classify_by_chn_name(dirs['CHN'])
    classify_by_chn_name(dirs['JAP'])
    classify_by_chn_name(dirs['KOR'])
    classify_by_chn_name(dirs['SEA'])
    classify_by_chn_name(dirs['LTA'])

    # # 测试字符串
    # test_str = "[JAP]Kaori.Sugita.杉田かおり » 绝对Time.Adventure.5.Seconds.Till.Climax.1986-1"
    # # 提取并打印第一个结果
    # result = extract_actor_name(test_str)
    # if result:
    #     print(result)
    # else:
    #     print("没有找到匹配的中文或日文字符串")