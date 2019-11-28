# -*- coding: utf-8 -*-
import os
import argparse
import sys

from googletrans import Translator
from progressbar import ProgressBar, Percentage, Bar, ETA
import multiprocessing


DEFAULT_CONCURRENCY = 10
DEFAULT_SRC_LANGUAGE = 'ja'
DEFAULT_DST_LANGUAGE = 'zh-CN'

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
            # unicode(sentence,'utf-8').encode("utf-8")
            return self.translator11.translate(sentence, src=self.src, dest=self.dst).text.encode("utf-8")
        except BaseException as e:
            print(e)
            return '翻译错误'



def main():
    """
    Run autosub as a command-line program.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('source_path', help="Path to the video or audio file to subtitle",
                        nargs='?')
    parser.add_argument('-C', '--concurrency', help="Number of concurrent API requests to make",
                        type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument('-S', '--src-language', help="Language spoken in source file",
                        default=DEFAULT_SRC_LANGUAGE)
    parser.add_argument('-D', '--dst-language', help="Desired language for the subtitles",
                        default=DEFAULT_DST_LANGUAGE)
    parser.add_argument('-T', '--translator', help="翻译字幕模式", type=int, default=0)

    args = parser.parse_args()

    try:
        sourcePath=args.source_path,
        concurrency=args.concurrency,
        srcLanguage=args.src_language,
        dstLanguage=args.dst_language,
        nowPath = os.getcwd()
        print(nowPath+sourcePath[0])
        subFile = open(sourcePath[0])
        subFileName = os.path.splitext(sourcePath[0])[0]
        subCon = subFile.readlines()
        subFile.close()
        regions = [x for (k, x) in enumerate(subCon) if (k%4 == 0 or k%4 == 1)]
        rawSub = [x[:-1] for (k, x) in enumerate(subCon) if (k%4 == 2)]
        translatedSub = []
        translatorex = Translator1(dstLanguage[0], None,
                                   dst=dstLanguage[0],
                                   src=srcLanguage[0])
        # print(translatorex.__call__(unicode(rawSub[0],'utf-8').encode("utf-8")))
        # return
        prompt = "Translating from {0} to {1}: ".format(srcLanguage[0], dstLanguage[0])
        widgets = [prompt, Percentage(), ' ', Bar(), ' ', ETA()]
        pbar = ProgressBar(widgets=widgets, maxval=len(regions)).start()
        poolHeight = multiprocessing.Pool(concurrency[0])
        for i, transcript in enumerate(poolHeight.imap(translatorex, rawSub)):
            translatedSub.append(transcript)
            # print(translatedSub[0].encode('utf-8'))
            pbar.update(i)
        pbar.finish()
        poolHeight.close()
        #翻译的字幕
        translatedSubCon = [regions[k*2]+regions[k*2+1]+translatedSub[k] for (k, x) in enumerate(translatedSub)]
        subtitle_file_path = subFileName+"."+dstLanguage[0]+".srt"
        with open(subtitle_file_path, 'wb') as output_file:
            output_file.write(('\n\n'.join(translatedSubCon)))
        print("Subtitles file created at {}".format(subtitle_file_path))
    except KeyboardInterrupt:
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())