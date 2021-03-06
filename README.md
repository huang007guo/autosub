# Autosub <a href="https://pypi.python.org/pypi/autosub"><img src="https://img.shields.io/pypi/v/autosub.svg"></img></a>
  
### Auto-generated subtitles for any video

Autosub is a utility for automatic speech recognition and subtitle generation. It takes a video or an audio file as input, performs voice activity detection to find speech regions, makes parallel requests to Google Web Speech API to generate transcriptions for those regions, (optionally) translates them to a different language, and finally saves the resulting subtitles to disk. It supports a variety of input and output languages (to see which, run the utility with the argument `--list-languages`) and can currently produce subtitles in either the [SRT format](https://en.wikipedia.org/wiki/SubRip) or simple [JSON](https://en.wikipedia.org/wiki/JSON).

### Installation

 只能在linux，python2下使用
```
 apt install ffmpeg
```
1. Install [ffmpeg](https://www.ffmpeg.org/).
2. Run `pip install autosub`.

OR:
 ```
   setup.py --help
    Common commands: (see '--help-commands' for more)

      setup.py build      will build the package underneath 'build/'
      setup.py install    will install the package

    Global options:
      --verbose (-v)      run verbosely (default)
      --quiet (-q)        run quietly (turns verbosity off)
      --dry-run (-n)      don't actually do anything
      --help (-h)         show detailed help message
      --no-user-cfg       ignore pydistutils.cfg in your home directory
      --command-packages  list of packages that provide distutils commands

    Information display options (just display information, ignore any commands)
      --help-commands     list all available commands
      --name              print package name
      --version (-V)      print package version
      --fullname          print <package name>-<version>
      --author            print the author's name
      --author-email      print the author's email address
      --maintainer        print the maintainer's name
      --maintainer-email  print the maintainer's email address
      --contact           print the maintainer's name if known, else the author's
      --contact-email     print the maintainer's email address if known, else the
                          author's
      --url               print the URL for this package
      --license           print the license of the package
      --licence           alias for --license
      --description       print the package description
      --long-description  print the long package description
      --platforms         print the list of platforms
      --classifiers       print the list of classifiers
      --keywords          print the list of keywords
      --provides          print the list of packages/modules provided
      --requires          print the list of packages/modules required
      --obsoletes         print the list of packages/modules made obsolete

    usage: setup.py [global_opts] cmd1 [cmd1_opts] [cmd2 [cmd2_opts] ...]
       or: setup.py --help [cmd1 cmd2 ...]
       or: setup.py --help-commands
       or: setup.py cmd --help
```



### Usage

```
$ autosub -h
usage: autosub [-h] [-C CONCURRENCY] [-o OUTPUT] [-F FORMAT] [-S SRC_LANGUAGE]
               [-D DST_LANGUAGE] [-K API_KEY] [--list-formats]
               [--list-languages]
               [source_path]

positional arguments:
  source_path           Path to the video or audio file to subtitle

optional arguments:
  -h, --help            show this help message and exit
  -C CONCURRENCY, --concurrency CONCURRENCY
                        Number of concurrent API requests to make
  -o OUTPUT, --output OUTPUT
                        Output path for subtitles (by default, subtitles are
                        saved in the same directory and name as the source
                        path)
  -F FORMAT, --format FORMAT
                        Destination subtitle format
  -S SRC_LANGUAGE, --src-language SRC_LANGUAGE
                        Language spoken in source file
  -D DST_LANGUAGE, --dst-language DST_LANGUAGE
                        Desired language for the subtitles
  -K API_KEY, --api-key API_KEY
                        The Google Translate API key to be used. (Required for
                        subtitle translation)
  --list-formats        List all available subtitle formats
  --list-languages      List all available source/destination languages
```
Japanese file to Chinese (Simplified) sub:
```
autosub -S ja -D zh-CN file.mp4
```
### License

MIT
