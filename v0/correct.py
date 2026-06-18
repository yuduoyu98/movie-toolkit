# conding=utf8
import configparser
import os

config = configparser.ConfigParser()
config.read('../movie.ini', encoding='utf-8')
path = config.get ('MovieConfig', 'target_base_path')
g = os.walk(path)
# g = os.walk(r"F:\DB\影视\Clip\Japan\水野美纪\[2011]Guilty of Romance")

# 基本信息 
actor = config.get('MovieConfig', 'actor')
chn_name = config.get('MovieConfig', 'chn_name', fallback=None)
movie = config.get('MovieConfig', 'movie')
country = config.get('MovieConfig', 'country')
year = config.getint('MovieConfig', 'year')
season = config.getint('MovieConfig', 'season', fallback=None)
episode = config.getint('MovieConfig', 'episode', fallback=None)
source_file_path = config.get('MovieConfig', 'source_file_path')
target_base_path = config.get('MovieConfig', 'target_base_path')

keyword = source_file_path.split('\\')[-1]
print   (f'文件名:  +{keyword}')
prefix = ''
format_actor = actor.replace(' ', '.')
if chn_name is not None:
    format_actor = f'{format_actor}.{chn_name}'
format_movie = movie.replace(' ', '.')
if season is None or episode is None:
    prefix = f'[{country}]{format_actor} » {format_movie}.{year}'
else:
    format_season = '{:02d}'.format(season)
    format_episode = '{:02d}'.format(episode)
    prefix = f'[{country}]{format_actor} » {format_movie}.{year}.S{format_season}E{format_episode}'
print(f"前缀:   {prefix}")

count = 1

for path, dir_list, file_list in g:

    for file_name in file_list:
        # print(file_name)
        if file_name.startswith(keyword):
            print(os.path.join(path, file_name))
            suffix = file_name.split('.')[-1]
            rename_file_name = f'{prefix}-{count}.{suffix}'
            count += 1
            while True:
                if not os.path.exists(os.path.join(path, rename_file_name)):
                    break
                else:
                    rename_file_name = f'{prefix}-{count}.{suffix}'
                    count += 1
            os.rename(os.path.join(path, file_name), os.path.join(path, rename_file_name))


