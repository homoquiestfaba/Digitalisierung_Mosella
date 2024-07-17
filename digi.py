from cltk.prosody.lat.hexameter_scanner import HexameterScanner
from cltk.prosody.lat.macronizer import Macronizer
from cltk.alphabet.lat import remove_macrons
from cltk.alphabet.lat import drop_latin_punctuation
from cltk.prosody.lat import verse as v
from xml.etree import ElementTree as ET
import re
import json
import typing

# Global Declarations

Verse: typing.TypeAlias = v

hex_scanner = HexameterScanner()
macronizer = Macronizer("tag_ngram_123_backoff")

FILE_NAME = "mosella_v.txt"
FILE_NAME_TRANSLATION = "translation.txt"
JSON_NAME = "mosella_meta.json"

COUNT = 1
TRUE = 0

MAX_COUNT = None


# File Functions

def read_poem(filename: str) -> typing.List[str]:
    return [
        verse.strip()
        for verse in open(filename, "r", encoding="utf-8").readlines()
    ]


def read_translation(filname: str) -> str:
    return re.sub(
        r"- ",
        "",
        " ".join(
            [
                line.strip()
                for line in open(filname, "r", encoding="utf-8").readlines()
            ]
        )
    )


def log(hexameters: typing.List[Verse]) -> None:
    with open('log.txt', 'w', encoding="utf-8") as log:
        [
            log.writelines(hexameter.accented + "\t" + ", ".join(hexameter.syllables) + hexameter.scansion + "\t" + str(
                hexameter.valid) + "\n")
            for hexameter in hexameters
        ]


def load_json(filename: str) -> dict:
    return json.load(open(filename, "r", encoding="utf-8"))


def write_xml(root: ET.ElementTree, filename: str) -> None:
    ET.indent(root, space="\t", level=0)
    with open(filename + ".xml", "wb") as f:
        f.write(bytes('<?xml version="1.0" encoding="UTF-8"?>\n', "utf-8"))
        root.write(f, encoding="utf-8")


# Analysis Funtions

def prepare_trans(text: str) -> typing.Iterator[str]:
    return iter(re.split(r"\(\d+\)", text))


def macron(text: str) -> str:
    return macronizer.macronize_text(text)


def verse_analysis(verse: str) -> Verse:
    global COUNT
    global TRUE
    verse = drop_latin_punctuation(verse)
    hexameter = hex_scanner.scan(verse)
    if not hexameter.valid:
        hexameter = hex_scanner.scan(verse, dactyl_smoothing=True)
        if not hexameter.valid:
            hexameter = hex_scanner.scan(verse, optional_transform=True)
            if not hexameter.valid:
                hexameter = hex_scanner.scan(verse, optional_transform=True, dactyl_smoothing=True)
                if not hexameter.valid:
                    verse_mac = macron(verse)
                    hexameter = hex_scanner.scan(verse_mac)
                    if not hexameter.valid:
                        hexameter = hex_scanner.scan(verse_mac, dactyl_smoothing=True)
                    if not hexameter.valid:
                        hexameter = hex_scanner.scan(verse_mac, optional_transform=True)
                        if not hexameter.valid:
                            hexameter = hex_scanner.scan(verse_mac, optional_transform=True, dactyl_smoothing=True)
                            if not hexameter.valid:
                                hexameter = hex_scanner.scan(verse)
    print(COUNT, "/", MAX_COUNT)
    if hexameter.valid:
        TRUE += 1
    COUNT += 1
    return hexameter


def metric_analysis(verse_list: list) -> typing.List[Verse]:
    return [
        verse_analysis(verse)
        for verse in verse_list
    ]


# XML Functions

def create_header(tei_header: ET.Element, meta: dict) -> None:
    fileDesc = ET.SubElement(tei_header, "fileDesc")
    titleStmt = ET.SubElement(fileDesc, "titleStmt")
    publicationStmt = ET.SubElement(fileDesc, "publicationStmt")
    sourceDesc = ET.SubElement(fileDesc, "sourceDesc")

    title_full = ET.SubElement(titleStmt, "title", {"type": "full"})
    title_main = ET.SubElement(title_full, "title", {"type": "main"})
    title_main.text = meta["title"]

    editor = ET.SubElement(titleStmt, "editor")
    editor.text = meta["editor"]

    author = ET.SubElement(titleStmt, "author", {"ref": meta["author"]["gnd1"]})
    author.text = meta["author"]["name1"]
    author = ET.SubElement(titleStmt, "author", {"ref": meta["author"]["gnd2"]})
    author.text = meta["author"]["name2"]

    publisher = ET.SubElement(publicationStmt, "publisher", {"ref": meta["publisher"]["gnd"]})
    publisher.text = meta["publisher"]["name"]

    address = ET.SubElement(publicationStmt, "address")
    placeName = ET.SubElement(address, "placeName", {"ref": meta["location"]["gnd1"]})
    placeName.text = meta["location"]["name1"]
    placeName = ET.SubElement(address, "placeName", {"ref": meta["location"]["gnd2"]})
    placeName.text = meta["location"]["name2"]

    date = ET.SubElement(publicationStmt, "date", {"when": meta["date1"]})
    date.text = meta["date1"]
    date = ET.SubElement(publicationStmt, "date", {"when": meta["date2"]})
    date.text = meta["date2"]

    src = ET.SubElement(sourceDesc, "p")
    src.text = meta["src_desc"]


def create_body(tei_body: ET.Element, text: typing.List[Verse], trans: typing.Iterator[str]) -> None:
    i = 0
    verse_count = 0
    for verse in text:
        # Creation of 5 line segment
        if verse_count == 0:
            block = ET.SubElement(tei_body, "div", {"type": "verse-segment", "n": str(i + 1) + "-" + str(i + 5)})
            lat_block = ET.SubElement(block, "div", {"type": "original"})

        # Meter extraction
        pro_meter = re.sub(r"U", "-",
                           re.sub(r"-", "+",
                                  re.sub(r"\s+", "", verse.scansion)
                                  )
                           )

        if verse.valid:
            meter = []
            stretch_mem = ""
            for stretch in pro_meter:
                stretch_mem += stretch
                if stretch_mem == "++":
                    meter.append("++|")
                    stretch_mem = ""
                elif stretch_mem == "+--":
                    meter.append("+--|")
                    stretch_mem = ""
            meter = "".join(meter)
        else:
            meter = "NaN"

        # Line creation
        i += 1
        line = ET.SubElement(lat_block, "l", {"n": str(i), "met": meter})
        line.text = remove_macrons(verse.original)

        # Syllable normalisation
        syllables = [
            re.sub(r"j", "i", s)
            for s in verse.syllables
        ]
        if len(syllables) != len(verse.syllables):
            print("WARNING")
        # Add syllables to line
        syll_count = 1
        if verse.valid and len(syllables) == len(pro_meter):
            last_syllable_stretched = False
            for syll in syllables:
                if last_syllable_stretched:
                    syllable = ET.SubElement(foot, "seg", {"type": "syll", "n": str(syll_count)})
                    syllable.text = syll
                    last_syllable_stretched = False
                elif pro_meter[syll_count - 1] == "+":
                    foot = ET.SubElement(line, "seg", {"type": "foot"})
                    syllable = ET.SubElement(foot, "seg", {"type": "syll", "n": str(syll_count)})
                    syllable.text = syll
                    last_syllable_stretched = True
                else:
                    syllable = ET.SubElement(foot, "seg", {"type": "syll", "n": str(syll_count)})
                    syllable.text = syll
                syll_count += 1

        # Add german translation
        verse_count += 1
        if verse_count == 5 or i == 484:
            verse_count = 0
            de_block = ET.SubElement(block, "div", {"type": "original"})
            translation = ET.SubElement(de_block, "p")
            translation.text = next(trans)


def to_tei(poet_text: typing.List[Verse], trans: typing.Iterator[str]) -> ET.ElementTree:
    meta = load_json(JSON_NAME)
    tei = ET.Element("TEI", {"xmlns": "http://www.tei-c.org/ns/1.0"})
    root = ET.ElementTree(tei)
    tei_header = ET.SubElement(tei, "teiHeader")
    text = ET.SubElement(tei, "text")
    body = ET.SubElement(text, "body")
    create_header(tei_header, meta)
    create_body(body, poet_text, trans)
    return root


# MAIN

def main():
    global MAX_COUNT
    verse_list = read_poem(FILE_NAME)
    translation = read_translation(FILE_NAME_TRANSLATION)
    MAX_COUNT = len(verse_list)
    analyzed = metric_analysis(verse_list)
    block_trans = prepare_trans(translation)
    print("\nValid Hexameters:", TRUE, "/", MAX_COUNT, "\n")
    log(analyzed)
    root = to_tei(analyzed, block_trans)
    write_xml(root, FILE_NAME[:-4])


if __name__ == '__main__':
    main()
