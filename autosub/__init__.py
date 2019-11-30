# -*- coding: utf-8 -*-
"""
Defines autosub's main functionality.
!写了# -*- coding: utf-8 -*-后所有的手动定义的str都会变成unicode类型,必须使用encode(utf8)转为字符串!
"""

#!/usr/bin/env python

from __future__ import absolute_import, print_function, unicode_literals

import argparse
import audioop
import math
import multiprocessing
from multiprocessing import Process
import os
import subprocess
import sys
import tempfile
import wave
import json
import requests
from googletrans import Translator
# import pdb
# reload(sys)
# sys.setdefaultencoding('utf8')
try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError

from googleapiclient.discovery import build
from progressbar import ProgressBar, Percentage, Bar, ETA

from autosub.constants import (
    LANGUAGE_CODES, GOOGLE_SPEECH_API_KEY, GOOGLE_SPEECH_API_URL,
)
from autosub.formatters import FORMATTERS

DEFAULT_SUBTITLE_FORMAT = 'srt'
DEFAULT_CONCURRENCY = 5
DEFAULT_HEIGHT_CONCURRENCY = 6
DEFAULT_SRC_LANGUAGE = 'ja'
DEFAULT_DST_LANGUAGE = 'zh-CN'
DEFAULT_ONCE_FILE = 4


def percentile(arr, percent):
    """
    Calculate the given percentile of arr.
    """
    arr = sorted(arr)
    index = (len(arr) - 1) * percent
    floor = math.floor(index)
    ceil = math.ceil(index)
    if floor == ceil:
        return arr[int(index)]
    low_value = arr[int(floor)] * (ceil - index)
    high_value = arr[int(ceil)] * (index - floor)
    return low_value + high_value


class FLACConverter(object): # pylint: disable=too-few-public-methods
    """
    Class for converting a region of an input audio or video file into a FLAC audio file
    """
    def __init__(self, source_path, include_before=0.25, include_after=0.25):
        # 这里传进来的是临时文件名没有编码问题 无需 .encode("utf8")
        self.source_path = source_path
        self.include_before = include_before
        self.include_after = include_after

    def __call__(self, region):
        try:
            start, end = region
            start = max(0, start - self.include_before)
            end += self.include_after
            temp = tempfile.NamedTemporaryFile(suffix='.flac', delete=False)
            # 这里传进来的是临时文件名没有编码问题 无需 .encode("utf8")
            command = ["E:\\YOKA\\project\\autosub\\ffmpeg\\bin\\ffmpeg.exe", "-ss", str(start), "-t", str(end - start),
                       "-y", "-i", self.source_path,
                       "-loglevel", "error", temp.name]
            use_shell = True if os.name == "nt" else False
            # print(command)
            subprocess.check_output(command, stdin=open(os.devnull), shell=use_shell)
            read_data = temp.read()
            temp.close()
            os.unlink(temp.name)
            return read_data

        except KeyboardInterrupt:
            return None


class SpeechRecognizer(object): # pylint: disable=too-few-public-methods
    """
    Class for performing speech-to-text for an input FLAC file.
    """
    def __init__(self, language="en", rate=44100, retries=3, api_key=GOOGLE_SPEECH_API_KEY):
        self.language = language
        self.rate = rate
        self.api_key = api_key
        self.retries = retries

    def __call__(self, data):
        try:
            for _ in range(self.retries):
                url = GOOGLE_SPEECH_API_URL.format(lang=self.language, key=self.api_key)
                headers = {"Content-Type": "audio/x-flac; rate=%d" % self.rate}

                try:
                    resp = requests.post(url, data=data, headers=headers)
                except requests.exceptions.ConnectionError:
                    continue

                for line in resp.content.decode('utf-8').split("\n"):
                    try:
                        line = json.loads(line)
                        line = line['result'][0]['alternative'][0]['transcript']
                        return line[:1].upper() + line[1:]
                    except IndexError:
                        # no result
                        continue
                    except JSONDecodeError:
                        continue

        except KeyboardInterrupt:
            return None


# class Translator1(object): # pylint: disable=too-few-public-methods
#     """
#     Class for translating a sentence from a one language to another.
#     """
#     def __init__(self, language, api_key, src, dst):
#         self.language = language
#         self.api_key = api_key
#         self.service = build('translate', 'v2',
#                              developerKey=self.api_key)
#         self.src = src
#         self.dst = dst
#
#     def __call__(self, sentence):
#         try:
#             if not sentence:
#                 return None
#
#             result = self.service.translations().list( # pylint: disable=no-member
#                 source=self.src,
#                 target=self.dst,
#                 q=[sentence]
#             ).execute()
#
#             if 'translations' in result and result['translations'] and \
#                 'translatedText' in result['translations'][0]:
#                 return result['translations'][0]['translatedText']
#
#             return None
#
#         except KeyboardInterrupt:
#             return None

class Translator1(object): # pylint: disable=too-few-public-methods
    """
    Class for translating a sentence from a one language to another.
    """
    def __init__(self, language, api_key, src, dst):
        self.language = language
        #self.api_key = api_key
        #self.service = build('translate', 'v2', developerKey=self.api_key)
        self.src = src
        self.dst = dst
        self.translator11 = Translator(service_urls=[
            'translate.google.cn',
            # 'translate.google.com',
            # 'translate.google.co.kr',
        ])

    def __call__(self, sentence):
        try:
            if not sentence:
                return None
            return self.translator11.translate(sentence, src=self.src, dest=self.dst).text
        except BaseException as e:
            print(e)
            return '翻译错误'


def which(program):
    """
    Return the path for a given executable.
    """
    def is_exe(file_path):
        """
        Checks whether a file is executable.
        """
        return os.path.isfile(file_path) and os.access(file_path, os.X_OK)

    fpath, _ = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None

# def extract_audio(filename, channels=1, rate=16000): # 采样频率一般共分为22.05KHz、44.1KHz、48KHz三个等级，22.05KHz只能达到FM广播的声音品质，44.1KHz则是理论上的CD音质界限，//48KHz则更加精确一些。
def extract_audio(filename, channels=1, rate=44100):
    """
    生成音频文件
    Extract audio from an input file to a temporary WAV file.
    :param channels 音轨
    :param rate 采样率
    """
    # pdb.set_trace() # 运行到这里会自动暂停
    temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    if not os.path.isfile(filename):
        print("The given file does not exist: {}".encode("utf8").format(filename))
        raise Exception("Invalid filepath: {}".encode("utf8").format(filename))
    # if not which("ffmpeg"):
    #     print("ffmpeg: Executable not found on machine.")
    #     raise Exception("Dependency not found: ffmpeg")
    command = ["E:\\YOKA\\project\\autosub\\ffmpeg\\bin\\ffmpeg.exe".encode("utf8"), "-y".encode("utf8"), "-i".encode("utf8"), filename,
               "-ac".encode("utf8"), str(channels).encode("utf8"), "-ar".encode("utf8"), str(rate).encode("utf8"),
               "-loglevel".encode("utf8"), "error".encode("utf8"), temp.name.encode("utf8")]
    use_shell = True if os.name == "nt" else False
    subprocess.check_output(command, stdin=open(os.devnull), shell=use_shell)
    return temp.name, rate


def find_speech_regions(filename, frame_width=4096, min_region_size=0.5,
                        max_region_size=6):  # pylint: disable=too-many-locals
    """
    语音分段
    :param frame_width 读取声音数据大小
    Perform voice activity detection on a given audio file.
    """
    reader = wave.open(filename)
    sample_width = reader.getsampwidth()
    rate = reader.getframerate()
    n_channels = reader.getnchannels()
    chunk_duration = float(frame_width) / rate

    n_chunks = int(math.ceil(reader.getnframes() * 1.0 / frame_width))
    energies = []

    for _ in range(n_chunks):
        # 读取声音数据
        chunk = reader.readframes(frame_width)
        energies.append(audioop.rms(chunk, sample_width * n_channels))

    threshold = percentile(energies, 0.2)

    elapsed_time = 0

    regions = []
    region_start = None

    for energy in energies:
        is_silence = energy <= threshold
        max_exceeded = region_start and elapsed_time - region_start >= max_region_size

        if (max_exceeded or is_silence) and region_start:
            if elapsed_time - region_start >= min_region_size:
                regions.append((region_start, elapsed_time))
                region_start = None

        elif (not region_start) and (not is_silence):
            region_start = elapsed_time
        elapsed_time += chunk_duration
    return regions


def generate_subtitles( # pylint: disable=too-many-locals,too-many-arguments
        source_path,
        output=None,
        concurrency=DEFAULT_CONCURRENCY,
        src_language=DEFAULT_SRC_LANGUAGE,
        dst_language=DEFAULT_DST_LANGUAGE,
        subtitle_file_format=DEFAULT_SUBTITLE_FORMAT,
        api_key=None,
):
    """
    Given an input audio/video file, generate subtitles in the specified language and format.
    """
    # 生成音频文件
    # nowPath = os.getcwd()
    # print(type(nowPath), type("\\"), type(source_path))
    # source_path = nowPath + "\\".encode("utf8") + source_path

    print(source_path)
    # source_path = unicode(source_path,'utf-8')
    audio_filename, audio_rate = extract_audio(source_path)

    # 分段
    regions = find_speech_regions(audio_filename)

    # 转换为.flac临时文件音频
    converter = FLACConverter(source_path=audio_filename)
    recognizer = SpeechRecognizer(language=src_language, rate=audio_rate,
                                  api_key=GOOGLE_SPEECH_API_KEY)

    transcripts = []
    translated_transcripts = []
    dest = output
    if regions:
        try:
            widgets = ["Converting speech regions to FLAC files: ", Percentage(), ' ', Bar(), ' ',
                       ETA()]
            pbar = ProgressBar(widgets=widgets, maxval=len(regions)).start()
            extracted_regions = []
            pool = multiprocessing.Pool(concurrency)
            for i, extracted_region in enumerate(pool.imap(converter, regions)):
                extracted_regions.append(extracted_region)
                pbar.update(i)
            pbar.finish()

            widgets = ["Performing speech recognition: ", Percentage(), ' ', Bar(), ' ', ETA()]
            pbar = ProgressBar(widgets=widgets, maxval=len(regions)).start()
            for i, transcript in enumerate(pool.imap(recognizer, extracted_regions)):
                transcripts.append(transcript)
                pbar.update(i)
            pbar.finish()
            pool.close()
            if src_language.split("-")[0] != dst_language.split("-")[0]:
                poolHeight = multiprocessing.Pool(DEFAULT_HEIGHT_CONCURRENCY)
                # if api_key:
                google_translate_api_key = api_key
                translatorex = Translator1(dst_language, google_translate_api_key,
                                           dst=dst_language,
                                           src=src_language)
                prompt = "Translating from {0} to {1}: ".format(src_language, dst_language)
                widgets = [prompt, Percentage(), ' ', Bar(), ' ', ETA()]
                pbar = ProgressBar(widgets=widgets, maxval=len(regions)).start()
                for i, transcript in enumerate(poolHeight.imap(translatorex, transcripts)):
                    translated_transcripts.append(transcript)
                    pbar.update(i)
                pbar.finish()
                # 翻译的字幕
                timed_subtitles = [(r, t) for r, t in zip(regions, translated_transcripts) if t]
                formatter = FORMATTERS.get(subtitle_file_format)
                formatted_subtitles = formatter(timed_subtitles)
                if not dest:
                    base = os.path.splitext(source_path)[0]
                    destFile = base + ".".encode("utf8") + subtitle_file_format.encode("utf8")
                with open(destFile, 'wb') as output_file:
                    output_file.write(formatted_subtitles.encode("utf-8"))
                poolHeight.close()
                # else:
                #     print(
                #         "Error: Subtitle translation requires specified Google Translate API key. "
                #         "See --help for further information."
                #     )
                #     return 1

        except BaseException as e:
            print(e)
            pbar.finish()
            pool.terminate()
            pool.join()
            print("Cancelling transcription")
            raise
        finally:
            # 原始字幕
            timed_subtitles = [(r, t) for r, t in zip(regions, transcripts) if t]
            formatter = FORMATTERS.get(subtitle_file_format)
            formatted_subtitles = formatter(timed_subtitles)
            if not dest:
                base = os.path.splitext(source_path)[0]
                destFile = base + ".raw.".encode("utf8") + subtitle_file_format.encode("utf8")
            with open(destFile, 'wb') as output_file:
                output_file.write(formatted_subtitles.encode("utf-8"))

    os.remove(audio_filename)
    print("Subtitles file created at ".encode("utf8") + destFile)
    return dest


def validate(args):
    """
    Check that the CLI arguments passed to autosub are valid.
    """
    if args.format not in FORMATTERS:
        print(
            "Subtitle format not supported. "
            "Run with --list-formats to see all supported formats."
        )
        return False

    if args.src_language not in LANGUAGE_CODES.keys():
        print(
            "Source language not supported. "
            "Run with --list-languages to see all supported languages."
        )
        return False

    if args.dst_language not in LANGUAGE_CODES.keys():
        print(
            "Destination language not supported. "
            "Run with --list-languages to see all supported languages."
        )
        return False

    if not args.source_path:
        print("Error: You need to specify a source path.")
        return False

    return True

def filterFileFun(fileName, *suffix):
    try:
        if isinstance(fileName, str):fileName=fileName.decode("gbk")
        for nowSuffix in suffix:
            if fileName.endswith(".".encode("utf8")+nowSuffix):
                return True
    except BaseException as e:
        print (e)
    return False

def main():
    """
    Run autosub as a command-line program.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('source_path', help="Path to the video or audio file to subtitle",
                        nargs='?')
    parser.add_argument('-C', '--concurrency', help="Number of concurrent API requests to make",
                        type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument('-o', '--output',
                        help="Output path for subtitles (by default, subtitles are saved in \
                        the same directory and name as the source path)")
    parser.add_argument('-F', '--format', help="Destination subtitle format",
                        default=DEFAULT_SUBTITLE_FORMAT)
    parser.add_argument('-S', '--src-language', help="Language spoken in source file",
                        default=DEFAULT_SRC_LANGUAGE)
    parser.add_argument('-D', '--dst-language', help="Desired language for the subtitles",
                        default=DEFAULT_DST_LANGUAGE)
    parser.add_argument('-K', '--api-key',
                        help="The Google Translate API key to be used. \
                        (Required for subtitle translation)")
    parser.add_argument('--list-formats', help="List all available subtitle formats",
                        action='store_true')
    parser.add_argument('--list-languages', help="List all available source/destination languages",
                        action='store_true')
    parser.add_argument('-T', '--translator', help="翻译字幕模式", type=int, default=0)
    parser.add_argument('-N', '--number', help="一次处理的个数", type=int, default=DEFAULT_ONCE_FILE)
	parser.add_argument('-SD', '--shutdown', help="转换完关机", type=int, default=0)

    args = parser.parse_args()

    onceNum = args.number
    source_path = args.source_path

    if args.list_formats:
        print("List of formats:")
        for subtitle_format in FORMATTERS:
            print("{format}".format(format=subtitle_format))
        return 0

    if args.list_languages:
        print("List of all languages:")
        for code, language in sorted(LANGUAGE_CODES.items()):
            print("{code}\t{language}".format(code=code, language=language))
        return 0
    # 字幕翻译
    if args.translator == 1:
        print('translator sub')
        import autosub.subTranslate
        sys.exit(autosub.subTranslate.main())
    # 音频翻译
    else:
        if not validate(args):
            return 1
        try:
            allFile = []
            if not os.path.isdir(source_path):
                allFile = [source_path]
            else:
                file_name_lists = []
                for maindir, subdir, file_name_list in os.walk(source_path):
                    # print("1:",maindir) #当前主目录
                    # print("2:",subdir) #当前主目录下的所有目录
                    # print("3:",file_name_list)  #当前主目录下的所有文件
                    file_name_lists = file_name_lists + [maindir+"\\".encode("utf8")+x for x in file_name_list]
                allFile = [x for x in file_name_lists if filterFileFun(x, "wmv", "avi", "mpeg", "mpg", "rm", "rmvb", "flv", "mp4", "mkv")]
            print(allFile)
            concurrencyNum = len(allFile) if len(allFile) < onceNum else onceNum
            i = 0
			j = 0
            nowProcessAll = []
            for nowFile in allFile:
                nowProcess = Process(target=generate_subtitles, args=(),
                        kwargs={
                            'source_path':nowFile,
                            'concurrency':args.concurrency,
                            'src_language':args.src_language,
                            'dst_language':args.dst_language,
                            'api_key':args.api_key,
                            'subtitle_file_format':args.format,
                            'output':args.output
                        })
                nowProcess.start()
                nowProcessAll.append(nowProcess)
                i = i+1
				j = j+1
                if i == concurrencyNum or j == len(allFile):
                    i = 0
                    for nowProcess in nowProcessAll:
						try:
							nowProcess.join()
						except BaseException as e:
							print(e)
                    print("----------------Ok----------------------")
                    nowProcessAll = []
            print("all Ok")

            # subtitle_file_path = generate_subtitles(
            #     source_path=allFile[0],
            #     concurrency=args.concurrency,
            #     src_language=args.src_language,
            #     dst_language=args.dst_language,
            #     api_key=args.api_key,
            #     subtitle_file_format=args.format,
            #     output=args.output,
            # )
            # print("Subtitles file created at {}".format(subtitle_file_path))
        except BaseException as e:
            print(e)
            return 1
		finally:
            # 自动关机
			if args.shutdown == 1:
				print('60s after shutdown pc')
				os.system('shutdown -s -t 60')
		
        return 0


if __name__ == '__main__':
    sys.exit(main())
