import random


def generate_username():
    adjectives = [
        "Bold",
        "Brave",
        "Bright",
        "Calm",
        "Clever",
        "Curious",
        "Gentle",
        "Hopeful",
        "Kind",
        "Luminous",
        "Quiet",
        "Radiant",
        "Serene",
        "Soft",
        "Steady",
        "Still",
        "Tender",
        "True",
        "Vivid",
        "Wise",
    ]

    nouns = [
        "Cloud",
        "Cypress",
        "Drift",
        "Echo",
        "Fern",
        "Flame",
        "Lantern",
        "Leaf",
        "Moon",
        "Nest",
        "Otter",
        "Pebble",
        "Petal",
        "River",
        "Sky",
        "Sparrow",
        "Star",
        "Stone",
        "Stream",
        "Willow",
    ]

    # Generate a random number between 1 and 9999 (1-4 digits)
    number = random.randint(1, 9999)

    # Randomly select an adjective and noun
    adjective = random.choice(adjectives)
    noun = random.choice(nouns)

    return f"{adjective}{noun}{number}"
