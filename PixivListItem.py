# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302

import os
import re
from urllib import parse

import PixivHelper
from PixivException import PixivException


class PixivListItem(object):
    '''Class for item in list.txt'''
    # Represents either contentId or memberId
    dataId = ""
    # Distinct contentId from memberId by boolen
    # False means it's memberId, True is contentId, respectively
    memberOrContent: bool = False
    path = ""

    def __init__(self, dataId, path, isContentId):
        self.dataId = int(dataId)
        self.path = path.strip()
        self.memberOrContent = isContentId
        if self.path == r"N\A":
            self.path = ""

    def __repr__(self):
        return "(id:{0}, path:'{1}')".format(self.dataId, self.path)

    @staticmethod
    def parseList(filename, rootDir=None):
        '''read list.txt and return the list of PixivListItem'''
        members = list()

        if not os.path.exists(filename):
            raise PixivException("File doesn't exists or no permission to read: " + filename,
                                 errorCode=PixivException.FILE_NOT_EXISTS_OR_NO_WRITE_PERMISSION)

        reader = PixivHelper.open_text_file(filename)
        line_no = 1
        try:
            for line in reader:
                original_line = line
                # PixivHelper.safePrint("Processing: " + line)
                if line.startswith('#') or len(line) < 1:
                    continue
                if len(line.strip()) == 0:
                    continue
                # line = PixivHelper.toUnicode(line)
                line = line.strip()
                items = line.split(None, 1)

                # Indicates whether or not it's a contentId instead of memberId,
                # see PixivListItem.memberOrContent member comment
                is_content_id = False

                if items[0].startswith("http"):
                    # handle urls:
                    # http://www.pixiv.net/member_illust.php?id=<member_id>
                    # http://www.pixiv.net/member.php?id=<member_id>
                    parsed = parse.urlparse(items[0])
                    if parsed.path == "/member.php" or parsed.path == "/member_illust.php":
                        query_str = parse.parse_qs(parsed.query)
                        if 'id' in query_str:
                            member_or_content_id = int(query_str["id"][0])
                        else:
                            PixivHelper.print_and_log(
                                'error', "Cannot detect member id from url: " + items[0])
                            continue
                    # Handle artwork urls:
                    # https://www.pixiv.net/<en/?>artworks/<content id>
                    # The en in angle brackets indicates language
                    # but seems to missing in non-english site versions
                    # (Japanese, Korean, whatewer I don't understand
                    # kanji/hiragana/katakana aka runes - yes I googled the name)
                    elif (strippedArtworksUrl := parsed.path.replace("/en", "", 1)).startswith("/artworks/"):
                        is_content_id = True
                        # Some fail tolerance
                        try:
                            member_or_content_id = int(
                                strippedArtworksUrl.replace("/artworks/", "", 1).rstrip("/")
                            )
                        except Exception as contentIdException:
                            PixivHelper.print_and_log(
                                "warning",
                                format(
                                    "Unable to extract ContentId from URL on {} line: {}",
                                    line_no,
                                    items[0],
                                ),
                                contentIdException,
                            )
                            continue
                    else:
                        PixivHelper.print_and_log(
                            "error", "Unsupported url detected: " + items[0]
                        )
                        continue

                else:
                    # handle member id directly
                    member_or_content_id = int(items[0])

                path = ""
                if len(items) > 1:
                    path = items[1].strip()

                    path = path.replace('\"', '')
                    if rootDir is not None:
                        path = path.replace('%root%', rootDir)
                    else:
                        path = path.replace('%root%', '')

                    path = os.path.abspath(path)
                    # have drive letter
                    if re.match(r'[a-zA-Z]:', path):
                        dirpath = path.split(os.sep, 1)
                        dirpath[1] = PixivHelper.sanitize_filename(
                            dirpath[1], None)
                        path = os.sep.join(dirpath)
                    else:
                        path = PixivHelper.sanitize_filename(path, rootDir)

                    path = path.replace('\\\\', '\\')
                    path = path.replace('\\', os.sep)

                list_item = PixivListItem(member_or_content_id, path, is_content_id)
                # PixivHelper.safePrint(u"- {0} ==> {1} ".format(member_id, path))
                members.append(list_item)
                line_no = line_no + 1
                original_line = ""
        except UnicodeDecodeError:
            PixivHelper.get_logger().exception("PixivListItem.parseList(): Invalid value when parsing list")
            PixivHelper.print_and_log('error', 'Invalid value: {0} at line {1}, try to save the list.txt in UTF-8.'.format(
                                      original_line, line_no))
        except BaseException:
            PixivHelper.get_logger().exception("PixivListItem.parseList(): Invalid value when parsing list")
            PixivHelper.print_and_log('error', 'Invalid value: {0} at line {1}'.format(original_line, line_no))

        reader.close()
        return members
