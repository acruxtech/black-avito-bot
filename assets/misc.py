import random


def generate_name():
    with open("assets/20k.txt", "r", encoding="utf-8") as f:
        words: list[str] = f.readlines()

    return random.choice(words[:10000]).strip().title() + random.choice(words[10000:]).strip().title()