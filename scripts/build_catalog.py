# Author: WangLei
# Email: WangLei1578@outlook.com
# Date: 2026-10-29

"""Rebuild exact, whitespace-normalized historical excerpts from the saved source."""

import hashlib
import html
import json
import re
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/sources/43548-h.htm"
URL = "https://www.gutenberg.org/files/43548/43548-h/43548-h.htm"
VERSION = "pg43548-excerpts-v1"

MAJOR = [
    ("The Fool", "愚者"),
    ("The Magician", "魔术师"),
    ("The High Priestess", "女祭司"),
    ("The Empress", "皇后"),
    ("The Emperor", "皇帝"),
    ("The Hierophant", "教皇"),
    ("The Lovers", "恋人"),
    ("The Chariot", "战车"),
    ("Fortitude", "力量"),
    ("The Hermit", "隐者"),
    ("Wheel of Fortune", "命运之轮"),
    ("Justice", "正义"),
    ("The Hanged Man", "倒吊人"),
    ("Death", "死神"),
    ("Temperance", "节制"),
    ("The Devil", "恶魔"),
    ("The Tower", "高塔"),
    ("The Star", "星星"),
    ("The Moon", "月亮"),
    ("The Sun", "太阳"),
    ("The Last Judgment", "审判"),
    ("The World", "世界"),
]
RANKS = [
    "Ace",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Page",
    "Knight",
    "Queen",
    "King",
]
RANK_ZH = [
    "一",
    "二",
    "三",
    "四",
    "五",
    "六",
    "七",
    "八",
    "九",
    "十",
    "侍从",
    "骑士",
    "王后",
    "国王",
]
SUITS = {"Wands": "权杖", "Cups": "圣杯", "Swords": "宝剑", "Pentacles": "星币"}


def clean(text):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", text)).split())


def make_card(name, zh, arcana, suit, rank, upright, reversed_, anchor, locator):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    upright, reversed_ = clean(upright), clean(reversed_)
    return {
        "id": str(uuid5(NAMESPACE_URL, f"ai-tarot:cards:{slug}")),
        "slug": slug,
        "name_zh": zh,
        "name_en": name,
        "arcana_type": arcana,
        "suit": suit,
        "rank": rank,
        "upright_keywords": re.split(r"[,;.]\s*", upright)[:3],
        "reversed_keywords": re.split(r"[,;.]\s*", reversed_)[:3],
        "upright_meaning": upright,
        "reversed_meaning": reversed_,
        "image_path": None,
        "source_reference": {
            "source_id": "pg-43548",
            "title": "The Illustrated Key to the Tarot: The Veil of Divination",
            "author": "L. W. de Laurence",
            "publication_year": 1918,
            "url": f"{URL}#{anchor}",
            "locator": locator,
            "license": "Public domain in the USA (Project Gutenberg catalog)",
            "language": "en",
            "content_kind": "historical_excerpt",
            "review_status": "source_verified_not_modern_advice",
            "retrieved_on": "2026-10-29",
            "version": VERSION,
            "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "excerpt_sha256": hashlib.sha256(
                (upright + "\n" + reversed_).encode()
            ).hexdigest(),
        },
        "content_version": VERSION,
    }


def build_cards(source):
    cards = []
    major = source.split('id="III3"')[1].split('id="III4"')[0]
    paragraphs = re.findall(r"<p\b[^>]*>(.*?)</p>", major, re.S)
    for rank, (name, zh) in enumerate(MAJOR):
        paragraph = next(p for p in paragraphs if f"<i>{name}.</i>" in p)
        meaning = paragraph.split(f"<i>{name}.</i>")[1]
        upright, reversed_ = re.split(r"<i>Reversed</i>\s*:\s*", meaning)
        upright = re.sub(r"^\s*(?:&mdash;|—)", "", upright)
        cards.append(
            make_card(
                name,
                zh,
                "major",
                None,
                str(rank),
                upright,
                reversed_,
                "III3",
                f"Part III, Section 3, {rank}: {name}",
            )
        )
    minor = source.split('id="III2"')[1].split('id="III3"')[0]
    blocks = minor.split('<div class="card">')[1:]
    assert len(blocks) == 56
    for suit, suit_zh in SUITS.items():
        for i, rank in enumerate(RANKS):
            name = f"{rank} of {suit}"
            block = next(b for b in blocks if f'alt="{name}"' in b)
            upright = re.search(
                r"<i>Divinatory\s+Meanings</i>\s*:(.*?)</p>", block, re.S
            ).group(1)
            reversed_match = re.search(r"<i>Reversed</i>\s*:(.*?)</p>", block, re.S)
            locator = f"Part III, Section 2, {suit.upper()}. {rank.upper()}."
            if reversed_match is None:
                assert name == "Two of Cups"
                supplement = source.split('id="III4"')[1].split('id="III5"')[0]
                cups = supplement.split("<b>Cups.</b>")[1].split("<b>Swords.</b>")[0]
                reversed_ = re.search(
                    r"<li><i>Two.</i>.*?<i>Reversed</i>\s*:(.*?)</li>", cups, re.S
                ).group(1)
                locator += " Upright: Section 2; reversed: Section 4, Cups, Two."
            else:
                reversed_ = reversed_match.group(1)
            anchor = "III2pent" if suit == "Pentacles" else f"III2{suit.lower()}"
            cards.append(
                make_card(
                    name,
                    suit_zh + RANK_ZH[i],
                    "minor",
                    suit.lower(),
                    rank.lower(),
                    upright,
                    reversed_,
                    anchor,
                    locator,
                )
            )
            if name == "Two of Cups":
                cards[-1]["source_reference"]["reversed_url"] = f"{URL}#III4"
    assert len(cards) == len({c["slug"] for c in cards}) == 78
    assert all(c["upright_meaning"] and c["reversed_meaning"] for c in cards)
    return cards


def build_spreads():
    definitions = [
        (
            "single-card",
            "单张牌",
            "聚焦一个主题，适合每日学习与简短反思。",
            ["当前主题"],
        ),
        (
            "three-card-past-present-future",
            "过去、现在、未来",
            "从时间视角整理经历、当下与可能的发展；未来位置不代表确定预言。",
            ["过去", "现在", "未来"],
        ),
        (
            "three-card-situation-challenge-advice",
            "现状、挑战、建议",
            "适合梳理一个具体困惑，以及自己可以采取的行动。",
            ["现状", "挑战", "建议"],
        ),
        (
            "five-card-reflection",
            "五张反思牌阵",
            "从多个角度展开自我反思，留意背景与不确定性。",
            ["问题", "影响因素", "内在状态", "行动建议", "可能的发展方向"],
        ),
    ]
    return [
        {
            "id": str(uuid5(NAMESPACE_URL, f"ai-tarot:spreads:{slug}")),
            "slug": slug,
            "name": name,
            "description": description,
            "positions": [
                {
                    "index": i,
                    "name": p,
                    "description": f"围绕“{p}”进行观察和反思。",
                    "x": i,
                    "y": 0,
                }
                for i, p in enumerate(positions)
            ],
            "is_active": True,
            "version": "1.0.0",
        }
        for slug, name, description, positions in definitions
    ]


if __name__ == "__main__":
    target = ROOT / "backend/app/data"
    target.mkdir(parents=True, exist_ok=True)
    for name, rows in [
        ("cards", build_cards(SOURCE.read_text(encoding="utf-8"))),
        ("spreads", build_spreads()),
    ]:
        (target / f"{name}.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print("Rebuilt 78 source-verified excerpts and 4 project-defined spreads")
